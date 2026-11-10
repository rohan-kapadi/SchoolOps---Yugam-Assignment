// MorningJobPage — trigger the 06:00 workflow manually

import { useState } from "react";
import { Play, Sun, AlertTriangle, CheckCircle } from "lucide-react";
import { triggerMorningJob } from "../api";
import type { MorningJobResult } from "../api";
import { useToast } from "../hooks";
import { Spinner, StatusBadge } from "../components";

export default function MorningJobPage() {
  const [date, setDate] = useState("");
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState<MorningJobResult | null>(null);
  const { toast } = useToast();

  const run = async (simulate: boolean = false) => {
    setRunning(true);
    setResult(null);
    try {
      const res = await triggerMorningJob(date || undefined, simulate);
      setResult(res);
      if (res.alerts_count === 0) {
        toast("success", "Morning check complete — no alerts today (ALL CLEAR)");
      } else {
        toast("info", `Morning check complete — ${res.alerts_count} alert(s) generated`);
      }
    } catch (e: unknown) {
      toast("error", e instanceof Error ? e.message : "Job failed");
    } finally {
      setRunning(false);
    }
  };

  return (
    <div className="page-body" style={{ maxWidth: 640 }}>
      <h2 className="section-title">Morning Operational Check</h2>
      <p className="text-muted" style={{ marginBottom: 24, fontSize: 13 }}>
        Run the 06:00 morning workflow to evaluate weather, AQI, bus routes, and
        outdoor events. Generates PENDING drafts for principal review.
      </p>

      {/* Info boxes */}
      <div style={{ display: "flex", flexDirection: "column", gap: 10, marginBottom: 24 }}>
        <InfoBox
          icon={<Sun size={16} />}
          color="var(--warning)"
          title="What it does"
          body="Fetches today's weather forecast and AQI for Jaipur, evaluates all outdoor events and bus routes, then drafts bilingual parent notifications if any thresholds are breached."
        />
        <InfoBox
          icon={<AlertTriangle size={16} />}
          color="var(--danger)"
          title="Principal approval required"
          body="All generated drafts remain PENDING until you review and approve or reject them from the Drafts page. No messages are sent without approval."
        />
        <InfoBox
          icon={<CheckCircle size={16} />}
          color="var(--success)"
          title="Idempotent"
          body="Running the job multiple times for the same date is safe — duplicate drafts are ignored via idempotency keys."
        />
      </div>

      {/* Controls */}
      <div className="card">
        <div className="card-header">
          <span className="card-title">
            <Play size={15} /> Run Job
          </span>
        </div>
        <div className="card-body">
          <div style={{ marginBottom: 16 }}>
            <label
              style={{ display: "block", fontSize: 12, fontWeight: 600, marginBottom: 6, color: "var(--gray-600)" }}
            >
              Target Date (optional — defaults to today)
            </label>
            <input
              type="date"
              className="input"
              value={date}
              onChange={(e) => setDate(e.target.value)}
              style={{ maxWidth: 220 }}
            />
            <div style={{ fontSize: 11, color: "var(--gray-500)", marginTop: 4 }}>
              School events are on Nov 14 (Assembly), Nov 17 (Football), Nov 18 (Amber Fort), Nov 21 (Sports Day).
            </div>
          </div>

          <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
            <button
              className="btn btn-primary btn-lg"
              onClick={() => run(false)}
              disabled={running}
            >
              {running ? <Spinner size={15} /> : <Play size={15} />}
              {running ? "Checking…" : "Run Live Check (Real Weather)"}
            </button>

            <button
              className="btn btn-warning btn-lg"
              onClick={() => run(true)}
              disabled={running}
              style={{ background: "#d97706", color: "white", borderColor: "#b45309" }}
            >
              {running ? <Spinner size={15} /> : <AlertTriangle size={15} />}
              Simulate Heavy Rain (35 mm)
            </button>
          </div>
        </div>
      </div>

      {/* Result */}
      {result && <JobResultCard result={result} />}
    </div>
  );
}

function InfoBox({
  icon,
  color,
  title,
  body,
}: {
  icon: React.ReactNode;
  color: string;
  title: string;
  body: string;
}) {
  return (
    <div
      style={{
        display: "flex",
        gap: 12,
        padding: "12px 14px",
        background: "white",
        border: "1px solid var(--gray-200)",
        borderRadius: 8,
        borderLeft: `4px solid ${color}`,
      }}
    >
      <div style={{ color, flexShrink: 0, marginTop: 1 }}>{icon}</div>
      <div>
        <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 3 }}>{title}</div>
        <div style={{ fontSize: 12, color: "var(--gray-600)", lineHeight: 1.5 }}>{body}</div>
      </div>
    </div>
  );
}

function JobResultCard({ result }: { result: MorningJobResult }) {
  const alertColor =
    result.alerts_count === 0
      ? "var(--success)"
      : result.alerts_count >= 3
      ? "var(--danger)"
      : "var(--warning)";

  return (
    <div style={{ marginTop: 20 }}>
      <div className="card">
        <div className="card-header">
          <span className="card-title">Job Result</span>
          <StatusBadge status={result.status} />
        </div>
        <div className="card-body" style={{ padding: 0 }}>
          <div className="job-result">
            <div className="job-result-row">
              <span className="job-result-label">Date</span>
              <span className="job-result-value">{result.run_date}</span>
            </div>
            <div className="job-result-row">
              <span className="job-result-label">Alerts generated</span>
              <span className="job-result-value" style={{ color: alertColor }}>
                {result.alerts_count}
              </span>
            </div>
            <div className="job-result-row">
              <span className="job-result-label">Drafts created</span>
              <span className="job-result-value">{result.drafts_created}</span>
            </div>
          </div>

          {result.drafts && result.drafts.length > 0 && (
            <div style={{ padding: "0 16px 16px" }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: "var(--gray-600)", marginBottom: 8 }}>
                Generated drafts:
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                {result.drafts.map((d) => (
                  <div
                    key={d.id}
                    style={{
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "space-between",
                      padding: "8px 12px",
                      background: "var(--gray-50)",
                      borderRadius: 6,
                      border: "1px solid var(--gray-200)",
                      fontSize: 13,
                    }}
                  >
                    <span>
                      <strong>#{d.id}</strong> — {d.type}
                      {d.target_id ? ` (${d.target_id})` : ""}
                    </span>
                    <StatusBadge status={d.status} />
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
