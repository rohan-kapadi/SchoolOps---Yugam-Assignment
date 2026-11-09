// Shared UI components

import { ReactNode, useState, useEffect } from "react";
import { X, CheckCircle, XCircle, Info, ChevronDown, ChevronUp } from "lucide-react";
import { useToast } from "./hooks";

// ─── Toast renderer ───────────────────────────────────────────────────────────

export function ToastContainer() {
  const { toasts, dismiss } = useToast();
  if (!toasts.length) return null;
  return (
    <div className="toast-container">
      {toasts.map((t) => (
        <div key={t.id} className={`toast toast-${t.type}`}>
          {t.type === "success" && <CheckCircle size={16} color="var(--success)" />}
          {t.type === "error" && <XCircle size={16} color="var(--danger)" />}
          {t.type === "info" && <Info size={16} color="var(--primary)" />}
          <span style={{ flex: 1 }}>{t.message}</span>
          <button
            onClick={() => dismiss(t.id)}
            style={{ background: "none", border: "none", cursor: "pointer", color: "var(--gray-400)" }}
          >
            <X size={14} />
          </button>
        </div>
      ))}
    </div>
  );
}

// ─── Status Badge ─────────────────────────────────────────────────────────────

export function StatusBadge({ status }: { status: string }) {
  const cls = `badge badge-${status.toLowerCase().replace(/_/g, "_")}`;
  return <span className={cls}>{status.replace(/_/g, " ")}</span>;
}

// ─── Spinner ─────────────────────────────────────────────────────────────────

export function Spinner({ size = 18 }: { size?: number }) {
  return (
    <span
      className="spinner"
      style={{ width: size, height: size, borderWidth: size < 16 ? 1.5 : 2 }}
    />
  );
}

// ─── Empty state ──────────────────────────────────────────────────────────────

export function EmptyState({
  icon,
  title,
  description,
  action,
}: {
  icon: ReactNode;
  title: string;
  description?: string;
  action?: ReactNode;
}) {
  return (
    <div className="empty-state">
      {icon}
      <h3>{title}</h3>
      {description && <p>{description}</p>}
      {action && <div style={{ marginTop: 16 }}>{action}</div>}
    </div>
  );
}

// ─── Collapsible section ──────────────────────────────────────────────────────

export function Collapsible({
  label,
  children,
  defaultOpen = false,
  badge,
}: {
  label: string;
  children: ReactNode;
  defaultOpen?: boolean;
  badge?: ReactNode;
}) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div style={{ border: "1px solid var(--gray-200)", borderRadius: 6, overflow: "hidden" }}>
      <button
        className="trace-header"
        style={{ width: "100%", border: "none", fontFamily: "var(--font)", justifyContent: "space-between" }}
        onClick={() => setOpen((v) => !v)}
      >
        <span style={{ display: "flex", alignItems: "center", gap: 6 }}>
          {label}
          {badge}
        </span>
        {open ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
      </button>
      {open && children}
    </div>
  );
}

// ─── Typing indicator ─────────────────────────────────────────────────────────

export function TypingIndicator() {
  return (
    <div className="chat-bubble assistant">
      <div className="typing-dots">
        <div className="typing-dot" />
        <div className="typing-dot" />
        <div className="typing-dot" />
      </div>
    </div>
  );
}

// ─── Auto-resize textarea ─────────────────────────────────────────────────────

export function AutoTextarea({
  value,
  onChange,
  onEnter,
  placeholder,
  disabled,
}: {
  value: string;
  onChange: (v: string) => void;
  onEnter?: () => void;
  placeholder?: string;
  disabled?: boolean;
}) {
  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      onEnter?.();
    }
  };

  return (
    <textarea
      className="input"
      value={value}
      onChange={(e) => onChange(e.target.value)}
      onKeyDown={handleKeyDown}
      placeholder={placeholder}
      disabled={disabled}
      rows={1}
      style={{ resize: "none", overflowY: "hidden" }}
      onInput={(e) => {
        const el = e.currentTarget;
        el.style.height = "auto";
        el.style.height = Math.min(el.scrollHeight, 120) + "px";
      }}
    />
  );
}

// ─── Health dot ───────────────────────────────────────────────────────────────

export function HealthDot({ status }: { status: "ok" | "err" | "checking" }) {
  return <span className={`health-dot ${status}`} />;
}

// ─── Countdown / auto refresh ─────────────────────────────────────────────────

export function useAutoRefresh(callback: () => void, intervalMs: number) {
  useEffect(() => {
    const id = setInterval(callback, intervalMs);
    return () => clearInterval(id);
  }, [callback, intervalMs]);
}

