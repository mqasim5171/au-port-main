// frontend/src/pages/CLOAlignment.js

import React, { useEffect, useMemo, useState } from "react";
import api from "../api";
import "../App.css";

/* -------------------- helpers -------------------- */

function normalizeCLOs(raw) {
  if (!Array.isArray(raw)) return [];
  return raw
    .map((x) => {
      if (typeof x === "string") return { text: x.trim() };
      if (x && typeof x === "object") {
        const t = (x.clo_text || x.text || x.statement || "").trim();
        return t ? { id: x.id, text: t } : null;
      }
      return null;
    })
    .filter(Boolean);
}

function normalizeAssessments(raw) {
  if (!raw) return [];
  if (Array.isArray(raw)) {
    return raw
      .map((x) => (typeof x === "string" ? x.trim() : (x?.name || "").trim()))
      .filter(Boolean);
  }
  return [];
}

function similarityColor(val) {
  if (val >= 0.75) return "#16a34a"; // green
  if (val >= 0.6) return "#f59e0b";  // amber
  return "#dc2626";                  // red
}

/* -------------------- component -------------------- */

export default function CLOAlignment() {
  const [courses, setCourses] = useState([]);
  const [selectedCourse, setSelectedCourse] = useState("");

  const [clos, setClos] = useState([]);
  const [assessmentsText, setAssessmentsText] = useState("");

  const [threshold, setThreshold] = useState(0.65);

  const [result, setResult] = useState(null);
  const [loadingAuto, setLoadingAuto] = useState(false);
  const [loadingRun, setLoadingRun] = useState(false);
  const [err, setErr] = useState("");

  /* -------------------- load courses -------------------- */

  useEffect(() => {
    api
      .get("/courses")
      .then((res) => setCourses(res.data || []))
      .catch(() => setCourses([]));
  }, []);

  /* -------------------- auto fetch CLOs + assessments -------------------- */

  useEffect(() => {
    setErr("");
    setResult(null);

    if (!selectedCourse) {
      setClos([]);
      setAssessmentsText("");
      return;
    }

    setLoadingAuto(true);

    api
      .get(`/align/${selectedCourse}/auto`)
      .then((res) => {
        const data = res.data || {};
        setClos(normalizeCLOs(data.clos));
        setAssessmentsText(normalizeAssessments(data.assessments).join("\n"));
      })
      .catch((e) => {
        setClos([]);
        setAssessmentsText("");
        setErr(
          e?.response?.data?.detail ||
            "Upload CLO / Course Guide before alignment."
        );
      })
      .finally(() => setLoadingAuto(false));
  }, [selectedCourse]);

  const cloPreview = useMemo(() => clos.map((c) => c.text), [clos]);

  /* -------------------- run alignment -------------------- */

  const analyze = async () => {
    setErr("");
    setResult(null);

    if (!selectedCourse) {
      setErr("Select a course first.");
      return;
    }

    const assessments = assessmentsText
      .split("\n")
      .map((s) => s.trim())
      .filter(Boolean)
      .map((name) => ({ name }));

    if (!clos.length) {
      setErr("No CLOs loaded.");
      return;
    }

    if (!assessments.length) {
      setErr("Enter at least one assessment.");
      return;
    }

    setLoadingRun(true);

    try {
      const payload = {
        clos: clos.map((c) => c.text),
        assessments,
        threshold,
      };

      const { data } = await api.post(
        `/align/clo/${selectedCourse}`,
        payload
      );

      setResult(data);
    } catch (e) {
      setErr(e?.response?.data?.detail || "Alignment failed");
    } finally {
      setLoadingRun(false);
    }
  };

  /* -------------------- UI -------------------- */

  return (
    <div className="fade-in">
      <div className="page-header">
        <h1 className="page-title">CLO Alignment</h1>
        <p className="page-subtitle">
          Explainable CLO ↔ Assessment semantic alignment
        </p>
      </div>

      {/* ---------- Course Select ---------- */}
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

          {loadingAuto && <p className="muted">Loading CLOs…</p>}

          {!!cloPreview.length && (
            <>
              {/* ---------- CLO Preview ---------- */}
              <div style={{ marginTop: 16 }}>
                <h3 className="card-title">Parsed CLOs</h3>
                <div className="box">
                  {cloPreview.map((c, i) => (
                    <div key={i} className="row">
                      <strong>CLO {i + 1}:</strong>&nbsp;{c}
                    </div>
                  ))}
                </div>
              </div>

              {/* ---------- Assessments ---------- */}
              <div style={{ marginTop: 16 }}>
                <h3 className="card-title">Assessments</h3>
                <textarea
                  className="form-input"
                  style={{ height: 120 }}
                  value={assessmentsText}
                  onChange={(e) => setAssessmentsText(e.target.value)}
                />
              </div>

              {/* ---------- Threshold ---------- */}
              <div style={{ marginTop: 12 }}>
                <label className="muted">
                  Similarity Threshold: {(threshold * 100).toFixed(0)}%
                </label>
                <input
                  type="range"
                  min="0.5"
                  max="0.9"
                  step="0.05"
                  value={threshold}
                  onChange={(e) => setThreshold(Number(e.target.value))}
                />
              </div>

              <button
                className="btn-primary"
                style={{ marginTop: 16 }}
                onClick={analyze}
                disabled={loadingRun}
              >
                {loadingRun ? "Analyzing…" : "Run Alignment"}
              </button>
            </>
          )}

          {err && <p style={{ color: "red", marginTop: 12 }}>{err}</p>}
        </div>
      </div>

      {/* ---------- RESULTS ---------- */}
      {result && (
        <div className="card" style={{ marginTop: 24 }}>
          <div className="card-header">
            <h2 className="card-title">Alignment Results</h2>
          </div>

          <div className="card-content">
            <p className="muted">
              Average similarity: {(result.avg_top * 100).toFixed(1)}%
            </p>

            {result.flags?.length ? (
              <p style={{ color: "#dc2626" }}>
                Flags: {result.flags.join(", ")}
              </p>
            ) : (
              <p style={{ color: "#16a34a" }}>No alignment flags</p>
            )}

            <hr />

            {result.pairs.map((p, i) => (
              <div key={i} style={{ marginBottom: 16 }}>
                <p><strong>CLO:</strong> {p.clo}</p>
                <p><strong>Assessment:</strong> {p.assessment}</p>
                <p style={{ color: similarityColor(p.similarity) }}>
                  Similarity: {(p.similarity * 100).toFixed(1)}%
                </p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
