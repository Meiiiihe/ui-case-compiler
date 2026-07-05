import { useState } from "react";
import { compileNl, compileRecording, startRecording, stopRecording } from "../api/cases";
import { useAsync } from "../hooks/useAsync";
import type { ExecutablePlan, RecordingSession } from "../api/types";
import { ErrorBanner } from "./ErrorBanner";

export function CreateCaseForm({ onCreated }: { onCreated: (planId: string) => void }) {
  const [tab, setTab] = useState<"nl" | "recording">("nl");
  const [text, setText] = useState("");
  const [url, setUrl] = useState("");
  const [name, setName] = useState("");
  const [recordingUrl, setRecordingUrl] = useState("");
  const [recordingSession, setRecordingSession] = useState<RecordingSession | null>(null);
  const [showJsonImport, setShowJsonImport] = useState(false);
  const [eventsJson, setEventsJson] = useState("");
  const [localError, setLocalError] = useState<string | null>(null);
  const { error, loading, run } = useAsync<ExecutablePlan | RecordingSession>();

  async function submitNl() {
    setLocalError(null);
    if (!url.trim()) {
      setLocalError("URL 必填");
      return;
    }
    await run(async () => {
      const plan = await compileNl({ text, context: { url }, name: name || undefined });
      onCreated(plan.id);
      return plan;
    });
  }

  async function submitRecording() {
    setLocalError(null);
    let events: Record<string, unknown>[];
    try {
      events = JSON.parse(eventsJson);
    } catch {
      setLocalError("事件 JSON 解析失败");
      return;
    }
    await run(async () => {
      const plan = await compileRecording({ events, name: name || "Recorded Flow" });
      onCreated(plan.id);
      return plan;
    });
  }

  async function startLiveRecording() {
    setLocalError(null);
    if (!recordingUrl.trim()) {
      setLocalError("起始 URL 必填");
      return;
    }
    await run(async () => {
      const session = await startRecording({
        url: recordingUrl.trim(),
        name: name || "Recorded Flow",
      });
      setRecordingSession(session);
      return session;
    });
  }

  async function stopLiveRecording() {
    if (!recordingSession) return;
    setLocalError(null);
    await run(async () => {
      const plan = await stopRecording(recordingSession.session_id);
      setRecordingSession(null);
      onCreated(plan.id);
      return plan;
    });
  }

  function useRecordingSample() {
    setEventsJson(
      JSON.stringify(
        [
          {
            type: "navigation",
            timestamp: 1,
            url: "https://example.test/login",
          },
          {
            type: "click",
            timestamp: 2,
            element: { tag: "button", role: "button", text: "Login" },
          },
        ],
        null,
        2,
      ),
    );
  }

  return (
    <section className="panel create-panel">
      <div className="section-heading">
        <div>
          <p className="eyebrow">创建入口</p>
          <h2>创建用例</h2>
        </div>
        <span className="hint">编译后会保存为可执行计划</span>
      </div>
      <div className="segmented" role="tablist" aria-label="创建方式">
        <button
          className={tab === "nl" ? "segment active" : "segment"}
          onClick={() => setTab("nl")}
          type="button"
        >
          自然语言
        </button>
        <button
          className={tab === "recording" ? "segment active" : "segment"}
          onClick={() => setTab("recording")}
          type="button"
        >
          实时录制
        </button>
      </div>
      <ErrorBanner message={localError ?? error} />
      <label className="field">
        <span>名称</span>
        <input
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="例如：登录流程回归"
        />
      </label>
      {tab === "nl" ? (
        <div className="form-grid">
          <label className="field field-wide">
            <span>自然语言用例</span>
            <textarea
              value={text}
              onChange={(e) => setText(e.target.value)}
              rows={5}
              placeholder="打开登录页，输入用户名和密码，点击登录，并验证出现欢迎文案。"
            />
          </label>
          <label className="field">
            <span>URL</span>
            <input
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder="https://example.test/login"
            />
          </label>
          <button className="primary-action" onClick={submitNl} disabled={loading} type="button">
            从自然语言创建
          </button>
        </div>
      ) : (
        <div className="form-grid">
          <div className="recording-guide field-wide">
            <strong>实时录制流程</strong>
            <ol>
              <li>输入起始 URL，点击开始录制。</li>
              <li>后端会打开一个 Playwright 控制的浏览器窗口。</li>
              <li>在浏览器里完成测试流程后，回到这里点击停止并生成步骤。</li>
            </ol>
          </div>
          <label className="field field-wide">
            <span>起始 URL</span>
            <input
              value={recordingUrl}
              onChange={(e) => setRecordingUrl(e.target.value)}
              placeholder="https://example.test/login 或 file:///F:/.../login.html"
              disabled={Boolean(recordingSession)}
            />
          </label>
          {recordingSession && (
            <div className="recording-status field-wide">
              <span className="recording-dot" />
              正在录制：<code>{recordingSession.session_id}</code>
              <span>{recordingSession.url}</span>
            </div>
          )}
          <div className="button-row">
            {!recordingSession ? (
              <button
                className="primary-action"
                onClick={startLiveRecording}
                disabled={loading}
                type="button"
              >
                开始录制
              </button>
            ) : (
              <button
                className="primary-action danger-action"
                onClick={stopLiveRecording}
                disabled={loading}
                type="button"
              >
                停止并生成步骤
              </button>
            )}
            <button
              className="secondary-action"
              onClick={() => setShowJsonImport((value) => !value)}
              type="button"
            >
              {showJsonImport ? "收起 JSON 导入" : "高级：导入事件 JSON"}
            </button>
          </div>
          {showJsonImport && (
            <div className="advanced-import field-wide">
              <label className="field">
                <span>事件 JSON</span>
                <textarea
                  value={eventsJson}
                  onChange={(e) => setEventsJson(e.target.value)}
                  rows={8}
                  spellCheck={false}
                  placeholder='[{"type":"navigation","timestamp":1,"url":"https://example.test"}]'
                />
              </label>
              <div className="button-row">
                <button className="secondary-action" onClick={useRecordingSample} type="button">
                  填入示例
                </button>
                <button
                  className="secondary-action"
                  onClick={submitRecording}
                  disabled={loading}
                  type="button"
                >
                  导入 JSON 并创建
                </button>
              </div>
            </div>
          )}
        </div>
      )}
    </section>
  );
}
