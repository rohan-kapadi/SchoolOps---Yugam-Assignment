// AskPage — conversational agent interface

import { useState, useRef, useEffect } from "react";
import { Send, Bot, User, ChevronDown, ChevronUp, Zap, Info, Trash2 } from "lucide-react";
import ReactMarkdown from "react-markdown";
import { askAgent } from "../api";
import type { AskResponse, ToolTraceItem } from "../api";
import { useToast } from "../hooks";
import { AutoTextarea, TypingIndicator } from "../components";

interface Message {
  id: number;
  role: "user" | "assistant";
  text: string;
  response?: AskResponse;
  time: string;
  error?: boolean;
}

const STORAGE_KEY = "schoolops_principal_chat_history";
const STORAGE_VERSION = 2; // bump to invalidate old cached traces

const DEFAULT_WELCOME: Message = {
  id: 0,
  role: "assistant",
  text: "Hello! I'm SchoolOps AI, your intelligent school assistant. Ask me anything about students, attendance, weather impact on events, or bus routes.",
  time: new Date().toISOString(),
};

function loadStoredMessages(): Message[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return [DEFAULT_WELCOME];
    const parsed = JSON.parse(raw);
    // Check version — discard old cache with broken tool traces
    if (!Array.isArray(parsed) || parsed.length === 0) return [DEFAULT_WELCOME];
    if (parsed[0]?._v !== STORAGE_VERSION) return [DEFAULT_WELCOME];
    return parsed;
  } catch {}
  return [DEFAULT_WELCOME];
}

const SUGGESTED = [
  "What's the weather forecast for Sports Day?",
  "Who has been absent for 3+ consecutive days?",
  "List all outdoor events this week",
  "Should we consider closing school tomorrow?",
  "Which bus routes may be delayed?",
  "Find students in class 7A",
];

