// AskPage — conversational agent interface

import { useState, useRef, useEffect } from "react";
import { Send, Bot, User, ChevronDown, ChevronUp, Zap, Info } from "lucide-react";
import ReactMarkdown from "react-markdown";
import { askAgent } from "../api";
import type { AskResponse } from "../api";
import { useToast } from "../hooks";
import { AutoTextarea, TypingIndicator } from "../components";

interface Message {
  id: number;
  role: "user" | "assistant";
  text: string;
  response?: AskResponse;
  time: Date;
  error?: boolean;
}

const SUGGESTED = [
  "What's the weather forecast for Sports Day?",
  "Who has been absent for 3+ consecutive days?",
  "List all outdoor events this week",
  "Should we consider closing school tomorrow?",
  "Which bus routes may be delayed?",
  "Find students in class 7A",
];

let msgId = 0;

export default function AskPage() {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: 0,
      role: "assistant",
      text: "Hello! I'm SchoolOps AI, your intelligent school assistant. Ask me anything about students, attendance, weather impact on events, or bus routes.",
      time: new Date(),
    },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const { toast } = useToast();

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  const send = async (question: string) => {
    const q = question.trim();
    if (!q || loading) return;
    setInput("");

    const userMsg: Message = { id: ++msgId, role: "user", text: q, time: new Date() };
    setMessages((m) => [...m, userMsg]);
    setLoading(true);

    try {
      const res = await askAgent(q);
      setMessages((m) => [
        ...m,
        { id: ++msgId, role: "assistant", text: res.answer, response: res, time: new Date() },
      ]);
    } catch (e: unknown) {
      const err = e instanceof Error ? e.message : String(e);
      toast("error", `Agent error: ${err}`);
      setMessages((m) => [
        ...m,
        {
          id: ++msgId,
          role: "assistant",
          text: `⚠️ Error: ${err}. Make sure the agent server is running on port 8000.`,
          time: new Date(),
          error: true,
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="chat-container" style={{ height: "100%" }}>
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
                {msg.time.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
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
  item: { tool: string; input: unknown; output: unknown };
}) {
  const [open, setOpen] = useState(false);
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
        </span>
        {open ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
      </button>
      {open && (
        <div className="trace-body">
          {"→ input: " + JSON.stringify(item.input, null, 2) + "\n\n← output: " + JSON.stringify(item.output, null, 2)}
        </div>
      )}
    </div>
  );
}

