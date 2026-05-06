// frontend/src/pages/GradingFairness.js
import React, { useEffect, useMemo, useState } from "react";
import api from "../api";
import "../App.css";

function badgeColor(level) {
  if (level === "high") return "#dc2626";
  if (level === "medium") return "#f59e0b";
  if (level === "low") return "#16a34a";
  return "#64748b";
}

function CardRow({ label, value }) {
  return (
    <div
      style={{
        display: "flex",
        justifyContent: "space-between",
        gap: 12,
        padding: "8px 0",
        borderBottom: "1px solid #f1f5f9",
      }}
    >
      <div className="muted">{label}</div>
      <div style={{ fontWeight: 700 }}>{value}</div>
    </div>
  );
}

// Tries both paths if you still have /api mounted
async function tryGet(paths, config) {
  let lastErr = null;
  for (const p of paths) {
    try {
      return await api.get(p, config);
    } catch (e) {
      lastErr = e;
      const status = e?.response?.status;
      if (status && status !== 404) throw e;
    }
  }
  throw lastErr;
}
async function tryPost(paths, data, config) {
  let lastErr = null;
  for (const p of paths) {
    try {
      return await api.post(p, data, config);
    } catch (e) {
      lastErr = e;
      const status = e?.response?.status;
      if (status && status !== 404) throw e;
    }
  }
  throw lastErr;
}

function toFixedMaybe(x, digits = 2) {
  if (typeof x !== "number") return "-";
  return x.toFixed(digits);
}

// ✅ Your backend returns: [{metric, value, ...}, ...]
function parseAuditMetricList(rows) {
  const arr = Array.isArray(rows) ? rows : [];
  const byMetric = {};
  for (const r of arr) {
    if (r?.metric) byMetric[r.metric] = r.value;
  }

  const distribution = byMetric.distribution || {};
  const outliers = byMetric.outliers || {};
  const perQuestion = byMetric.per_question || {};
  const cloAchievement = byMetric.clo_achievement || {};

  // Simple explainable risk scoring (frontend-only, no backend change required)
  const flags = [];
  const std = distribution.std;
  const outCount = outliers.count ?? 0;

  // These thresholds are just reasonable defaults for demo/explainability
  if (typeof std === "number" && std >= 3) flags.push("Very high score spread (high std deviation).");
  if (typeof std === "number" && std >= 1.5 && std < 3) flags.push("Moderate score spread (std deviation is elevated).");
  if (outCount > 0) flags.push(`There are ${outCount} outlier(s) outside the normal range.`);

  // Per-question imbalance check
  // If one question avg is extremely low vs others, it might indicate confusing question / wrong expected answers
  const qAvgs = Object.entries(perQuestion || {})
    .map(([qid, stats]) => ({ qid, avg: stats?.avg }))
    .filter((x) => typeof x.avg === "number");

  if (qAvgs.length >= 2) {
    const avgs = qAvgs.map((x) => x.avg);
    const maxAvg = Math.max(...avgs);
    const minAvg = Math.min(...avgs);
    if (maxAvg - minAvg >= 3) {
      flags.push("Large per-question difficulty gap (some questions are much harder/easier).");
    }
  }

  let risk_level = "low";
  if (flags.length >= 2) risk_level = "medium";
  if (flags.length >= 3 || (outCount > 0 && typeof std === "number" && std >= 1.5)) risk_level = "high";
  if (!arr.length) risk_level = "unknown";

  return {
    raw: arr,
    distribution,
    outliers,
    perQuestion,
    cloAchievement,
    flags,
    risk_level,
  };
}

