// DraftsPage — principal approval workflow

import { useState, useEffect, useCallback } from "react";
import {
  FileText, CheckCircle, XCircle, RefreshCw, Edit3, Calendar, Filter, Eye, MessageSquare
} from "lucide-react";
import {
  getDrafts, approveDraft, rejectDraft, updateDraft, getMessages
} from "../api";
import type { Draft, OutboxMessage } from "../api";
import { useToast } from "../hooks";
import { StatusBadge, Spinner, EmptyState, useAutoRefresh } from "../components";

export default function DraftsPage() {
  const [drafts, setDrafts] = useState<Draft[]>([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState("");
  const [dateFilter, setDateFilter] = useState("");
  const [selected, setSelected] = useState<Draft | null>(null);
  const { toast } = useToast();

  const load = useCallback(async () => {
    try {
      const data = await getDrafts(statusFilter || undefined, dateFilter || undefined);
      setDrafts(data);
    } catch {
      toast("error", "Failed to load drafts");
    } finally {
      setLoading(false);
    }
  }, [statusFilter, dateFilter, toast]);

  useEffect(() => {
    setLoading(true);
    load();
  }, [load]);

  useAutoRefresh(load, 15000);

  const pending = drafts.filter((d) => d.status === "PENDING").length;

  return (
    <div className="page-body">
      {/* Header row */}
      <div className="flex items-center justify-between mb-4">
        <div>
          <h2 className="section-title" style={{ marginBottom: 2 }}>
            Operational Drafts
          </h2>
          <span className="text-sm text-muted">
            Principal review and approval of AI-generated alerts
          </span>
        </div>
        <button className="btn btn-secondary btn-sm" onClick={load}>
          <RefreshCw size={13} />
          Refresh
        </button>
      </div>

      {/* Filters */}
      <div className="filter-row mb-4">
        <Filter size={14} color="var(--gray-500)" />
        <select
          className="filter-select"
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
        >
          <option value="">All Statuses</option>
          <option value="PENDING">Pending</option>
          <option value="APPROVED">Approved</option>
          <option value="REJECTED">Rejected</option>
          <option value="ALL_CLEAR">All Clear</option>
        </select>
        <input
          type="date"
          className="filter-select"
          value={dateFilter}
          onChange={(e) => setDateFilter(e.target.value)}
        />
        {(statusFilter || dateFilter) && (
          <button
            className="btn btn-ghost btn-sm"
            onClick={() => { setStatusFilter(""); setDateFilter(""); }}
          >
            Clear
          </button>
        )}
        {pending > 0 && (
          <span className="badge badge-pending" style={{ marginLeft: "auto" }}>
            {pending} pending approval
          </span>
        )}
      </div>

      {/* Stats row */}
      <DraftStats drafts={drafts} />

      <div style={{ marginTop: 20 }}>
        {loading ? (
          <div style={{ textAlign: "center", padding: 48 }}>
            <Spinner size={32} />
          </div>
        ) : drafts.length === 0 ? (
          <EmptyState
            icon={<FileText />}
            title="No drafts found"
            description="Run the morning job to generate operational drafts."
          />
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            {drafts.map((d) => (
              <DraftCard
                key={d.id}
                draft={d}
                onRefresh={load}
                onSelect={() => setSelected(d)}
              />
            ))}
          </div>
        )}
      </div>

      {selected && (
        <DraftDetailPanel
          draft={selected}
          onClose={() => setSelected(null)}
          onRefresh={() => { load(); setSelected(null); }}
        />
      )}
    </div>
  );
}

// ─── Stat cards ───────────────────────────────────────────────────────────────

function DraftStats({ drafts }: { drafts: Draft[] }) {
  const counts = { PENDING: 0, APPROVED: 0, REJECTED: 0, ALL_CLEAR: 0 };
  drafts.forEach((d) => {
    counts[d.status as keyof typeof counts] = (counts[d.status as keyof typeof counts] || 0) + 1;
  });

  return (
    <div className="grid-3" style={{ gridTemplateColumns: "repeat(4, 1fr)" }}>
      {(["PENDING", "APPROVED", "REJECTED", "ALL_CLEAR"] as const).map((s) => (
        <div key={s} className="stat-card">
          <div className="stat-label">{s.replace("_", " ")}</div>
          <div className="stat-value">{counts[s]}</div>
        </div>
      ))}
    </div>
  );
}

// ─── Draft card ───────────────────────────────────────────────────────────────

function DraftCard({
  draft,
  onRefresh,
  onSelect,
}: {
  draft: Draft;
  onRefresh: () => void;
  onSelect: () => void;
}) {
  const [busy, setBusy] = useState(false);
  const { toast } = useToast();

  const approve = async () => {
    setBusy(true);
    try {
      await approveDraft(draft.id);
      toast("success", `Draft #${draft.id} approved — messages dispatched`);
      onRefresh();
    } catch (e: unknown) {
      toast("error", e instanceof Error ? e.message : "Approve failed");
    } finally {
      setBusy(false);
    }
  };

  const reject = async () => {
    setBusy(true);
    try {
      await rejectDraft(draft.id);
      toast("info", `Draft #${draft.id} rejected`);
      onRefresh();
    } catch (e: unknown) {
      toast("error", e instanceof Error ? e.message : "Reject failed");
    } finally {
      setBusy(false);
    }
  };

  const typeColors: Record<string, string> = {
    PRINCIPAL_SUMMARY: "#1a56db",
    ROUTE_DELAY: "#d97706",
    EVENT_OUTDOOR: "#7c3aed",
    ALL_CLEAR: "#0e9f6e",
  };

  return (
    <div className="draft-card">
      <div className="draft-card-header">
        <div>
          <div
            className="draft-type"
            style={{ color: typeColors[draft.type] ?? "var(--primary)" }}
          >
            {draft.type.replace(/_/g, " ")}
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginTop: 4 }}>
            <Calendar size={12} color="var(--gray-400)" />
            <span className="text-xs text-muted">{draft.date}</span>
            {draft.target_id && (
              <span className="text-xs" style={{ color: "var(--gray-600)" }}>
                · Target: <strong>{draft.target_id}</strong>
              </span>
            )}
          </div>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <span className="text-xs text-muted">#{draft.id}</span>
          <StatusBadge status={draft.status} />
        </div>
      </div>

      <div className="draft-card-body">
        <p className="draft-summary">{draft.summary}</p>
        {draft.principal_note && (
          <p className="draft-note">📝 {draft.principal_note}</p>
        )}
      </div>

      <div className="draft-card-footer">
        {draft.status === "PENDING" && (
          <>
            <button className="btn btn-success btn-sm" onClick={approve} disabled={busy}>
              {busy ? <Spinner size={12} /> : <CheckCircle size={13} />}
              Approve
            </button>
            <button className="btn btn-danger btn-sm" onClick={reject} disabled={busy}>
              {busy ? <Spinner size={12} /> : <XCircle size={13} />}
              Reject
            </button>
          </>
        )}
        <button className="btn btn-secondary btn-sm" onClick={onSelect} style={{ marginLeft: "auto" }}>
          <Eye size={13} />
          Details
        </button>
      </div>
    </div>
  );
}

