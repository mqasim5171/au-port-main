import React, { useEffect, useState } from "react";
import api from "../api";
import {
  ArrowDownTrayIcon,
  DocumentTextIcon,
  PencilSquareIcon,
} from "@heroicons/react/24/outline";
import "../App.css";

function Reports() {
  const [courses, setCourses] = useState([]);
  const [selectedCourse, setSelectedCourse] = useState("");

  const [quality, setQuality] = useState(null);
  const [overrides, setOverrides] = useState([]);

  const [loading, setLoading] = useState(false);
  const [recomputing, setRecomputing] = useState(false);
  const [overrideOpen, setOverrideOpen] = useState(false);

  const [moduleName, setModuleName] = useState("quality");
  const [overriddenScore, setOverriddenScore] = useState("");
  const [reason, setReason] = useState("");

  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const selectedCourseObj = courses.find((c) => c.id === selectedCourse);

  useEffect(() => {
    api
      .get("/courses")
      .then((res) => setCourses(res.data || []))
      .catch(() => setError("Unable to load courses."));
  }, []);

  useEffect(() => {
    if (!selectedCourse) {
      setQuality(null);
      setOverrides([]);
      return;
    }

    loadQuality();
    loadOverrides();
    // eslint-disable-next-line
  }, [selectedCourse]);

  const loadQuality = async () => {
    try {
      const res = await api.get(`/courses/${selectedCourse}/quality-score`);
      setQuality(res.data || null);
    } catch {
      setQuality(null);
    }
  };

  const loadOverrides = async () => {
    try {
      const res = await api.get(`/overrides/${selectedCourse}`);
      setOverrides(res.data || []);
    } catch {
      setOverrides([]);
    }
  };

  const recomputeQuality = async () => {
    if (!selectedCourse) {
      setError("Please select a course first.");
      return;
    }

    setError("");
    setSuccess("");
    setRecomputing(true);

    try {
      const res = await api.post(`/courses/${selectedCourse}/recompute`);
      setQuality(res.data || null);
      setSuccess("Quality score recomputed successfully.");
    } catch (e) {
      setError(e?.response?.data?.detail || "Quality recompute failed.");
    } finally {
      setRecomputing(false);
    }
  };

  const getOriginalScore = () => {
    if (!quality) return 0;

    if (moduleName === "quality") {
      return quality.overall_score || 0;
    }

    if (moduleName === "completeness") {
      return quality.completeness_score || 0;
    }

    return 0;
  };

  const submitOverride = async () => {
    setError("");
    setSuccess("");

    if (!selectedCourse) {
      setError("Please select a course first.");
      return;
    }

    if (!overriddenScore) {
      setError("Please enter overridden score.");
      return;
    }

    const score = Number(overriddenScore);

    if (Number.isNaN(score) || score < 0 || score > 100) {
      setError("Overridden score must be between 0 and 100.");
      return;
    }

    if (!reason.trim()) {
      setError("Please enter a reason for the override.");
      return;
    }

    try {
      await api.post("/overrides/", {
        course_id: selectedCourse,
        module: moduleName,
        original_score: getOriginalScore(),
        overridden_score: score,
        reason: reason.trim(),
      });

      setSuccess("Manual override saved successfully.");
      setOverrideOpen(false);
      setOverriddenScore("");
      setReason("");

      await loadOverrides();
    } catch (e) {
      setError(e?.response?.data?.detail || "Failed to save override.");
    }
  };

  const openReport = async () => {
    if (!selectedCourse) {
      setError("Please select a course first.");
      return;
    }

    setError("");
    setLoading(true);

    try {
      const res = await api.get(`/courses/${selectedCourse}/qa-report`, {
        responseType: "blob",
      });

      const blob = new Blob([res.data], { type: "text/html" });
      const url = window.URL.createObjectURL(blob);
      window.open(url, "_blank");
    } catch (e) {
      setError(e?.response?.data?.detail || "Report generation failed.");
    } finally {
      setLoading(false);
    }
  };

  const downloadReport = async () => {
    if (!selectedCourse) {
      setError("Please select a course first.");
      return;
    }

    setError("");
    setLoading(true);

    try {
      const res = await api.get(`/courses/${selectedCourse}/qa-report`, {
        responseType: "blob",
      });

      const blob = new Blob([res.data], { type: "text/html" });
      const url = window.URL.createObjectURL(blob);

      const a = document.createElement("a");
      a.href = url;
      a.download = `${selectedCourseObj?.course_code || "course"}_qa_report.html`;
      a.click();

      window.URL.revokeObjectURL(url);
    } catch (e) {
      setError(e?.response?.data?.detail || "Report download failed.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fade-in">
      <div className="page-header">
        <h1 className="page-title">QA Reports</h1>
        <p className="page-subtitle">
          Generate course-based QA reports, recompute quality scores, and apply QEC manual overrides.
        </p>
      </div>

      <div className="card" style={{ marginBottom: 24 }}>
        <div className="card-header">
          <h2 className="card-title">Generate Report</h2>
        </div>

        <div className="card-content">
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "1fr auto auto auto auto",
              gap: 14,
              alignItems: "center",
              marginBottom: 18,
            }}
          >
            <select
              value={selectedCourse}
              onChange={(e) => setSelectedCourse(e.target.value)}
              className="form-input"
            >
              <option value="">Choose a course...</option>
              {courses.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.course_code} - {c.course_name}
                </option>
              ))}
            </select>

            <button
              onClick={recomputeQuality}
              className="btn btn-secondary"
              disabled={!selectedCourse || recomputing}
            >
              {recomputing ? "Recomputing..." : "Recompute Score"}
            </button>

            <button
              onClick={() => setOverrideOpen(true)}
              className="btn btn-secondary"
              disabled={!selectedCourse || !quality}
            >
              <PencilSquareIcon className="w-4 h-4" style={{ marginRight: 8 }} />
              Manual Override
            </button>

            <button
              onClick={openReport}
              className="btn btn-primary"
              disabled={!selectedCourse || loading}
            >
              <DocumentTextIcon className="w-4 h-4" style={{ marginRight: 8 }} />
              Preview
            </button>

            <button
              onClick={downloadReport}
              className="btn btn-success"
              disabled={!selectedCourse || loading}
            >
              <ArrowDownTrayIcon className="w-4 h-4" style={{ marginRight: 8 }} />
              Download
            </button>
          </div>

          {error && <p style={{ color: "#dc2626", marginBottom: 12 }}>{error}</p>}
          {success && <p style={{ color: "#166534", marginBottom: 12 }}>{success}</p>}

          {selectedCourseObj ? (
            <div
              style={{
                background: "#f8fafc",
                border: "1px solid #e2e8f0",
                borderRadius: 14,
                padding: 18,
              }}
            >
              <h3 style={{ marginBottom: 6 }}>
                {selectedCourseObj.course_code} - {selectedCourseObj.course_name}
              </h3>

              <p className="page-subtitle" style={{ margin: 0 }}>
                This report includes completeness score, CLO alignment, assessments,
                quality score, suggestions, and manual QA override records.
              </p>
            </div>
          ) : (
            <div
              style={{
                background: "#f8fafc",
                border: "1px dashed #cbd5e1",
                borderRadius: 14,
                padding: 22,
                textAlign: "center",
                color: "#64748b",
              }}
            >
              Select a course to generate its QA report.
            </div>
          )}
        </div>
      </div>

      {selectedCourse && (
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "1fr 1fr",
            gap: 24,
          }}
        >
          <div className="card">
            <div className="card-header">
              <h2 className="card-title">Current Quality Snapshot</h2>
            </div>

            <div className="card-content">
              {!quality ? (
                <div style={{ color: "#64748b" }}>
                  No quality score available. Click “Recompute Score” first.
                </div>
              ) : (
                <div style={{ display: "grid", gap: 12 }}>
                  <ScoreRow label="Overall Quality" value={quality.overall_score} />
                  <ScoreRow label="Completeness" value={quality.completeness_score} />
                  <ScoreRow label="CLO Alignment" value={quality.alignment_score} />
                  <ScoreRow label="Feedback" value={quality.feedback_score} />
                  <ScoreRow label="Grading" value={quality.grading_score} />

                  {quality.suggestions?.length > 0 && (
                    <div
                      style={{
                        marginTop: 10,
                        background: "#f8fafc",
                        border: "1px solid #e2e8f0",
                        borderRadius: 12,
                        padding: 12,
                      }}
                    >
                      <div style={{ fontWeight: 900, marginBottom: 8 }}>
                        System Suggestions
                      </div>

                      <ul style={{ margin: 0, paddingLeft: 18 }}>
                        {quality.suggestions.map((s, idx) => (
                          <li key={idx} style={{ fontSize: 13, color: "#475569", marginBottom: 5 }}>
                            {s}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>

          <div className="card">
            <div className="card-header">
              <h2 className="card-title">Manual Override History</h2>
            </div>

            <div className="card-content">
              {overrides.length === 0 ? (
                <div style={{ color: "#64748b" }}>
                  No manual overrides have been recorded for this course.
                </div>
              ) : (
                overrides.map((item, idx) => (
                  <div
                    key={idx}
                    style={{
                      padding: 12,
                      border: "1px solid #e2e8f0",
                      borderRadius: 12,
                      marginBottom: 10,
                      background: "#f8fafc",
                    }}
                  >
                    <div style={{ display: "flex", justifyContent: "space-between", gap: 10 }}>
                      <div style={{ fontWeight: 900, textTransform: "capitalize" }}>
                        {item.module} Override
                      </div>

                      <div style={{ fontSize: 12, color: "#64748b" }}>
                        {item.created_at
                          ? new Date(item.created_at).toLocaleString()
                          : ""}
                      </div>
                    </div>

                    <div style={{ marginTop: 8, fontSize: 13, color: "#475569" }}>
                      Original Score: <b>{item.original_score}%</b> → Overridden Score:{" "}
                      <b>{item.overridden_score}%</b>
                    </div>

                    <div style={{ marginTop: 6, fontSize: 13, color: "#334155" }}>
                      Reason: {item.reason}
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      )}

      {overrideOpen && (
        <div
          style={{
            position: "fixed",
            inset: 0,
            background: "rgba(15, 23, 42, 0.45)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 999,
            padding: 20,
          }}
        >
          <div
            className="card"
            style={{
              width: "100%",
              maxWidth: 560,
              background: "#ffffff",
            }}
          >
            <div className="card-header">
              <h2 className="card-title">Apply Manual Override</h2>
            </div>

            <div className="card-content">
              <p className="page-subtitle" style={{ marginBottom: 16 }}>
                This creates an auditable QEC/Admin override record. Use it only when
                manual academic review justifies adjusting the automated score.
              </p>

              <div style={{ display: "grid", gap: 14 }}>
                <div>
                  <label style={labelStyle}>Module</label>
                  <select
                    className="form-input"
                    value={moduleName}
                    onChange={(e) => setModuleName(e.target.value)}
                  >
                    <option value="quality">Quality</option>
                    <option value="completeness">Completeness</option>
                  </select>
                </div>

                <div>
                  <label style={labelStyle}>Original Score</label>
                  <input
                    className="form-input"
                    value={`${getOriginalScore()}%`}
                    disabled
                  />
                </div>

                <div>
                  <label style={labelStyle}>Overridden Score</label>
                  <input
                    className="form-input"
                    type="number"
                    min="0"
                    max="100"
                    value={overriddenScore}
                    onChange={(e) => setOverriddenScore(e.target.value)}
                    placeholder="Enter score between 0 and 100"
                  />
                </div>

                <div>
                  <label style={labelStyle}>Justification / Reason</label>
                  <textarea
                    className="form-input"
                    style={{ minHeight: 110 }}
                    value={reason}
                    onChange={(e) => setReason(e.target.value)}
                    placeholder="Example: Manual QEC review found that uploaded supporting evidence was valid but not detected automatically."
                  />
                </div>

                <div
                  style={{
                    display: "flex",
                    justifyContent: "flex-end",
                    gap: 10,
                    marginTop: 8,
                  }}
                >
                  <button
                    className="btn btn-secondary"
                    onClick={() => setOverrideOpen(false)}
                  >
                    Cancel
                  </button>

                  <button className="btn btn-success" onClick={submitOverride}>
                    Save Override
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function ScoreRow({ label, value }) {
  const score = Number(value || 0);

  const color =
    score >= 80 ? "#166534" : score >= 60 ? "#854d0e" : "#991b1b";

  const bg =
    score >= 80 ? "#dcfce7" : score >= 60 ? "#fef9c3" : "#fee2e2";

  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: "160px 1fr 70px",
        alignItems: "center",
        gap: 12,
      }}
    >
      <div style={{ fontWeight: 800, color: "#334155" }}>{label}</div>

      <div
        style={{
          height: 10,
          borderRadius: 999,
          background: "#e5e7eb",
          overflow: "hidden",
        }}
      >
        <div
          style={{
            width: `${Math.min(100, Math.max(0, score))}%`,
            height: "100%",
            background: color,
          }}
        />
      </div>

      <span
        style={{
          display: "inline-flex",
          justifyContent: "center",
          padding: "4px 8px",
          borderRadius: 999,
          background: bg,
          color,
          fontWeight: 900,
          fontSize: 12,
        }}
      >
        {score}%
      </span>
    </div>
  );
}

const labelStyle = {
  display: "block",
  fontSize: 13,
  fontWeight: 800,
  color: "#475569",
  marginBottom: 6,
};

export default Reports;