export default function AskPage() {
  const [messages, setMessages] = useState<Message[]>(loadStoredMessages);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const { toast } = useToast();

  // Persist messages whenever they change (stamp version on first message)
  useEffect(() => {
    try {
      const toStore = messages.map((m, i) => (i === 0 ? { ...m, _v: STORAGE_VERSION } : m));
      localStorage.setItem(STORAGE_KEY, JSON.stringify(toStore));
    } catch {}
  }, [messages]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  const clearHistory = () => {
    if (window.confirm("Clear all conversation history?")) {
      const reset = [
        {
          id: Date.now(),
          role: "assistant" as const,
          text: "Conversation cleared. How can I assist you today, Principal?",
          time: new Date().toISOString(),
        },
      ];
      setMessages(reset);
      try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(reset));
      } catch {}
      toast("info", "Chat history cleared");
    }
  };

  const send = async (question: string) => {
    const q = question.trim();
    if (!q || loading) return;
    setInput("");

    const nowIso = new Date().toISOString();
    const userMsg: Message = { id: Date.now(), role: "user", text: q, time: nowIso };
    setMessages((m) => [...m, userMsg]);
    setLoading(true);

    try {
      const res = await askAgent(q);
      setMessages((m) => [
        ...m,
        { id: Date.now() + 1, role: "assistant", text: res.answer, response: res, time: new Date().toISOString() },
      ]);
    } catch (e: unknown) {
      const err = e instanceof Error ? e.message : String(e);
      toast("error", `Agent error: ${err}`);
      setMessages((m) => [
        ...m,
        {
          id: Date.now() + 1,
          role: "assistant",
          text: `⚠️ Error: ${err}. Make sure the agent server is running on port 8000.`,
          time: new Date().toISOString(),
          error: true,
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="chat-container" style={{ height: "100%" }}>
      {/* Persistent chat bar */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          padding: "8px 16px",
          background: "white",
          borderBottom: "1px solid var(--gray-200)",
          fontSize: 12,
        }}
      >
        <span style={{ color: "var(--gray-500)", fontWeight: 500 }}>
          💬 Conversation auto-saved ({messages.length} message{messages.length === 1 ? "" : "s"})
        </span>
        {messages.length > 1 && (
          <button
            onClick={clearHistory}
            className="btn btn-ghost btn-sm"
            style={{ fontSize: 11, color: "var(--danger)", display: "flex", alignItems: "center", gap: 4 }}
          >
            <Trash2 size={12} />
            Clear Chat
          </button>
        )}
      </div>

      <div className="chat-messages">
        {messages.map((msg) => (
          <div key={msg.id} className={`chat-bubble ${msg.role}`}>
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: 6,
                marginBottom: 4,
                flexDirection: msg.role === "user" ? "row-reverse" : "row",
              }}
            >
              <div
                style={{
                  width: 24,
                  height: 24,
                  borderRadius: "50%",
                  background: msg.role === "user" ? "var(--primary)" : "var(--gray-200)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  flexShrink: 0,
                }}
              >
                {msg.role === "user" ? (
                  <User size={12} color="white" />
                ) : (
                  <Bot size={12} color="var(--gray-600)" />
                )}
              </div>
              <span className="bubble-time">
                {new Date(msg.time).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
              </span>
            </div>

            <div className={`bubble-content ${msg.error ? "text-danger" : ""}`}>
              {msg.role === "assistant" ? (
                <div className="md-answer">
                  <ReactMarkdown>{msg.text}</ReactMarkdown>
                </div>
              ) : (
                msg.text
              )}
            </div>

            {/* Tool trace */}
            {msg.response && msg.response.tool_trace.length > 0 && (
              <ToolTrace trace={msg.response.tool_trace} sources={msg.response.sources} />
            )}
          </div>
        ))}

        {loading && (
          <div className="chat-bubble assistant">
            <TypingIndicator />
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* Suggested prompts (shown only when no conversation yet) */}
      {messages.length <= 1 && (
        <div className="suggested-prompts">
          {SUGGESTED.map((p) => (
            <button key={p} className="prompt-chip" onClick={() => send(p)}>
              {p}
            </button>
          ))}
        </div>
      )}

      <div className="chat-input-row">
        <AutoTextarea
          value={input}
          onChange={setInput}
          onEnter={() => send(input)}
          placeholder="Ask a question… (Enter to send, Shift+Enter for newline)"
          disabled={loading}
        />
        <button
          className="btn btn-primary"
          onClick={() => send(input)}
          disabled={loading || !input.trim()}
          style={{ height: 44, flexShrink: 0 }}
        >
          {loading ? (
            <span className="spinner" style={{ width: 14, height: 14 }} />
          ) : (
            <Send size={15} />
          )}
        </button>
      </div>
    </div>
  );
}

// ─── Tool Trace component ─────────────────────────────────────────────────────

function ToolTrace({
  trace,
  sources,
}: {
  trace: AskResponse["tool_trace"];
  sources: string[];
}) {
  const [open, setOpen] = useState(false);

  return (
    <div style={{ marginTop: 6, maxWidth: "100%" }}>
      <button
        onClick={() => setOpen((v) => !v)}
        style={{
          display: "flex",
          alignItems: "center",
          gap: 5,
          background: "none",
          border: "1px solid var(--gray-200)",
          borderRadius: 6,
          padding: "4px 10px",
          fontSize: 11,
          color: "var(--gray-500)",
          cursor: "pointer",
          fontFamily: "var(--font)",
        }}
      >
        <Zap size={11} />
        {trace.length} tool call{trace.length !== 1 ? "s" : ""}
        {open ? <ChevronUp size={11} /> : <ChevronDown size={11} />}
      </button>

      {open && (
        <div style={{ marginTop: 6, display: "flex", flexDirection: "column", gap: 4 }}>
          {trace.map((t, i) => (
            <TraceItem key={i} index={i} item={t} />
          ))}
          {sources.length > 0 && (
            <div className="sources-list">
              <span style={{ fontSize: 11, color: "var(--gray-500)" }}>
                <Info size={11} style={{ display: "inline", marginRight: 4 }} />
                Sources:
              </span>
              {sources.map((s) => (
                <span key={s} className="source-tag">
                  {s}
                </span>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function TraceItem({
  index,
  item,
}: {
  index: number;
  item: ToolTraceItem;
}) {
  const [open, setOpen] = useState(false);
  const inputData = item.input ?? item.args ?? null;
  const outputData = item.output ?? item.result ?? (item.status ? { status: item.status } : null);

  return (
    <div className="trace-item">
      <button
        className="trace-header"
        style={{ width: "100%", border: "none", fontFamily: "var(--font)", justifyContent: "space-between" }}
        onClick={() => setOpen((v) => !v)}
      >
        <span>
          <span style={{ color: "var(--primary)", marginRight: 6 }}>#{index + 1}</span>
          <span style={{ fontFamily: "var(--font-mono)", fontSize: 11 }}>{item.tool}</span>
          {item.status && (
            <span
              style={{
                marginLeft: 8,
                fontSize: 10,
                padding: "1px 6px",
                borderRadius: 4,
                background: item.status === "ok" ? "var(--success-light)" : "var(--danger-light)",
                color: item.status === "ok" ? "var(--success)" : "var(--danger)",
                textTransform: "uppercase",
              }}
            >
              {item.status}
            </span>
          )}
        </span>
        {open ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
      </button>
      {open && (
        <div className="trace-body">
          {"→ input:\n" + (inputData != null ? JSON.stringify(inputData, null, 2) : "(no args)") + "\n\n← output:\n" + (outputData != null ? JSON.stringify(outputData, null, 2) : "(no output)")}
        </div>
      )}
    </div>
  );
}