export default function GradingFairness() {
  const [courses, setCourses] = useState([]);
  const [selectedCourse, setSelectedCourse] = useState("");

  const [assessments, setAssessments] = useState([]);
  const [selectedAssessment, setSelectedAssessment] = useState("");

  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState("");
  const [audit, setAudit] = useState(null);

  useEffect(() => {
    api
      .get("/courses")
      .then((res) => {
        const list = res.data || [];
        setCourses(list);
        if (list.length) setSelectedCourse(list[0].id);
      })
      .catch(() => setCourses([]));
  }, []);

  useEffect(() => {
    setErr("");
    setAudit(null);
    setAssessments([]);
    setSelectedAssessment("");

    if (!selectedCourse) return;

    setLoading(true);
    (async () => {
      try {
        const res = await tryGet(
          [`/courses/${selectedCourse}/assessments`, `/api/courses/${selectedCourse}/assessments`],
          {}
        );
        const list = Array.isArray(res.data) ? res.data : [];
        setAssessments(list);
        if (list.length) setSelectedAssessment(list[0].id);
      } catch (e) {
        setErr(e?.response?.data?.detail || "Failed to load assessments for this course.");
      } finally {
        setLoading(false);
      }
    })();
  }, [selectedCourse]);

  const whyFlagged = useMemo(() => {
    if (!audit) return "";
    if (!audit.flags.length) {
      return "No fairness flags were raised based on distribution/outlier/per-question checks.";
    }
    const bullets = audit.flags.map((f) => `• ${f}`).join("\n");
    return `This grading run may need review because:\n${bullets}\n\nRecommended action:\n• Inspect outlier submissions\n• Check rubric / marking consistency\n• Verify expected answers & question clarity`;
  }, [audit]);

  const runAudit = async () => {
    setErr("");
    setAudit(null);

    if (!selectedAssessment) {
      setErr("Please select an assessment first.");
      return;
    }

    setLoading(true);
    try {
      await tryPost(
        [`/assessments/${selectedAssessment}/run-grading-audit`, `/api/assessments/${selectedAssessment}/run-grading-audit`],
        {}
      );

      const res = await tryGet(
        [`/assessments/${selectedAssessment}/grading-audit`, `/api/assessments/${selectedAssessment}/grading-audit`],
        {}
      );

      setAudit(parseAuditMetricList(res.data));
    } catch (e) {
      setErr(e?.response?.data?.detail || "Failed to run/load grading audit.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fade-in">
      <div className="page-header">
        <h1 className="page-title">Explainable Grading Fairness</h1>
        <p className="page-subtitle">Uses grading-audit metrics (distribution, outliers, per-question)</p>
      </div>

      <div className="card">
        <div className="card-content">
          <select className="form-input" value={selectedCourse} onChange={(e) => setSelectedCourse(e.target.value)}>
            <option value="">Choose a course...</option>
            {courses.map((c) => (
              <option key={c.id} value={c.id}>
                {c.course_code} — {c.course_name}
              </option>
            ))}
          </select>

          <div style={{ marginTop: 12 }}>
            <select
              className="form-input"
              value={selectedAssessment}
              onChange={(e) => setSelectedAssessment(e.target.value)}
              disabled={!assessments.length}
            >
              {!assessments.length ? <option value="">No assessments found</option> : null}
              {assessments.map((a) => (
                <option key={a.id} value={a.id}>
                  {a.title || a.name || "Assessment"}
                </option>
              ))}
            </select>
          </div>

          <button className="btn-primary" style={{ marginTop: 12 }} onClick={runAudit} disabled={loading || !selectedAssessment}>
            {loading ? "Working..." : "Run Audit"}
          </button>

          {err ? <p style={{ color: "red", marginTop: 12 }}>{err}</p> : null}
        </div>
      </div>

      {audit ? (
        <>
          <div className="card" style={{ marginTop: 16 }}>
            <div className="card-header">
              <h2 className="card-title">Summary</h2>
            </div>
            <div className="card-content">
              <CardRow label="Mean marks" value={toFixedMaybe(audit.distribution.mean, 2)} />
              <CardRow label="Median marks" value={toFixedMaybe(audit.distribution.median, 2)} />
              <CardRow label="Std dev" value={toFixedMaybe(audit.distribution.std, 2)} />
              <CardRow label="Max marks" value={audit.distribution.max_marks ?? "-"} />
              <CardRow label="Outliers count" value={audit.outliers.count ?? 0} />
              <CardRow label="Outlier lower bound" value={toFixedMaybe(audit.outliers.lower, 2)} />
              <CardRow label="Outlier upper bound" value={toFixedMaybe(audit.outliers.upper, 2)} />

              <div style={{ marginTop: 12 }}>
                <span
                  style={{
                    display: "inline-block",
                    padding: "6px 10px",
                    borderRadius: 999,
                    background: "#f1f5f9",
                    color: badgeColor(audit.risk_level),
                    border: `1px solid ${badgeColor(audit.risk_level)}30`,
                    fontWeight: 800,
                  }}
                >
                  Risk: {(audit.risk_level || "unknown").toUpperCase()}
                </span>
              </div>
            </div>
          </div>

          <div className="card" style={{ marginTop: 16 }}>
            <div className="card-header">
              <h2 className="card-title">Why flagged?</h2>
            </div>
            <div className="card-content">
              <pre style={{ whiteSpace: "pre-wrap", margin: 0, fontFamily: "inherit" }}>{whyFlagged}</pre>
            </div>
          </div>

          {audit.outliers?.values?.length ? (
            <div className="card" style={{ marginTop: 16 }}>
              <div className="card-header">
                <h2 className="card-title">Outliers</h2>
              </div>
              <div className="card-content">
                {audit.outliers.values.map((v, idx) => (
                  <div key={idx} style={{ padding: "10px 0", borderBottom: "1px solid #f1f5f9" }}>
                    <strong>Student:</strong> {v.student_id || v.student_name || "—"} &nbsp; | &nbsp;
                    <strong>Marks:</strong> {v.marks ?? v.score ?? "—"}
                  </div>
                ))}
              </div>
            </div>
          ) : null}

          {audit.perQuestion && Object.keys(audit.perQuestion).length ? (
            <div className="card" style={{ marginTop: 16 }}>
              <div className="card-header">
                <h2 className="card-title">Per Question Stats</h2>
              </div>
              <div className="card-content">
                {Object.entries(audit.perQuestion).map(([qid, s]) => (
                  <div key={qid} style={{ padding: "10px 0", borderBottom: "1px solid #f1f5f9" }}>
                    <div style={{ fontWeight: 800 }}>Q{qid}</div>
                    <div className="muted">
                      avg: {toFixedMaybe(s?.avg, 2)} | min: {toFixedMaybe(s?.min, 2)} | max: {toFixedMaybe(s?.max, 2)} | count:{" "}
                      {s?.count ?? "-"}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ) : null}

          <div className="card" style={{ marginTop: 16 }}>
            <div className="card-header">
              <h2 className="card-title">Audit JSON</h2>
            </div>
            <div className="card-content">
              <pre
                style={{
                  whiteSpace: "pre-wrap",
                  margin: 0,
                  fontSize: 12,
                  background: "#0b1220",
                  color: "white",
                  padding: 12,
                  borderRadius: 12,
                  overflow: "auto",
                  maxHeight: 320,
                }}
              >
                {JSON.stringify(audit.raw, null, 2)}
              </pre>
            </div>
          </div>
        </>
      ) : null}
    </div>
  );
}
