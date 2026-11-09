// SchoolDataPage — browse students, routes, events, attendance, policy

import { useState, useEffect } from "react";
import { Users, Bus, Calendar, BookOpen, ClipboardList, Search, ChevronDown, ChevronUp } from "lucide-react";
import { getStudents, getRoutes, getEvents, getAttendance, getPolicy, Student, BusRoute, Event, AttendanceDay } from "../api";
import { Spinner, EmptyState } from "../components";

type Tab = "students" | "routes" | "events" | "attendance" | "policy";

export default function SchoolDataPage() {
  const [tab, setTab] = useState<Tab>("students");

  const tabs: { key: Tab; label: string; icon: React.ReactNode }[] = [
    { key: "students", label: "Students", icon: <Users size={14} /> },
    { key: "routes", label: "Bus Routes", icon: <Bus size={14} /> },
    { key: "events", label: "Events", icon: <Calendar size={14} /> },
    { key: "attendance", label: "Attendance", icon: <ClipboardList size={14} /> },
    { key: "policy", label: "Policy", icon: <BookOpen size={14} /> },
  ];

  return (
    <div className="page-body">
      <h2 className="section-title">School Data Explorer</h2>

      {/* Tab bar */}
      <div
        style={{
          display: "flex",
          gap: 4,
          borderBottom: "1px solid var(--gray-200)",
          marginBottom: 20,
        }}
      >
        {tabs.map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            style={{
              display: "flex",
              alignItems: "center",
              gap: 6,
              padding: "9px 14px",
              background: "none",
              border: "none",
              borderBottom: tab === t.key ? "2px solid var(--primary)" : "2px solid transparent",
              color: tab === t.key ? "var(--primary)" : "var(--gray-500)",
              fontWeight: tab === t.key ? 600 : 400,
              cursor: "pointer",
              fontSize: 13,
              fontFamily: "var(--font)",
              marginBottom: -1,
            }}
          >
            {t.icon}
            {t.label}
          </button>
        ))}
      </div>

      {tab === "students" && <StudentsTab />}
      {tab === "routes" && <RoutesTab />}
      {tab === "events" && <EventsTab />}
      {tab === "attendance" && <AttendanceTab />}
      {tab === "policy" && <PolicyTab />}
    </div>
  );
}

// ─── Students ─────────────────────────────────────────────────────────────────

