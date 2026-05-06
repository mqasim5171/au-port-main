// frontend/src/pages/AuditLogs.js
import React, { useEffect, useState } from "react";
import api from "../api";
import "../App.css";

const API_PATH = "/audit"; // change to your real endpoint

export default function AuditLogs({ user }) {
  const [courses, setCourses] = useState([]);
  const [courseId, setCourseId] = useState("");

  const [action, setAction] = useState("");
  const [actor, setActor] = useState("");
  const [limit, setLimit] = useState(50);

  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState("");
  const [logs, setLogs] = useState([]);

  useEffect(() => {
    api.get("/courses")
      .then((res) => setCourses(res.data || []))
      .catch(() => setCourses([]));
  }, []);

  const load = async () => {
    setErr("");
    setLogs([]);
    setLoading(true);
    try {
      const { data } = await api.get(API_PATH, {
        params: {
          course_id: courseId || undefined,
          action: action || undefined,
          actor_id: actor || undefined,
          limit,
        },
      });
      setLogs(Array.isArray(data) ? data : (data?.items || []));
    } catch (e) {
      setErr(e?.response?.data?.detail || "Failed to load audit logs.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fade-in">
      <div className="page-header">
        <h1 className="page-title">Audit Logs (QEC)</h1>
        <p className="page-subtitle">Trace every major action: uploads, checks, alignment, grading, flags</p>
      </div>

      <div className="card">
        <div className="card-content" style={{ display: "grid", gap: 10 }}>
          <select className="form-input" value={courseId} onChange={(e) => setCourseId(e.target.value)}>
            <option value="">All courses</option>
            {courses.map((c) => (
              <option key={c.id} value={c.id}>
                {c.course_code} — {c.course_name}
              </option>
            ))}
          </select>

          <input className="form-input" value={action} onChange={(e) => setAction(e.target.value)} placeholder="Filter by action (e.g. upload, align, grade)" />
          <input className="form-input" value={actor} onChange={(e) => setActor(e.target.value)} placeholder="Filter by actor_id (optional)" />

          <div style={{ display: "flex", gap: 10 }}>
            <input className="form-input" type="number" value={limit} onChange={(e) => setLimit(Number(e.target.value))} />
            <button className="btn-primary" onClick={load} disabled={loading}>
              {loading ? "Loading..." : "Load Logs"}
            </button>
          </div>

          {err && <p style={{ color: "red" }}>{err}</p>}
        </div>
      </div>

      <div className="card" style={{ marginTop: 16 }}>
        <div className="card-header">
          <h2 className="card-title">Events</h2>
        </div>
        <div className="card-content">
          {!logs.length ? (
            <p className="muted">No logs loaded.</p>
          ) : (
            logs.map((l, idx) => (
              <div key={idx} style={{ padding: "12px 0", borderBottom: "1px solid #f1f5f9" }}>
                <div style={{ display: "flex", justifyContent: "space-between", gap: 12 }}>
                  <div style={{ fontWeight: 900 }}>{l.action || "event"}</div>
                  <div className="muted">{l.ts || l.created_at || "-"}</div>
                </div>
                <div className="muted" style={{ marginTop: 4 }}>
                  actor: <strong>{l.actor_id ?? "-"}</strong> • course: <strong>{l.course_id ?? "-"}</strong>
                </div>
                {l.summary ? <div style={{ marginTop: 6 }}>{l.summary}</div> : null}
                {l.meta ? (
                  <details style={{ marginTop: 8 }}>
                    <summary style={{ cursor: "pointer" }}>details</summary>
                    <pre style={{ whiteSpace: "pre-wrap", margin: 0 }}>{JSON.stringify(l.meta, null, 2)}</pre>
                  </details>
                ) : null}
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
