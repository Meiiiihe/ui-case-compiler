from __future__ import annotations

import csv
from dataclasses import dataclass
from io import BytesIO, StringIO
from pathlib import PurePosixPath
from xml.etree import ElementTree
from zipfile import ZipFile

from ui_case_compiler.errors import UiCaseCompilerError


class DatasetParseError(UiCaseCompilerError):
    """Raised when a data-driven run dataset cannot be parsed."""


@dataclass(frozen=True)
class ParsedDataset:
    columns: list[str]
    rows: list[dict[str, str]]


class TableDatasetParser:
    """Parse CSV, TSV, and basic XLSX files into runtime parameter rows."""

    def parse(self, filename: str, content: bytes) -> ParsedDataset:
        lower = filename.lower()
        if lower.endswith(".csv"):
            return self._parse_delimited(content, delimiter=",")
        if lower.endswith(".tsv"):
            return self._parse_delimited(content, delimiter="\t")
        if lower.endswith(".xlsx"):
            return self._parse_xlsx(content)
        msg = "仅支持 CSV、TSV 或 XLSX 数据文件"
        raise DatasetParseError(msg)

    def _parse_delimited(self, content: bytes, delimiter: str) -> ParsedDataset:
        text = self._decode_text(content)
        reader = csv.DictReader(StringIO(text), delimiter=delimiter)
        fieldnames = reader.fieldnames or []
        columns = [self._normalize_header(column) for column in fieldnames]
        if not columns or any(not column for column in columns):
            msg = "数据文件第一行必须是非空表头"
            raise DatasetParseError(msg)

        rows: list[dict[str, str]] = []
        for raw in reader:
            row = {
                columns[index]: self._string_value(raw.get(fieldnames[index], ""))
                for index in range(len(columns))
            }
            if any(value != "" for value in row.values()):
                rows.append(row)
        return self._validated(columns, rows)

    def _parse_xlsx(self, content: bytes) -> ParsedDataset:
        try:
            with ZipFile(BytesIO(content)) as workbook:
                shared_strings = self._read_shared_strings(workbook)
                sheet_path = self._first_sheet_path(workbook)
                sheet_xml = workbook.read(sheet_path)
        except Exception as exc:
            msg = "XLSX 文件读取失败，请确认文件没有损坏"
            raise DatasetParseError(msg) from exc

        table = self._sheet_to_table(sheet_xml, shared_strings)
        if not table:
            msg = "XLSX 文件中没有可读取的数据"
            raise DatasetParseError(msg)

        header_index = next(
            (index for index, row in enumerate(table) if any(cell.strip() for cell in row)),
            None,
        )
        if header_index is None:
            msg = "XLSX 文件中没有表头"
            raise DatasetParseError(msg)

        columns = [self._normalize_header(cell) for cell in table[header_index]]
        while columns and not columns[-1]:
            columns.pop()
        if not columns or any(not column for column in columns):
            msg = "XLSX 第一行有效数据必须是非空表头"
            raise DatasetParseError(msg)

        rows: list[dict[str, str]] = []
        for raw in table[header_index + 1 :]:
            row = {
                columns[index]: raw[index].strip() if index < len(raw) else ""
                for index in range(len(columns))
            }
            if any(value != "" for value in row.values()):
                rows.append(row)
        return self._validated(columns, rows)

    def _read_shared_strings(self, workbook: ZipFile) -> list[str]:
        if "xl/sharedStrings.xml" not in workbook.namelist():
            return []
        root = ElementTree.fromstring(workbook.read("xl/sharedStrings.xml"))
        namespace = self._namespace(root.tag)
        values: list[str] = []
        for item in root.findall(f"{namespace}si"):
            texts = [node.text or "" for node in item.findall(f".//{namespace}t")]
            values.append("".join(texts))
        return values

    def _first_sheet_path(self, workbook: ZipFile) -> str:
        workbook_root = ElementTree.fromstring(workbook.read("xl/workbook.xml"))
        workbook_ns = self._namespace(workbook_root.tag)
        rel_ns = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
        first_sheet = workbook_root.find(f"{workbook_ns}sheets/{workbook_ns}sheet")
        if first_sheet is None:
            raise DatasetParseError("XLSX 文件中没有工作表")
        rel_id = first_sheet.attrib.get(f"{rel_ns}id")
        if not rel_id:
            return "xl/worksheets/sheet1.xml"

        rels_root = ElementTree.fromstring(workbook.read("xl/_rels/workbook.xml.rels"))
        rels_ns = self._namespace(rels_root.tag)
        for rel in rels_root.findall(f"{rels_ns}Relationship"):
            if rel.attrib.get("Id") == rel_id:
                target = rel.attrib["Target"].lstrip("/")
                path = PurePosixPath("xl") / target
                return str(path)
        raise DatasetParseError("XLSX 工作表关系解析失败")

    def _sheet_to_table(self, sheet_xml: bytes, shared_strings: list[str]) -> list[list[str]]:
        root = ElementTree.fromstring(sheet_xml)
        namespace = self._namespace(root.tag)
        table: list[list[str]] = []
        for row_node in root.findall(f".//{namespace}sheetData/{namespace}row"):
            row_values: dict[int, str] = {}
            for cell in row_node.findall(f"{namespace}c"):
                ref = cell.attrib.get("r", "")
                column_index = self._column_index(ref)
                row_values[column_index] = self._cell_value(cell, namespace, shared_strings)
            if row_values:
                max_index = max(row_values)
                table.append([row_values.get(index, "") for index in range(max_index + 1)])
        return table

    def _cell_value(
        self,
        cell: ElementTree.Element,
        namespace: str,
        shared_strings: list[str],
    ) -> str:
        cell_type = cell.attrib.get("t")
        if cell_type == "inlineStr":
            texts = [node.text or "" for node in cell.findall(f".//{namespace}t")]
            return "".join(texts).strip()

        value_node = cell.find(f"{namespace}v")
        value = value_node.text if value_node is not None else ""
        if cell_type == "s" and value:
            index = int(value)
            return shared_strings[index].strip() if index < len(shared_strings) else ""
        return self._string_value(value)

    def _validated(self, columns: list[str], rows: list[dict[str, str]]) -> ParsedDataset:
        if len(set(columns)) != len(columns):
            msg = "数据文件表头不能重复"
            raise DatasetParseError(msg)
        if not rows:
            msg = "数据文件至少需要一行数据"
            raise DatasetParseError(msg)
        return ParsedDataset(columns=columns, rows=rows)

    @staticmethod
    def _decode_text(content: bytes) -> str:
        for encoding in ("utf-8-sig", "utf-8", "gb18030"):
            try:
                return content.decode(encoding)
            except UnicodeDecodeError:
                continue
        msg = "文本文件编码无法识别，请使用 UTF-8 或 GB18030"
        raise DatasetParseError(msg)

    @staticmethod
    def _normalize_header(value: str | None) -> str:
        return (value or "").strip()

    @staticmethod
    def _string_value(value: object) -> str:
        return "" if value is None else str(value).strip()

    @staticmethod
    def _namespace(tag: str) -> str:
        return tag.split("}")[0] + "}" if tag.startswith("{") else ""

    @staticmethod
    def _column_index(cell_ref: str) -> int:
        letters = "".join(char for char in cell_ref if char.isalpha())
        if not letters:
            return 0
        index = 0
        for char in letters:
            index = index * 26 + (ord(char.upper()) - ord("A") + 1)
        return index - 1
