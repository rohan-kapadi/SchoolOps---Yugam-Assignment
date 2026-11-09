// DashboardPage — overview of system health and key stats

import { useState, useEffect, useCallback } from "react";
import {
  MessageSquare, FileText, Users, Calendar, TrendingUp, Sun,
  CheckCircle, Clock, AlertTriangle, RefreshCw
} from "lucide-react";
import { getDrafts, getMessages, getStudents, getEvents, checkAgentHealth, checkSchoolHealth } from "../api";
import type { Draft } from "../api";
import { useToast } from "../hooks";
import { StatusBadge, Spinner, HealthDot, useAutoRefresh } from "../components";

interface Stats {
  totalStudents: number;
  totalEvents: number;
  pendingDrafts: number;
  approvedDrafts: number;
  sentMessages: number;
  failedMessages: number;
  recentDrafts: Draft[];
}

export default function DashboardPage() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [agentOk, setAgentOk] = useState<"ok" | "err" | "checking">("checking");
  const [schoolOk, setSchoolOk] = useState<"ok" | "err" | "checking">("checking");
  const [loading, setLoading] = useState(true);
  const { toast } = useToast();

  const checkHealth = useCallback(async () => {
    const [a, s] = await Promise.all([checkAgentHealth(), checkSchoolHealth()]);
    setAgentOk(a ? "ok" : "err");
    setSchoolOk(s ? "ok" : "err");
  }, []);

  const loadStats = useCallback(async () => {
    try {
      const [drafts, msgs, students, events] = await Promise.all([
        getDrafts(),
        getMessages(),
        getStudents(),
        getEvents(),
      ]);
      setStats({
        totalStudents: students.data.length,
        totalEvents: events.data.length,
        pendingDrafts: drafts.filter((d) => d.status === "PENDING").length,
        approvedDrafts: drafts.filter((d) => d.status === "APPROVED").length,
        sentMessages: msgs.filter((m) => m.status === "SENT").length,
        failedMessages: msgs.filter((m) => m.status === "FAILED").length,
        recentDrafts: drafts.slice(-5).reverse(),
      });
    } catch {
      toast("error", "Failed to load dashboard data. Are the servers running?");
    } finally {
      setLoading(false);
    }
  }, [toast]);

  useEffect(() => {
    checkHealth();
    loadStats();
  }, [checkHealth, loadStats]);

  useAutoRefresh(checkHealth, 15000);
  useAutoRefresh(loadStats, 30000);

  const refresh = () => {
    setLoading(true);
    checkHealth();
    loadStats();
  };

  return (
    <div className="page-body">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h2 className="section-title" style={{ marginBottom: 2 }}>
            Dashboard
          </h2>
          <span className="text-sm text-muted">
            SchoolOps AI — Principal command center
          </span>
        </div>
        <button className="btn btn-secondary btn-sm" onClick={refresh} disabled={loading}>
          <RefreshCw size={13} /> Refresh
        </button>
      </div>

      {/* Service health */}
      <div
        style={{
          display: "flex",
          gap: 12,
          padding: "10px 16px",
          background: "white",
          border: "1px solid var(--gray-200)",
          borderRadius: 8,
          marginBottom: 20,
          alignItems: "center",
          flexWrap: "wrap",
        }}
      >
        <span style={{ fontSize: 12, fontWeight: 600, color: "var(--gray-600)" }}>
          Services:
        </span>
        <div className="health-row" style={{ color: "var(--gray-700)" }}>
          <HealthDot status={agentOk} />
          <span style={{ fontSize: 12 }}>Agent API (port 8000)</span>
        </div>
        <div className="health-row" style={{ color: "var(--gray-700)" }}>
          <HealthDot status={schoolOk} />
          <span style={{ fontSize: 12 }}>School API (port 8001)</span>
        </div>
        {(agentOk === "err" || schoolOk === "err") && (
          <span
            style={{
              fontSize: 11,
              color: "var(--danger)",
              marginLeft: "auto",
              fontStyle: "italic",
            }}
          >
            One or more services offline. Start with uvicorn commands.
          </span>
        )}
      </div>

      {loading ? (
        <div style={{ textAlign: "center", padding: 48 }}>
          <Spinner size={36} />
          <p className="text-muted" style={{ marginTop: 12, fontSize: 13 }}>
            Loading dashboard…
          </p>
        </div>
      ) : stats ? (
        <>
          {/* KPI cards */}
          <div
            className="grid-3"
            style={{ gridTemplateColumns: "repeat(3, 1fr)", marginBottom: 20 }}
          >
            <KpiCard
              icon={<Users size={20} />}
              color="#1a56db"
              label="Total Students"
              value={stats.totalStudents}
            />
            <KpiCard
              icon={<Calendar size={20} />}
              color="#7c3aed"
              label="School Events"
              value={stats.totalEvents}
            />
            <KpiCard
              icon={<Clock size={20} />}
              color="#d97706"
              label="Pending Drafts"
              value={stats.pendingDrafts}
              urgent={stats.pendingDrafts > 0}
            />
            <KpiCard
              icon={<CheckCircle size={20} />}
              color="#0e9f6e"
              label="Approved Drafts"
              value={stats.approvedDrafts}
            />
            <KpiCard
              icon={<MessageSquare size={20} />}
              color="#0e9f6e"
              label="Messages Sent"
              value={stats.sentMessages}
            />
            <KpiCard
              icon={<AlertTriangle size={20} />}
              color="#e02424"
              label="Messages Failed"
              value={stats.failedMessages}
              urgent={stats.failedMessages > 0}
            />
          </div>

          {/* Quick start guide + recent drafts */}
          <div className="grid-2">
            <div>
              <div className="section-title" style={{ fontSize: 13 }}>Recent Drafts</div>
              {stats.recentDrafts.length === 0 ? (
                <div className="card">
                  <div
                    style={{
                      padding: "32px 16px",
                      textAlign: "center",
                      color: "var(--gray-500)",
                      fontSize: 13,
                    }}
                  >
                    <Sun size={32} style={{ marginBottom: 8, opacity: 0.4 }} />
                    <p>No drafts yet. Run the morning job to get started.</p>
                  </div>
                </div>
              ) : (
                <div className="card" style={{ overflow: "hidden" }}>
                  {stats.recentDrafts.map((d, i) => (
                    <div
                      key={d.id}
                      style={{
                        padding: "12px 16px",
                        borderBottom:
                          i < stats.recentDrafts.length - 1
                            ? "1px solid var(--gray-100)"
                            : "none",
                        display: "flex",
                        alignItems: "flex-start",
                        justifyContent: "space-between",
                        gap: 8,
                      }}
                    >
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <div
                          style={{
                            fontSize: 12,
                            fontWeight: 600,
                            color: "var(--gray-700)",
                            marginBottom: 2,
                          }}
                        >
                          #{d.id} · {d.type.replace(/_/g, " ")}
                        </div>
                        <div
                          style={{
                            fontSize: 11,
                            color: "var(--gray-500)",
                            overflow: "hidden",
                            textOverflow: "ellipsis",
                            whiteSpace: "nowrap",
                          }}
                        >
                          {d.summary}
                        </div>
                        <div style={{ fontSize: 10, color: "var(--gray-400)", marginTop: 2 }}>
                          {d.date}
                        </div>
                      </div>
                      <StatusBadge status={d.status} />
                    </div>
                  ))}
                </div>
              )}
            </div>

            <div>
              <div className="section-title" style={{ fontSize: 13 }}>Quick Actions</div>
              <div
                className="card"
                style={{ display: "flex", flexDirection: "column", gap: 0, overflow: "hidden" }}
              >
                {[
                  {
                    icon: <Sun size={16} />,
                    color: "#d97706",
                    title: "Run Morning Check",
                    desc: "Trigger 06:00 weather + event analysis",
                    page: "morning",
                  },
                  {
                    icon: <FileText size={16} />,
                    color: "#1a56db",
                    title: "Review Drafts",
                    desc: `${stats.pendingDrafts} pending approval`,
                    page: "drafts",
                  },
                  {
                    icon: <MessageSquare size={16} />,
                    color: "#0e9f6e",
                    title: "View Messages",
                    desc: `${stats.sentMessages} sent, ${stats.failedMessages} failed`,
                    page: "messages",
                  },
                  {
                    icon: <TrendingUp size={16} />,
                    color: "#7c3aed",
                    title: "Ask the AI",
                    desc: "Natural language school queries",
                    page: "ask",
                  },
                ].map((item) => (
                  <a
                    key={item.page}
                    href={`#${item.page}`}
                    onClick={(e) => {
                      e.preventDefault();
                      window.dispatchEvent(
                        new CustomEvent("navigate", { detail: item.page })
                      );
                    }}
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: 12,
                      padding: "14px 16px",
                      borderBottom: "1px solid var(--gray-100)",
                      textDecoration: "none",
                      color: "inherit",
                      transition: "background 0.1s",
                    }}
                    onMouseEnter={(e) =>
                      (e.currentTarget.style.background = "var(--gray-50)")
                    }
                    onMouseLeave={(e) =>
                      (e.currentTarget.style.background = "transparent")
                    }
                  >
                    <div
                      style={{
                        width: 34,
                        height: 34,
                        borderRadius: 8,
                        background: item.color + "1a",
                        color: item.color,
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        flexShrink: 0,
                      }}
                    >
                      {item.icon}
                    </div>
                    <div>
                      <div style={{ fontSize: 13, fontWeight: 600 }}>{item.title}</div>
                      <div style={{ fontSize: 11, color: "var(--gray-500)" }}>{item.desc}</div>
                    </div>
                    <span style={{ marginLeft: "auto", color: "var(--gray-400)", fontSize: 18 }}>›</span>
                  </a>
                ))}
              </div>
            </div>
          </div>
        </>
      ) : null}
    </div>
  );
}

function KpiCard({
  icon,
  color,
  label,
  value,
  urgent,
}: {
  icon: React.ReactNode;
  color: string;
  label: string;
  value: number;
  urgent?: boolean;
}) {
  return (
    <div
      className="stat-card"
      style={{ borderLeft: urgent ? `3px solid ${color}` : undefined }}
    >
      <div
        style={{
          width: 36,
          height: 36,
          borderRadius: 8,
          background: color + "1a",
          color,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          marginBottom: 8,
        }}
      >
        {icon}
      </div>
      <div className="stat-value" style={{ color: urgent ? color : undefined }}>
        {value}
      </div>
      <div className="stat-label">{label}</div>
    </div>
  );
}

