import { useState } from "react";
import { Link } from "react-router-dom";
import { batchRunCase, previewDataset } from "../api/cases";
import type { BatchRunResult, DatasetPreviewResponse } from "../api/types";
import { ErrorBanner } from "./ErrorBanner";
import { Spinner } from "./Spinner";

function paramsSummary(params: Record<string, string>): string {
  return Object.entries(params)
    .slice(0, 4)
    .map(([key, value]) => `${key}=${value}`)
    .join("，");
}

async function fileToBase64(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onerror = () => reject(new Error("数据文件读取失败"));
    reader.onload = () => {
      const result = String(reader.result ?? "");
      resolve(result.includes(",") ? (result.split(",")[1] ?? "") : result);
    };
    reader.readAsDataURL(file);
  });
}

export function BatchRunPanel({ caseId }: { caseId: string }) {
  const [preview, setPreview] = useState<DatasetPreviewResponse | null>(null);
  const [result, setResult] = useState<BatchRunResult | null>(null);
  const [filename, setFilename] = useState("");
  const [concurrency, setConcurrency] = useState(1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onFileChange(file: File | undefined) {
    setError(null);
    setResult(null);
    setPreview(null);
    if (!file) return;
    setFilename(file.name);
    setLoading(true);
    try {
      const content = await fileToBase64(file);
      const resp = await previewDataset({ filename: file.name, content_base64: content });
      setPreview(resp);
    } catch (err) {
      setError(err instanceof Error ? err.message : "数据文件解析失败");
    } finally {
      setLoading(false);
    }
  }

  async function runBatch() {
    if (!preview) return;
    setError(null);
    setLoading(true);
    try {
      const resp = await batchRunCase(caseId, {
        rows: preview.rows,
        concurrency,
        headed: false,
      });
      setResult(resp);
    } catch (err) {
      setError(err instanceof Error ? err.message : "批量执行失败");
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="panel batch-panel">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Data Driven</p>
          <h2>批量数据驱动</h2>
        </div>
        <span className="hint">表头会作为运行参数名，例如 username、password</span>
      </div>

      <ErrorBanner message={error} />
      <Spinner show={loading} />

      <div className="batch-controls">
        <label className="field">
          <span>数据文件</span>
          <input
            aria-label="数据文件"
            accept=".csv,.tsv,.xlsx"
            type="file"
            onChange={(event) => void onFileChange(event.target.files?.[0])}
          />
        </label>
        <label className="field batch-concurrency">
          <span>并发数</span>
          <input
            aria-label="并发数"
            min={1}
            max={8}
            type="number"
            value={concurrency}
            onChange={(event) => {
              const next = Number(event.target.value);
              setConcurrency(Number.isFinite(next) ? Math.min(8, Math.max(1, next)) : 1);
            }}
          />
        </label>
        <button
          className="primary-action"
          disabled={!preview || loading}
          onClick={runBatch}
          type="button"
        >
          执行批量测试
        </button>
      </div>

      {preview && (
        <div className="dataset-preview">
          <div className="batch-summary-line">
            <strong>{filename}</strong>
            <span>{preview.row_count} 行数据</span>
            <span>{preview.columns.length} 个参数</span>
          </div>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  {preview.columns.map((column) => (
                    <th key={column}>{column}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {preview.preview_rows.map((row, index) => (
                  <tr key={`${index}-${paramsSummary(row)}`}>
                    {preview.columns.map((column) => (
                      <td key={column}>{row[column]}</td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {result && (
        <div className="batch-result">
          <div className="metric-grid">
            <div className="metric"><span>总数</span><strong>{result.total}</strong></div>
            <div className="metric passed"><span>通过</span><strong>{result.passed}</strong></div>
            <div className="metric failed"><span>失败</span><strong>{result.failed}</strong></div>
          </div>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>行号</th>
                  <th>状态</th>
                  <th>数据摘要</th>
                  <th>耗时</th>
                  <th>运行详情</th>
                </tr>
              </thead>
              <tbody>
                {result.results.map((item) => (
                  <tr key={item.index}>
                    <td>{item.index}</td>
                    <td><span className={`status-badge ${item.status}`}>{item.status === "passed" ? "通过" : "失败"}</span></td>
                    <td>{paramsSummary(item.params)}</td>
                    <td>{item.duration_ms} ms</td>
                    <td>
                      {item.run_id ? (
                        <Link className="link-button" to={`/runs/${item.run_id}`}>
                          查看
                        </Link>
                      ) : (
                        item.error ?? "无运行详情"
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </section>
  );
}
