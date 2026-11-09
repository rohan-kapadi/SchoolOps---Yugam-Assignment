// MessagesPage — outbox / parent notification log

import { useState, useEffect, useCallback } from "react";
import { MessageSquare, RefreshCw, Filter, Send, AlertCircle, Clock } from "lucide-react";
import { getMessages } from "../api";
import type { OutboxMessage } from "../api";
import { useToast } from "../hooks";
import { StatusBadge, Spinner, EmptyState, useAutoRefresh } from "../components";

export default function MessagesPage() {
  const [messages, setMessages] = useState<OutboxMessage[]>([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState("");
  const { toast } = useToast();

  const load = useCallback(async () => {
    try {
      const data = await getMessages(undefined, statusFilter || undefined);
      setMessages(data);
    } catch {
      toast("error", "Failed to load messages");
    } finally {
      setLoading(false);
    }
  }, [statusFilter, toast]);

  useEffect(() => {
    setLoading(true);
    load();
  }, [load]);

  useAutoRefresh(load, 10000);

  const sent = messages.filter((m) => m.status === "SENT").length;
  const failed = messages.filter((m) => m.status === "FAILED").length;
  const queued = messages.filter((m) => m.status === "QUEUED").length;

  return (
    <div className="page-body">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h2 className="section-title" style={{ marginBottom: 2 }}>
            Parent Message Outbox
          </h2>
          <span className="text-sm text-muted">
            Bilingual (EN/HI) notifications sent to parents after draft approval
          </span>
        </div>
        <button className="btn btn-secondary btn-sm" onClick={load}>
          <RefreshCw size={13} /> Refresh
        </button>
      </div>

      {/* Stats */}
      <div className="grid-3" style={{ gridTemplateColumns: "repeat(3, 1fr)", marginBottom: 20 }}>
        <div className="stat-card">
          <div
            className="stat-icon"
            style={{ background: "var(--success-light)", color: "var(--success)" }}
          >
            <Send size={18} />
          </div>
          <div className="stat-label">Sent</div>
          <div className="stat-value" style={{ color: "var(--success)" }}>
            {sent}
          </div>
        </div>
        <div className="stat-card">
          <div
            className="stat-icon"
            style={{ background: "var(--danger-light)", color: "var(--danger)" }}
          >
            <AlertCircle size={18} />
          </div>
          <div className="stat-label">Failed</div>
          <div className="stat-value" style={{ color: "var(--danger)" }}>
            {failed}
          </div>
        </div>
        <div className="stat-card">
          <div
            className="stat-icon"
            style={{ background: "var(--warning-light)", color: "var(--warning)" }}
          >
            <Clock size={18} />
          </div>
          <div className="stat-label">Queued</div>
          <div className="stat-value" style={{ color: "var(--warning)" }}>
            {queued}
          </div>
        </div>
      </div>

      {/* Filter */}
      <div className="filter-row mb-4">
        <Filter size={14} color="var(--gray-500)" />
        <select
          className="filter-select"
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
        >
          <option value="">All Statuses</option>
          <option value="SENT">Sent</option>
          <option value="QUEUED">Queued</option>
          <option value="FAILED">Failed</option>
        </select>
        {statusFilter && (
          <button className="btn btn-ghost btn-sm" onClick={() => setStatusFilter("")}>
            Clear
          </button>
        )}
      </div>

      {/* Table */}
      {loading ? (
        <div style={{ textAlign: "center", padding: 48 }}>
          <Spinner size={32} />
        </div>
      ) : messages.length === 0 ? (
        <EmptyState
          icon={<MessageSquare />}
          title="No messages yet"
          description="Approve a draft to dispatch bilingual parent notifications."
        />
      ) : (
        <div className="card" style={{ overflow: "hidden" }}>
          <div style={{ overflowX: "auto" }}>
            <table className="table">
              <thead>
                <tr>
                  <th>#</th>
                  <th>Recipient</th>
                  <th>Draft</th>
                  <th>Status</th>
                  <th>Attempts</th>
                  <th>Last Attempt</th>
                  <th>Message Preview</th>
                </tr>
              </thead>
              <tbody>
                {messages.map((m) => (
                  <MessageRow key={m.id} msg={m} />
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

function MessageRow({ msg }: { msg: OutboxMessage }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <>
      <tr
        onClick={() => setExpanded((v) => !v)}
        style={{ cursor: "pointer" }}
      >
        <td className="text-xs text-muted font-mono">{msg.id}</td>
        <td>
          <span
            style={{
              fontFamily: "var(--font-mono)",
              fontSize: 12,
              background: "var(--gray-100)",
              padding: "2px 6px",
              borderRadius: 4,
            }}
          >
            {msg.recipient_id}
          </span>
        </td>
        <td className="text-xs text-muted">#{msg.draft_id}</td>
        <td>
          <StatusBadge status={msg.status} />
        </td>
        <td className="text-xs text-muted">{msg.attempts}/3</td>
        <td className="text-xs text-muted">
          {msg.last_attempt_at ? msg.last_attempt_at.slice(0, 16) : "—"}
        </td>
        <td
          style={{
            maxWidth: 260,
            overflow: "hidden",
            textOverflow: "ellipsis",
            whiteSpace: "nowrap",
            fontSize: 12,
            color: "var(--gray-600)",
          }}
        >
          {msg.message_en}
        </td>
      </tr>
      {expanded && (
        <tr>
          <td colSpan={7} style={{ padding: 0 }}>
            <div style={{ padding: "12px 16px", background: "var(--gray-50)" }}>
              <div style={{ marginBottom: 10 }}>
                <div style={{ fontSize: 11, fontWeight: 600, color: "var(--gray-500)", marginBottom: 4 }}>
                  ENGLISH
                </div>
                <div style={{ fontSize: 13, lineHeight: 1.6 }}>{msg.message_en}</div>
              </div>
              <div>
                <div style={{ fontSize: 11, fontWeight: 600, color: "var(--gray-500)", marginBottom: 4 }}>
                  हिंदी
                </div>
                <div style={{ fontSize: 13, lineHeight: 1.6, fontFamily: "serif" }}>
                  {msg.message_hi}
                </div>
              </div>
            </div>
          </td>
        </tr>
      )}
    </>
  );
}
