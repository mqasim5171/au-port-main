// frontend/src/pages/CLOHeatmap.js
import React, { useEffect, useMemo, useState } from "react";
import api from "../api";
import "../App.css";

function clamp01(x) {
  if (typeof x !== "number") return 0;
  return Math.max(0, Math.min(1, x));
}

function cellBg(sim) {
  // simple red->green gradient
  const s = clamp01(sim);
  const r = Math.round(220 - 160 * s);
  const g = Math.round(60 + 140 * s);
  const b = Math.round(70);
  return `rgb(${r},${g},${b})`;
}

export default function CLOHeatmap() {
  const [courses, setCourses] = useState([]);
  const [selectedCourse, setSelectedCourse] = useState("");

  const [clos, setClos] = useState([]);
  const [assessments, setAssessments] = useState([]);

  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState("");

  // backend result
  const [result, setResult] = useState(null);

  useEffect(() => {
    api.get("/courses")
      .then((res) => setCourses(res.data || []))
      .catch(() => setCourses([]));
  }, []);

  // auto-load clos + assessments preview
  useEffect(() => {
    setErr("");
    setResult(null);
    setClos([]);
    setAssessments([]);

    if (!selectedCourse) return;

    setLoading(true);
    api.get(`/align/${selectedCourse}/auto`)
      .then((res) => {
        const data = res.data || {};
        setClos(Array.isArray(data.clos) ? data.clos : []);
        setAssessments(Array.isArray(data.assessments) ? data.assessments : []);
      })
      .catch((e) => {
        setErr(e?.response?.data?.detail || "Failed to fetch CLOs/assessments.");
      })
      .finally(() => setLoading(false));
  }, [selectedCourse]);

  const run = async () => {
    setErr("");
    setResult(null);

    if (!selectedCourse) {
      setErr("Select a course.");
      return;
    }
    if (!clos.length || !assessments.length) {
      setErr("Need CLOs and assessments. Upload course guide/materials first.");
      return;
    }

    setLoading(true);
    try {
      const payload = {
        clos,
        assessments: assessments.map((a) => ({ name: a })),
        threshold: 0.0, // for heatmap, we want full scores (no filtering)
      };
      const { data } = await api.post(`/align/clo/${selectedCourse}`, payload);
      setResult(data);
    } catch (e) {
      setErr(e?.response?.data?.detail || "Failed to compute alignment.");
    } finally {
      setLoading(false);
    }
  };

  // Build a matrix:
  // If backend returns result.matrix => use it
  // else approximate using pairs (only best matches marked)
  const matrix = useMemo(() => {
    if (!result) return [];
    if (Array.isArray(result.matrix)) return result.matrix;

    // fallback: matrix from pairs
    const aIndex = new Map(assessments.map((a, i) => [a, i]));
    const m = clos.map(() => assessments.map(() => 0));
    if (Array.isArray(result.pairs)) {
      result.pairs.forEach((p) => {
        const ci = clos.indexOf(p.clo);
        const ai = aIndex.get(p.assessment);
        if (ci >= 0 && typeof ai === "number") m[ci][ai] = clamp01(p.similarity);
      });
    }
    return m;
  }, [result, clos, assessments]);

  return (
    <div className="fade-in">
      <div className="page-header">
        <h1 className="page-title">CLO ↔ Assessment Heatmap</h1>
        <p className="page-subtitle">Visualize semantic similarity across all CLOs and assessments</p>
      </div>

      <div className="card">
        <div className="card-content">
          <select
            className="form-input"
            value={selectedCourse}
            onChange={(e) => setSelectedCourse(e.target.value)}
          >
            <option value="">Choose a course...</option>
            {courses.map((c) => (
              <option key={c.id} value={c.id}>
                {c.course_code} — {c.course_name}
              </option>
            ))}
          </select>

          <button className="btn-primary" style={{ marginTop: 12 }} onClick={run} disabled={loading}>
            {loading ? "Working..." : "Generate Heatmap"}
          </button>

          {err && <p style={{ color: "red", marginTop: 12 }}>{err}</p>}
        </div>
      </div>

      {result && (
        <div className="card" style={{ marginTop: 16 }}>
          <div className="card-header">
            <h2 className="card-title">Heatmap</h2>
          </div>
          <div className="card-content" style={{ overflowX: "auto" }}>
            <table style={{ borderCollapse: "collapse", width: "100%", minWidth: 900 }}>
              <thead>
                <tr>
                  <th style={{ textAlign: "left", padding: 10, borderBottom: "1px solid #e5e7eb" }}>CLO \\ Assessment</th>
                  {assessments.map((a, i) => (
                    <th key={i} style={{ textAlign: "left", padding: 10, borderBottom: "1px solid #e5e7eb" }}>
                      {a}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {clos.map((c, r) => (
                  <tr key={r}>
                    <td style={{ padding: 10, borderBottom: "1px solid #f1f5f9", fontWeight: 800 }}>
                      {c}
                    </td>
                    {assessments.map((_, col) => {
                      const sim = matrix?.[r]?.[col] ?? 0;
                      return (
                        <td
                          key={col}
                          title={`Similarity: ${(sim * 100).toFixed(1)}%`}
                          style={{
                            padding: 10,
                            borderBottom: "1px solid #f1f5f9",
                            background: cellBg(sim),
                            color: "white",
                            fontWeight: 900,
                            textAlign: "center",
                            borderRight: "1px solid rgba(255,255,255,0.15)",
                          }}
                        >
                          {(sim * 100).toFixed(0)}%
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>

            <p className="muted" style={{ marginTop: 10 }}>
              Tip: hover a cell to see exact similarity.
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
