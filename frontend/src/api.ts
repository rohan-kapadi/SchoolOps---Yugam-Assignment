// API client for SchoolOps Agent (port 8000) and School API (port 8001)

const AGENT_API = "http://localhost:8000";
const SCHOOL_API = "http://localhost:8001";

// ─── Types ───────────────────────────────────────────────────────────────────

export interface ToolTraceItem {
  tool: string;
  input?: unknown;
  args?: unknown;
  output?: unknown;
  result?: unknown;
  status?: string;
}

export interface AskResponse {
  answer: string;
  tool_trace: ToolTraceItem[];
  sources: string[];
}

export interface Draft {
  id: number;
  date: string;
  type: string;
  status: "PENDING" | "APPROVED" | "REJECTED" | "ALL_CLEAR";
  summary: string;
  principal_note: string | null;
  idempotency_key: string;
  target_id: string | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface OutboxMessage {
  id: number;
  draft_id: number;
  recipient_id: string;
  message_en: string;
  message_hi: string;
  status: "QUEUED" | "SENT" | "FAILED";
  attempts: number;
  last_attempt_at: string | null;
  created_at: string | null;
}

export interface MorningJobResult {
  run_date: string;
  alerts_count: number;
  drafts_created: number;
  status: string;
  drafts?: Draft[];
}

export interface Student {
  id: string;
  name: string;
  class: string;
  busRouteId: string | null;
  busStop: string | null;
  homeArea: string;
  homePin: string;
  parent: { name: string; phone: string; language: string };
}

export interface BusRoute {
  id: string;
  name: string;
  driverName: string;
  pickupStartTime: string;
  stops: Array<{ order: number; area: string; pin: string; lat: number; lon: number }>;
}

export interface Event {
  id: string;
  title: string;
  date: string;
  start: string;
  end: string;
  location: string;
  outdoor: boolean;
  classes: string | string[];
  description: string;
}

export interface AttendanceDay {
  date: string;
  absent: string[];
  late: string[];
}

// ─── Agent API ───────────────────────────────────────────────────────────────

export async function askAgent(question: string): Promise<AskResponse> {
  const res = await fetch(`${AGENT_API}/ask`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? `HTTP ${res.status}`);
  }
  return res.json();
}

export async function triggerMorningJob(
  date?: string,
  simulateAdverseWeather: boolean = false
): Promise<MorningJobResult> {
  const res = await fetch(`${AGENT_API}/jobs/morning/run`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      date: date ?? null,
      simulate_adverse_weather: simulateAdverseWeather,
    }),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export async function getDrafts(status?: string, date?: string): Promise<Draft[]> {
  const params = new URLSearchParams();
  if (status) params.set("status", status);
  if (date) params.set("date", date);
  const res = await fetch(`${AGENT_API}/drafts?${params}`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export async function getDraft(id: number): Promise<Draft> {
  const res = await fetch(`${AGENT_API}/drafts/${id}`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export async function updateDraft(
  id: number,
  data: { summary?: string; principal_note?: string }
): Promise<Draft> {
  const res = await fetch(`${AGENT_API}/drafts/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? `HTTP ${res.status}`);
  }
  return res.json();
}

export async function approveDraft(id: number): Promise<unknown> {
  const res = await fetch(`${AGENT_API}/drafts/${id}/approve`, { method: "POST" });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? `HTTP ${res.status}`);
  }
  return res.json();
}

export async function rejectDraft(id: number): Promise<unknown> {
  const res = await fetch(`${AGENT_API}/drafts/${id}/reject`, { method: "POST" });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? `HTTP ${res.status}`);
  }
  return res.json();
}

export async function getMessages(draftId?: number, status?: string): Promise<OutboxMessage[]> {
  const params = new URLSearchParams();
  if (draftId !== undefined) params.set("draft_id", String(draftId));
  if (status) params.set("status", status);
  const res = await fetch(`${AGENT_API}/messages?${params}`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export async function checkAgentHealth(): Promise<boolean> {
  try {
    const res = await fetch(`${AGENT_API}/health`, { signal: AbortSignal.timeout(3000) });
    return res.ok;
  } catch {
    return false;
  }
}

export async function checkSchoolHealth(): Promise<boolean> {
  try {
    const res = await fetch(`${SCHOOL_API}/school`, { signal: AbortSignal.timeout(3000) });
    return res.ok;
  } catch {
    return false;
  }
}

// ─── School API ──────────────────────────────────────────────────────────────

export async function getStudents(): Promise<{ data: Student[] }> {
  const res = await fetch(`${SCHOOL_API}/school/students`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  const data = await res.json();
  return { data };
}

export async function getRoutes(): Promise<{ data: BusRoute[] }> {
  const res = await fetch(`${SCHOOL_API}/school/routes`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  const data = await res.json();
  return { data };
}

export async function getEvents(): Promise<{ data: Event[] }> {
  const res = await fetch(`${SCHOOL_API}/school/events`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  const data = await res.json();
  return { data };
}

export async function getAttendance(): Promise<{ data: AttendanceDay[] }> {
  const res = await fetch(`${SCHOOL_API}/school/attendance`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  const data = await res.json();
  return { data };
}

export async function getPolicy(): Promise<{ data: string }> {
  const res = await fetch(`${SCHOOL_API}/school/policy`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  const raw = await res.json();
  // policy endpoint returns { "policy": "..." }
  return { data: raw.policy ?? raw.data ?? raw };
}

