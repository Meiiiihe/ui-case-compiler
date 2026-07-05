import { Link, Route, Routes } from "react-router-dom";
import { CaseListPage } from "./pages/CaseListPage";
import { CaseDetailPage } from "./pages/CaseDetailPage";
import { RunDetailPage } from "./pages/RunDetailPage";

export function App() {
  return (
    <div className="app">
      <header className="app-header">
        <Link to="/">UI Case Compiler</Link>
      </header>
      <main className="app-main">
        <Routes>
          <Route path="/" element={<CaseListPage />} />
          <Route path="/cases/:caseId" element={<CaseDetailPage />} />
          <Route path="/runs/:runId" element={<RunDetailPage />} />
        </Routes>
      </main>
    </div>
  );
}
