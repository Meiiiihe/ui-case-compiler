import { NavLink, Route, Routes } from "react-router-dom";
import { CaseListPage } from "./pages/CaseListPage";
import { CaseDetailPage } from "./pages/CaseDetailPage";
import { RunDetailPage } from "./pages/RunDetailPage";

export function App() {
  return (
    <div className="app">
      <header className="app-header">
        <div className="brand-block">
          <NavLink to="/" className="brand">
            UI Case Compiler
          </NavLink>
          <span className="brand-subtitle">自然语言 / 录制事件编译控制台</span>
        </div>
        <nav className="top-nav" aria-label="主导航">
          <NavLink to="/" className={({ isActive }) => (isActive ? "nav-link active" : "nav-link")}>
            用例
          </NavLink>
        </nav>
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