// ─── Draft detail panel ───────────────────────────────────────────────────────

function DraftDetailPanel({
  draft,
  onClose,
  onRefresh,
}: {
  draft: Draft;
  onClose: () => void;
  onRefresh: () => void;
}) {
  const [editMode, setEditMode] = useState(false);
  const [summary, setSummary] = useState(draft.summary);
  const [note, setNote] = useState(draft.principal_note ?? "");
  const [messages, setMessages] = useState<OutboxMessage[]>([]);
  const [busy, setBusy] = useState(false);
  const [msgLoading, setMsgLoading] = useState(false);
  const { toast } = useToast();

  useEffect(() => {
    setMsgLoading(true);
    getMessages(draft.id)
      .then(setMessages)
      .catch(() => {})
      .finally(() => setMsgLoading(false));
  }, [draft.id]);

  const save = async () => {
    setBusy(true);
    try {
      await updateDraft(draft.id, { summary, principal_note: note });
      toast("success", "Draft updated");
      setEditMode(false);
      onRefresh();
    } catch (e: unknown) {
      toast("error", e instanceof Error ? e.message : "Update failed");
    } finally {
      setBusy(false);
    }
  };

  const approve = async () => {
    setBusy(true);
    try {
      await approveDraft(draft.id);
      toast("success", `Draft #${draft.id} approved`);
      onRefresh();
    } catch (e: unknown) {
      toast("error", e instanceof Error ? e.message : "Approve failed");
    } finally {
      setBusy(false);
    }
  };

  const reject = async () => {
    setBusy(true);
    try {
      await rejectDraft(draft.id);
      toast("info", `Draft #${draft.id} rejected`);
      onRefresh();
    } catch (e: unknown) {
      toast("error", e instanceof Error ? e.message : "Reject failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="detail-panel" onClick={(e) => e.stopPropagation()}>
        <div className="detail-panel-header">
          <div>
            <div style={{ fontSize: 15, fontWeight: 600 }}>Draft #{draft.id}</div>
            <StatusBadge status={draft.status} />
          </div>
          <button className="btn btn-ghost btn-sm" onClick={onClose}>
            ✕
          </button>
        </div>

        <div className="detail-panel-body">
          {/* Meta */}
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "1fr 1fr",
              gap: 10,
              marginBottom: 16,
              fontSize: 12,
              color: "var(--gray-600)",
            }}
          >
            <div>
              <strong>Type</strong>
              <div>{draft.type}</div>
            </div>
            <div>
              <strong>Date</strong>
              <div>{draft.date}</div>
            </div>
            {draft.target_id && (
              <div>
                <strong>Target</strong>
                <div>{draft.target_id}</div>
              </div>
            )}
            <div>
              <strong>Created</strong>
              <div>{draft.created_at?.slice(0, 16) ?? "—"}</div>
            </div>
          </div>

          <div className="divider" />

          {/* Summary */}
          <div style={{ marginBottom: 12 }}>
            <div
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                marginBottom: 6,
              }}
            >
              <strong style={{ fontSize: 13 }}>Summary</strong>
              {draft.status === "PENDING" && (
                <button
                  className="btn btn-ghost btn-sm"
                  onClick={() => setEditMode((v) => !v)}
                >
                  <Edit3 size={12} />
                  Edit
                </button>
              )}
            </div>
            {editMode ? (
              <textarea
                className="input"
                value={summary}
                onChange={(e) => setSummary(e.target.value)}
                rows={4}
              />
            ) : (
              <p style={{ fontSize: 13, color: "var(--gray-700)", lineHeight: 1.6 }}>{summary}</p>
            )}
          </div>

          <div style={{ marginBottom: 12 }}>
            <strong style={{ fontSize: 13, display: "block", marginBottom: 6 }}>
              Principal Note
            </strong>
            {editMode ? (
              <input
                className="input"
                value={note}
                onChange={(e) => setNote(e.target.value)}
                placeholder="Optional note…"
              />
            ) : (
              <p style={{ fontSize: 13, color: "var(--gray-600)", fontStyle: "italic" }}>
                {draft.principal_note ?? "No note added"}
              </p>
            )}
          </div>

          {editMode && (
            <div style={{ display: "flex", gap: 8, marginBottom: 12 }}>
              <button className="btn btn-primary btn-sm" onClick={save} disabled={busy}>
                {busy ? <Spinner size={12} /> : null}
                Save changes
              </button>
              <button
                className="btn btn-secondary btn-sm"
                onClick={() => { setEditMode(false); setSummary(draft.summary); setNote(draft.principal_note ?? ""); }}
              >
                Cancel
              </button>
            </div>
          )}

          <div className="divider" />

          {/* Messages */}
          <div>
            <div
              style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 10 }}
            >
              <MessageSquare size={14} />
              <strong style={{ fontSize: 13 }}>Parent Messages</strong>
              {messages.length > 0 && (
                <span
                  className="badge badge-pending"
                  style={{ marginLeft: "auto" }}
                >
                  {messages.length}
                </span>
              )}
            </div>

            {msgLoading ? (
              <Spinner />
            ) : messages.length === 0 ? (
              <p className="text-sm text-muted">
                {draft.type === "PRINCIPAL_SUMMARY" || draft.type === "ALL_CLEAR"
                  ? "No parent messages for this draft type."
                  : "No messages queued yet. Approve draft to dispatch."}
              </p>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                {messages.slice(0, 5).map((m) => (
                  <div
                    key={m.id}
                    style={{
                      border: "1px solid var(--gray-200)",
                      borderRadius: 6,
                      overflow: "hidden",
                    }}
                  >
                    <div
                      style={{
                        padding: "8px 12px",
                        background: "var(--gray-50)",
                        display: "flex",
                        justifyContent: "space-between",
                        fontSize: 12,
                      }}
                    >
                      <span className="font-mono">{m.recipient_id}</span>
                      <StatusBadge status={m.status} />
                    </div>
                    <div style={{ padding: "8px 12px", fontSize: 12, color: "var(--gray-700)" }}>
                      {m.message_en}
                    </div>
                    <div
                      style={{
                        padding: "6px 12px",
                        fontSize: 12,
                        color: "var(--gray-600)",
                        borderTop: "1px solid var(--gray-100)",
                        fontFamily: "serif",
                      }}
                    >
                      {m.message_hi}
                    </div>
                  </div>
                ))}
                {messages.length > 5 && (
                  <p className="text-sm text-muted">
                    + {messages.length - 5} more messages
                  </p>
                )}
              </div>
            )}
          </div>
        </div>

        {draft.status === "PENDING" && (
          <div className="detail-panel-footer">
            <button className="btn btn-success" onClick={approve} disabled={busy} style={{ flex: 1 }}>
              {busy ? <Spinner size={14} /> : <CheckCircle size={15} />}
              Approve & Send
            </button>
            <button className="btn btn-danger" onClick={reject} disabled={busy} style={{ flex: 1 }}>
              {busy ? <Spinner size={14} /> : <XCircle size={15} />}
              Reject
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

