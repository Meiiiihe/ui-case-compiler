from __future__ import annotations

from io import BytesIO
from zipfile import ZipFile

import pytest

from ui_case_compiler.data.table_parser import DatasetParseError, TableDatasetParser


def test_parse_csv_rows() -> None:
    content = b"username,password\nalice,secret\nbob,wrong\n"

    dataset = TableDatasetParser().parse("login.csv", content)

    assert dataset.columns == ["username", "password"]
    assert dataset.rows == [
        {"username": "alice", "password": "secret"},
        {"username": "bob", "password": "wrong"},
    ]


def test_parse_xlsx_rows() -> None:
    dataset = TableDatasetParser().parse("login.xlsx", _xlsx_bytes())

    assert dataset.columns == ["username", "password"]
    assert dataset.rows[0]["username"] == "alice"
    assert dataset.rows[1]["password"] == "wrong"


def test_duplicate_headers_are_rejected() -> None:
    content = b"username,username\nalice,bob\n"

    with pytest.raises(DatasetParseError, match="表头不能重复"):
        TableDatasetParser().parse("bad.csv", content)


def _xlsx_bytes() -> bytes:
    buffer = BytesIO()
    with ZipFile(buffer, "w") as workbook:
        workbook.writestr(
            "xl/workbook.xml",
            """<?xml version="1.0" encoding="UTF-8"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"
 xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <sheets><sheet name="Sheet1" sheetId="1" r:id="rId1"/></sheets>
</workbook>""",
        )
        workbook.writestr(
            "xl/_rels/workbook.xml.rels",
            """<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1"
   Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet"
   Target="worksheets/sheet1.xml"/>
</Relationships>""",
        )
        workbook.writestr(
            "xl/sharedStrings.xml",
            """<?xml version="1.0" encoding="UTF-8"?>
<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <si><t>username</t></si><si><t>password</t></si>
  <si><t>alice</t></si><si><t>secret</t></si>
  <si><t>bob</t></si><si><t>wrong</t></si>
</sst>""",
        )
        workbook.writestr(
            "xl/worksheets/sheet1.xml",
            """<?xml version="1.0" encoding="UTF-8"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <sheetData>
    <row r="1"><c r="A1" t="s"><v>0</v></c><c r="B1" t="s"><v>1</v></c></row>
    <row r="2"><c r="A2" t="s"><v>2</v></c><c r="B2" t="s"><v>3</v></c></row>
    <row r="3"><c r="A3" t="s"><v>4</v></c><c r="B3" t="s"><v>5</v></c></row>
  </sheetData>
</worksheet>""",
        )
    return buffer.getvalue()
