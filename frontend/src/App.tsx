// Main App shell with sidebar navigation

import { useState, useEffect } from "react";
import {
  LayoutDashboard, MessageSquare, FileText, Sun, Users, Bot
} from "lucide-react";
import { getDrafts, checkAgentHealth, checkSchoolHealth } from "./api";
import { ToastProvider } from "./hooks";
import { ToastContainer, HealthDot } from "./components";

import DashboardPage from "./pages/DashboardPage";
import AskPage from "./pages/AskPage";
import DraftsPage from "./pages/DraftsPage";
import MessagesPage from "./pages/MessagesPage";
import MorningJobPage from "./pages/MorningJobPage";
import SchoolDataPage from "./pages/SchoolDataPage";

import "./styles.css";

type Page = "dashboard" | "ask" | "drafts" | "messages" | "morning" | "school";

const NAV: { key: Page; label: string; icon: React.ReactNode }[] = [
  { key: "dashboard", label: "Dashboard", icon: <LayoutDashboard size={16} /> },
  { key: "ask", label: "Ask AI", icon: <Bot size={16} /> },
  { key: "drafts", label: "Drafts", icon: <FileText size={16} /> },
  { key: "messages", label: "Messages", icon: <MessageSquare size={16} /> },
  { key: "morning", label: "Morning Job", icon: <Sun size={16} /> },
  { key: "school", label: "School Data", icon: <Users size={16} /> },
];

const PAGE_TITLES: Record<Page, { title: string; sub: string }> = {
  dashboard: { title: "Dashboard", sub: "Overview of your school operations" },
  ask: { title: "Ask AI", sub: "Natural language queries powered by Gemini + school data" },
  drafts: { title: "Draft Approvals", sub: "Review and approve AI-generated operational alerts" },
  messages: { title: "Parent Messages", sub: "Bilingual notification outbox" },
  morning: { title: "Morning Job", sub: "Trigger the 06:00 operational workflow" },
  school: { title: "School Data", sub: "Browse students, routes, events, and policy" },
};

export default function App() {
  const [page, setPage] = useState<Page>("dashboard");
  const [pendingCount, setPendingCount] = useState(0);
  const [agentOk, setAgentOk] = useState<"ok" | "err" | "checking">("checking");
  const [schoolOk, setSchoolOk] = useState<"ok" | "err" | "checking">("checking");

  // Poll pending drafts count for badge
  useEffect(() => {
    const poll = async () => {
      try {
        const drafts = await getDrafts("PENDING");
        setPendingCount(drafts.length);
      } catch {}
    };
    poll();
    const id = setInterval(poll, 15000);
    return () => clearInterval(id);
  }, []);

  // Health check
  useEffect(() => {
    const check = async () => {
      const [a, s] = await Promise.all([checkAgentHealth(), checkSchoolHealth()]);
      setAgentOk(a ? "ok" : "err");
      setSchoolOk(s ? "ok" : "err");
    };
    check();
    const id = setInterval(check, 20000);
    return () => clearInterval(id);
  }, []);

  // Listen for internal navigation events (from dashboard quick actions)
  useEffect(() => {
    const handler = (e: Event) => {
      const page = (e as CustomEvent).detail as Page;
      setPage(page);
    };
    window.addEventListener("navigate", handler);
    return () => window.removeEventListener("navigate", handler);
  }, []);

  const { title, sub } = PAGE_TITLES[page];

  return (
    <ToastProvider>
      <div className="app-shell">
        {/* Sidebar */}
        <nav className="sidebar">
          <div className="sidebar-logo">
            <div className="sidebar-logo-icon">🏫</div>
            <div>
              <div className="sidebar-logo-text">SchoolOps AI</div>
              <div className="sidebar-logo-sub">Principal Dashboard</div>
            </div>
          </div>

          <div className="sidebar-section-label">Navigation</div>

          {NAV.map((n) => (
            <button
              key={n.key}
              className={`nav-item ${page === n.key ? "active" : ""}`}
              onClick={() => setPage(n.key)}
            >
              {n.icon}
              {n.label}
              {n.key === "drafts" && pendingCount > 0 && (
                <span className="nav-badge">{pendingCount}</span>
              )}
            </button>
          ))}

          {/* Health panel */}
          <div className="health-panel">
            <div style={{ fontSize: 10, fontWeight: 600, letterSpacing: "0.08em", color: "var(--gray-500)", textTransform: "uppercase", marginBottom: 8 }}>
              Services
            </div>
            <div className="health-row">
              <HealthDot status={agentOk} />
              <span>Agent :8000</span>
            </div>
            <div className="health-row">
              <HealthDot status={schoolOk} />
              <span>School :8001</span>
            </div>
          </div>
        </nav>

        {/* Main content */}
        <div className="main-content">
          <header className="page-header">
            <div>
              <h1>{title}</h1>
              <div className="page-header-sub">{sub}</div>
            </div>
          </header>

          <div
            style={{
              flex: 1,
              overflow: "hidden",
              display: "flex",
              flexDirection: "column",
            }}
          >
            {page === "dashboard" && <DashboardPage />}
            {page === "ask" && (
              <div style={{ flex: 1, overflow: "hidden", display: "flex", flexDirection: "column" }}>
                <AskPage />
              </div>
            )}
            {page === "drafts" && <DraftsPage />}
            {page === "messages" && <MessagesPage />}
            {page === "morning" && <MorningJobPage />}
            {page === "school" && <SchoolDataPage />}
          </div>
        </div>
      </div>

      <ToastContainer />
    </ToastProvider>
  );
}
