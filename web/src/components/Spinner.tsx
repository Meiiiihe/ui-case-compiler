export function Spinner({ show }: { show: boolean }) {
  if (!show) return null;
  return <div className="spinner">加载中…</div>;
}