function StudentsTab() {
  const [students, setStudents] = useState<Student[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [classFilter, setClassFilter] = useState("");

  useEffect(() => {
    getStudents()
      .then((r) => setStudents(r.data))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const classes = [...new Set(students.map((s) => s.class))].sort();

  const filtered = students.filter((s) => {
    const q = search.toLowerCase();
    const matchSearch =
      !q ||
      s.name.toLowerCase().includes(q) ||
      s.id.toLowerCase().includes(q) ||
      s.homeArea.toLowerCase().includes(q);
    const matchClass = !classFilter || s.class === classFilter;
    return matchSearch && matchClass;
  });

  if (loading) return <div style={{ textAlign: "center", padding: 48 }}><Spinner size={32} /></div>;

  return (
    <div>
      <div className="filter-row mb-4">
        <div style={{ position: "relative", flex: 1, maxWidth: 300 }}>
          <Search
            size={14}
            style={{ position: "absolute", left: 10, top: "50%", transform: "translateY(-50%)", color: "var(--gray-400)" }}
          />
          <input
            className="input"
            style={{ paddingLeft: 32 }}
            placeholder="Search by name, ID, area…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        <select
          className="filter-select"
          value={classFilter}
          onChange={(e) => setClassFilter(e.target.value)}
        >
          <option value="">All Classes</option>
          {classes.map((c) => (
            <option key={c} value={c}>{c}</option>
          ))}
        </select>
        <span className="text-sm text-muted">{filtered.length} of {students.length}</span>
      </div>

      <div className="card" style={{ overflow: "hidden" }}>
        <div style={{ overflowX: "auto" }}>
          <table className="table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Name</th>
                <th>Class</th>
                <th>Area</th>
                <th>PIN</th>
                <th>Bus Route</th>
                <th>Parent</th>
                <th>Language</th>
              </tr>
            </thead>
            <tbody>
              {filtered.slice(0, 100).map((s) => (
                <tr key={s.id}>
                  <td className="font-mono text-xs">{s.id}</td>
                  <td style={{ fontWeight: 500 }}>{s.name}</td>
                  <td><span className="badge badge-all_clear">{s.class}</span></td>
                  <td className="text-xs">{s.homeArea}</td>
                  <td className="font-mono text-xs">{s.homePin}</td>
                  <td className="text-xs">{s.busRouteId ?? <span className="text-muted">—</span>}</td>
                  <td className="text-xs">{s.parent.name}</td>
                  <td className="text-xs">{s.parent.language}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {filtered.length > 100 && (
          <div style={{ padding: "10px 16px", fontSize: 12, color: "var(--gray-500)", borderTop: "1px solid var(--gray-100)" }}>
            Showing 100 of {filtered.length}. Refine filter to see more.
          </div>
        )}
      </div>
    </div>
  );
}

// ─── Routes ───────────────────────────────────────────────────────────────────

function RoutesTab() {
  const [routes, setRoutes] = useState<BusRoute[]>([]);
  const [loading, setLoading] = useState(true);
  const [expanded, setExpanded] = useState<string | null>(null);

  useEffect(() => {
    getRoutes()
      .then((r) => setRoutes(r.data))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div style={{ textAlign: "center", padding: 48 }}><Spinner size={32} /></div>;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
      {routes.map((r) => (
        <div key={r.id} className="card" style={{ overflow: "hidden" }}>
          <div
            onClick={() => setExpanded(expanded === r.id ? null : r.id)}
            style={{
              padding: "14px 16px",
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              cursor: "pointer",
            }}
          >
            <div>
              <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                <span
                  style={{
                    width: 32,
                    height: 32,
                    background: "var(--primary-light)",
                    color: "var(--primary)",
                    borderRadius: 8,
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    fontWeight: 700,
                    fontSize: 13,
                  }}
                >
                  {r.id}
                </span>
                <div>
                  <div style={{ fontWeight: 600, fontSize: 14 }}>{r.name}</div>
                  <div style={{ fontSize: 12, color: "var(--gray-500)" }}>
                    Driver: {r.driverName} · Pickup: {r.pickupStartTime}
                  </div>
                </div>
              </div>
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <span className="text-xs text-muted">{r.stops.length} stops</span>
              {expanded === r.id ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
            </div>
          </div>
          {expanded === r.id && (
            <div style={{ borderTop: "1px solid var(--gray-100)", padding: "0 16px 14px" }}>
              <div style={{ display: "flex", flexDirection: "column", gap: 4, marginTop: 12 }}>
                {r.stops.map((s) => (
                  <div
                    key={s.order}
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: 12,
                      padding: "6px 10px",
                      background: "var(--gray-50)",
                      borderRadius: 6,
                      fontSize: 12,
                    }}
                  >
                    <span
                      style={{
                        width: 20,
                        height: 20,
                        background: "var(--primary)",
                        color: "white",
                        borderRadius: "50%",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        fontSize: 10,
                        fontWeight: 700,
                        flexShrink: 0,
                      }}
                    >
                      {s.order}
                    </span>
                    <span style={{ flex: 1, fontWeight: 500 }}>{s.area}</span>
                    <span className="font-mono text-xs text-muted">{s.pin}</span>
                    <span className="text-xs text-muted">
                      {s.lat.toFixed(4)}, {s.lon.toFixed(4)}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

// ─── Events ───────────────────────────────────────────────────────────────────

function EventsTab() {
  const [events, setEvents] = useState<Event[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getEvents()
      .then((r) => setEvents(r.data))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div style={{ textAlign: "center", padding: 48 }}><Spinner size={32} /></div>;
  if (!events.length) return <EmptyState icon={<Calendar />} title="No events" />;

  return (
    <div className="grid-auto">
      {events.map((e) => (
        <div key={e.id} className="card" style={{ overflow: "hidden" }}>
          <div style={{ padding: "12px 14px", background: e.outdoor ? "var(--warning-light)" : "var(--primary-light)" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
              <div style={{ fontSize: 11, fontWeight: 700, letterSpacing: "0.06em", color: e.outdoor ? "var(--warning)" : "var(--primary)" }}>
                {e.outdoor ? "OUTDOOR" : "INDOOR"}
              </div>
              <span className="text-xs text-muted font-mono">{e.id}</span>
            </div>
            <div style={{ fontSize: 15, fontWeight: 600, marginTop: 4 }}>{e.title}</div>
          </div>
          <div style={{ padding: "12px 14px" }}>
            <div style={{ fontSize: 12, color: "var(--gray-600)", marginBottom: 6 }}>
              📅 {e.date} · {e.start}–{e.end}
            </div>
            <div style={{ fontSize: 12, color: "var(--gray-600)", marginBottom: 6 }}>
              📍 {e.location}
            </div>
            <div style={{ fontSize: 12, color: "var(--gray-600)", marginBottom: 8 }}>
              🏫 Classes: {Array.isArray(e.classes) ? e.classes.join(", ") : e.classes}
            </div>
            <p style={{ fontSize: 12, color: "var(--gray-700)", lineHeight: 1.5 }}>{e.description}</p>
          </div>
        </div>
      ))}
    </div>
  );
}

// ─── Attendance ───────────────────────────────────────────────────────────────

function AttendanceTab() {
  const [records, setRecords] = useState<AttendanceDay[]>([]);
  const [loading, setLoading] = useState(true);
  const [expanded, setExpanded] = useState<string | null>(null);

  useEffect(() => {
    getAttendance()
      .then((r) => setRecords(r.data))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div style={{ textAlign: "center", padding: 48 }}><Spinner size={32} /></div>;

  const sorted = [...records].sort((a, b) => b.date.localeCompare(a.date));

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
      {sorted.map((r) => (
        <div key={r.date} className="card" style={{ overflow: "hidden" }}>
          <div
            onClick={() => setExpanded(expanded === r.date ? null : r.date)}
            style={{
              padding: "12px 16px",
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              cursor: "pointer",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
              <span style={{ fontWeight: 600, fontSize: 14 }}>{r.date}</span>
              {r.absent.length > 0 && (
                <span className="badge badge-rejected">
                  {r.absent.length} absent
                </span>
              )}
              {r.late.length > 0 && (
                <span className="badge badge-pending">
                  {r.late.length} late
                </span>
              )}
              {r.absent.length === 0 && r.late.length === 0 && (
                <span className="badge badge-approved">Full attendance</span>
              )}
            </div>
            {expanded === r.date ? <ChevronUp size={15} /> : <ChevronDown size={15} />}
          </div>
          {expanded === r.date && (
            <div
              style={{
                borderTop: "1px solid var(--gray-100)",
                padding: "12px 16px",
                display: "grid",
                gridTemplateColumns: "1fr 1fr",
                gap: 12,
              }}
            >
              <div>
                <div style={{ fontSize: 11, fontWeight: 600, color: "var(--danger)", marginBottom: 6 }}>
                  ABSENT ({r.absent.length})
                </div>
                {r.absent.length === 0 ? (
                  <span className="text-xs text-muted">None</span>
                ) : (
                  <div style={{ display: "flex", flexWrap: "wrap", gap: 4 }}>
                    {r.absent.map((id) => (
                      <span key={id} className="font-mono text-xs" style={{ background: "var(--danger-light)", color: "var(--danger)", padding: "2px 6px", borderRadius: 4 }}>
                        {id}
                      </span>
                    ))}
                  </div>
                )}
              </div>
              <div>
                <div style={{ fontSize: 11, fontWeight: 600, color: "var(--warning)", marginBottom: 6 }}>
                  LATE ({r.late.length})
                </div>
                {r.late.length === 0 ? (
                  <span className="text-xs text-muted">None</span>
                ) : (
                  <div style={{ display: "flex", flexWrap: "wrap", gap: 4 }}>
                    {r.late.map((id) => (
                      <span key={id} className="font-mono text-xs" style={{ background: "var(--warning-light)", color: "var(--warning)", padding: "2px 6px", borderRadius: 4 }}>
                        {id}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

// ─── Policy ───────────────────────────────────────────────────────────────────

function PolicyTab() {
  const [policy, setPolicy] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getPolicy()
      .then((r) => setPolicy(r.data))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div style={{ textAlign: "center", padding: 48 }}><Spinner size={32} /></div>;

  return (
    <div className="card">
      <div className="card-header">
        <span className="card-title"><BookOpen size={15} /> School Policy</span>
      </div>
      <div className="card-body">
        <pre
          style={{
            fontFamily: "var(--font)",
            fontSize: 13,
            lineHeight: 1.8,
            whiteSpace: "pre-wrap",
            color: "var(--gray-800)",
          }}
        >
          {policy}
        </pre>
      </div>
    </div>
  );
}
