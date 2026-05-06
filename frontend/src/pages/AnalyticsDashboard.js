import React, { useEffect, useMemo, useState } from "react";
import api from "../api";
import "../App.css";

const badge = (risk) => {
  const r = String(risk || "").toLowerCase();

  if (r === "critical") return { background: "#fee2e2", color: "#991b1b" };
  if (r === "medium") return { background: "#fef9c3", color: "#854d0e" };
  return { background: "#dcfce7", color: "#166534" };
};

function ScoreBar({ value }) {
  const score = Number(value || 0);

  const color =
    score >= 80 ? "#166534" : score >= 60 ? "#854d0e" : "#991b1b";

  return (
    <div style={{ display: "grid", gridTemplateColumns: "1fr 55px", gap: 10, alignItems: "center" }}>
      <div style={{ height: 9, background: "#e5e7eb", borderRadius: 999, overflow: "hidden" }}>
        <div style={{ width: `${Math.max(0, Math.min(100, score))}%`, height: "100%", background: color }} />
      </div>
      <b>{score}%</b>
    </div>
  );
}

export default function AnalyticsDashboard() {
  const [data, setData] = useState(null);
  const [department, setDepartment] = useState("");
  const [risk, setRisk] = useState("");
  const [err, setErr] = useState("");

  const load = async () => {
    setErr("");
    try {
      const res = await api.get("/analytics/overview");
      setData(res.data || null);
    } catch (e) {
      setErr(e?.response?.data?.detail || "Failed to load analytics.");
    }
  };

  useEffect(() => {
    load();
  }, []);

  const departments = useMemo(() => {
    const set = new Set((data?.courses || []).map((c) => c.department || "Unknown"));
    return Array.from(set);
  }, [data]);

  const filteredCourses = useMemo(() => {
    return (data?.courses || []).filter((c) => {
      if (department && c.department !== department) return false;
      if (risk && c.risk_level !== risk) return false;
      return true;
    });
  }, [data, department, risk]);

  return (
    <div className="fade-in">
      <div className="page-header">
        <h1 className="page-title">Advanced Analytics</h1>
        <p className="page-subtitle">
          Compare course quality, department performance, risk levels, and QA readiness.
        </p>
      </div>

      {err && (
        <div className="card" style={{ padding: 14, marginBottom: 16, background: "#fff1f2", border: "1px solid #fecaca", color: "#991b1b", fontWeight: 800 }}>
          {err}
        </div>
      )}

      <div className="dashboard-grid">
        <div className="stats-card">
          <div className="stats-number">{data?.total_courses ?? "—"}</div>
          <div className="stats-label">Total Courses</div>
        </div>
        <div className="stats-card">
          <div className="stats-number">{data?.scored_courses ?? "—"}</div>
          <div className="stats-label">Scored Courses</div>
        </div>
        <div className="stats-card">
          <div className="stats-number">{data?.average_quality ?? "—"}%</div>
          <div className="stats-label">Average Quality</div>
        </div>
        <div className="stats-card">
          <div className="stats-number">{data?.at_risk_courses ?? "—"}</div>
          <div className="stats-label">At-Risk Courses</div>
        </div>
      </div>

      <div className="card" style={{ marginBottom: 24 }}>
        <div className="card-header">
          <h2 className="card-title">Filters</h2>
        </div>

        <div className="card-content" style={{ display: "grid", gridTemplateColumns: "1fr 1fr auto", gap: 12 }}>
          <select className="form-input" value={department} onChange={(e) => setDepartment(e.target.value)}>
            <option value="">All Departments</option>
            {departments.map((d) => (
              <option key={d} value={d}>{d}</option>
            ))}
          </select>

          <select className="form-input" value={risk} onChange={(e) => setRisk(e.target.value)}>
            <option value="">All Risk Levels</option>
            <option value="critical">Critical</option>
            <option value="medium">Medium</option>
            <option value="low">Low</option>
          </select>

          <button className="btn btn-secondary" onClick={load}>Refresh</button>
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 24, marginBottom: 24 }}>
        <div className="card">
          <div className="card-header">
            <h2 className="card-title">Department Performance</h2>
          </div>

          <div className="card-content">
            {(data?.departments || []).length === 0 ? (
              <div style={{ color: "#64748b" }}>No department data available.</div>
            ) : (
              (data?.departments || []).map((d) => (
                <div key={d.department} style={{ padding: "12px 0", borderBottom: "1px solid #e2e8f0" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 8 }}>
                    <b>{d.department}</b>
                    <span style={{ color: "#64748b", fontSize: 13 }}>{d.courses} courses · {d.at_risk} at risk</span>
                  </div>
                  <ScoreBar value={d.average_quality} />
                </div>
              ))
            )}
          </div>
        </div>

        <div className="card">
          <div className="card-header">
            <h2 className="card-title">Highest Risk Courses</h2>
          </div>

          <div className="card-content">
            {(data?.courses || []).slice(0, 6).map((c) => (
              <div key={c.course_id} style={{ padding: 12, border: "1px solid #e2e8f0", borderRadius: 12, marginBottom: 10, background: "#f8fafc" }}>
                <div style={{ display: "flex", justifyContent: "space-between", gap: 10 }}>
                  <div>
                    <b>{c.course_code}</b>
                    <div style={{ fontSize: 13, color: "#64748b" }}>{c.course_name}</div>
                  </div>
                  <span style={{ ...badge(c.risk_level), padding: "5px 10px", borderRadius: 999, fontWeight: 900, fontSize: 12 }}>
                    {c.risk_level}
                  </span>
                </div>
                <div style={{ marginTop: 10 }}>
                  <ScoreBar value={c.overall_score} />
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="card">
        <div className="card-header">
          <h2 className="card-title">Course Comparison</h2>
        </div>

        <div className="card-content" style={{ overflowX: "auto" }}>
          {filteredCourses.length === 0 ? (
            <div style={{ color: "#64748b" }}>No matching courses found.</div>
          ) : (
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 14 }}>
              <thead>
                <tr style={{ background: "#f8fafc" }}>
                  <th style={th}>Course</th>
                  <th style={th}>Department</th>
                  <th style={th}>Overall</th>
                  <th style={th}>Completeness</th>
                  <th style={th}>Alignment</th>
                  <th style={th}>Feedback</th>
                  <th style={th}>Grading</th>
                  <th style={th}>Uploads</th>
                  <th style={th}>Risk</th>
                </tr>
              </thead>

              <tbody>
                {filteredCourses.map((c) => (
                  <tr key={c.course_id}>
                    <td style={td}>
                      <b>{c.course_code}</b>
                      <div style={{ color: "#64748b", fontSize: 12 }}>{c.course_name}</div>
                    </td>
                    <td style={td}>{c.department}</td>
                    <td style={td}>{c.overall_score}%</td>
                    <td style={td}>{c.completeness_score}%</td>
                    <td style={td}>{c.alignment_score}%</td>
                    <td style={td}>{c.feedback_score}%</td>
                    <td style={td}>{c.grading_score}%</td>
                    <td style={td}>{c.uploads_count}</td>
                    <td style={td}>
                      <span style={{ ...badge(c.risk_level), padding: "5px 10px", borderRadius: 999, fontWeight: 900, fontSize: 12 }}>
                        {c.risk_level}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
}

const th = {
  padding: 12,
  textAlign: "left",
  borderBottom: "1px solid #e2e8f0",
  color: "#475569",
  fontWeight: 900,
};

const td = {
  padding: 12,
  borderBottom: "1px solid #e2e8f0",
  verticalAlign: "top",
};