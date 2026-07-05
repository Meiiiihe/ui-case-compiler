import { useState } from "react";
import { compileNl, compileRecording } from "../api/cases";
import { useAsync } from "../hooks/useAsync";
import type { ExecutablePlan } from "../api/types";
import { ErrorBanner } from "./ErrorBanner";

export function CreateCaseForm({ onCreated }: { onCreated: (planId: string) => void }) {
  const [tab, setTab] = useState<"nl" | "recording">("nl");
  const [text, setText] = useState("");
  const [url, setUrl] = useState("");
  const [name, setName] = useState("");
  const [eventsJson, setEventsJson] = useState("");
  const [localError, setLocalError] = useState<string | null>(null);
  const { error, loading, run } = useAsync<ExecutablePlan>();

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

  return (
    <section>
      <h2>创建用例</h2>
      <div>
        <button className={tab === "nl" ? "tab-active" : ""} onClick={() => setTab("nl")}>
          自然语言
        </button>
        <button
          className={tab === "recording" ? "tab-active" : ""}
          onClick={() => setTab("recording")}
        >
          录制 JSON
        </button>
      </div>
      <ErrorBanner message={localError ?? error} />
      <div>
        <label>
          名称
          <input value={name} onChange={(e) => setName(e.target.value)} />
        </label>
      </div>
      {tab === "nl" ? (
        <div>
          <label>
            自然语言用例
            <textarea value={text} onChange={(e) => setText(e.target.value)} rows={3} />
          </label>
          <label>
            URL
            <input value={url} onChange={(e) => setUrl(e.target.value)} />
          </label>
          <button onClick={submitNl} disabled={loading}>
            从自然语言创建
          </button>
        </div>
      ) : (
        <div>
          <label>
            事件 JSON
            <textarea
              value={eventsJson}
              onChange={(e) => setEventsJson(e.target.value)}
              rows={4}
            />
          </label>
          <button onClick={submitRecording} disabled={loading}>
            从录制创建
          </button>
        </div>
      )}
    </section>
  );
}
