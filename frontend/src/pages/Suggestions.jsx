import React, { useEffect, useState } from "react";
import api from "../api";

function Suggestions() {
  const [courses, setCourses] = useState([]);
  const [selectedCourse, setSelectedCourse] = useState("");
  const [suggestions, setSuggestions] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  // ------------------ Load courses ------------------
  useEffect(() => {
    api.get("/courses")
      .then(res => setCourses(res.data || []))
      .catch(() => setCourses([]));
  }, []);

  // ------------------ Load suggestions ------------------
  const loadSuggestions = async (courseId) => {
    setLoading(true);
    setError("");
    try {
      const res = await api.get(`/courses/${courseId}/suggestions`);
      setSuggestions(res.data || []);
    } catch {
      setSuggestions([]);
      setError("Failed to load suggestions.");
    } finally {
      setLoading(false);
    }
  };

  // ------------------ Generate AI suggestions ------------------
  const generateSuggestions = async () => {
    if (!selectedCourse) return;
    setLoading(true);
    setError("");
    try {
      await api.post(`/courses/${selectedCourse}/suggestions/auto`);
      await loadSuggestions(selectedCourse);
    } catch {
      setError("AI suggestion generation failed.");
    } finally {
      setLoading(false);
    }
  };

  // ------------------ Course change ------------------
  useEffect(() => {
    if (selectedCourse) {
      loadSuggestions(selectedCourse);
    } else {
      setSuggestions([]);
    }
  }, [selectedCourse]);

  // ------------------ UI ------------------
  return (
    <div className="fade-in">
      <div className="page-header">
        <h1 className="page-title">AI Quality Suggestions</h1>
        <p className="page-subtitle">
          Live, AI-generated academic improvement suggestions based on current course data
        </p>
      </div>

      {/* Course selector */}
      <div className="card" style={{ marginBottom: 24 }}>
        <div className="card-header">
          <h2 className="card-title">Select Course</h2>
        </div>
        <div className="card-content">
          <select
            value={selectedCourse}
            onChange={(e) => setSelectedCourse(e.target.value)}
            className="form-input"
            style={{ maxWidth: 420 }}
          >
            <option value="">Choose a course…</option>
            {courses.map(c => (
              <option key={c.id} value={c.id}>
                {c.course_code} — {c.course_name}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Actions */}
      {selectedCourse && (
        <div className="card" style={{ marginBottom: 24 }}>
          <div className="card-header">
            <h2 className="card-title">AI Actions</h2>
          </div>
          <div className="card-content" style={{ display: "flex", gap: 12 }}>
            <button
              className="btn-primary"
              onClick={generateSuggestions}
              disabled={loading}
            >
              {loading ? "Analyzing…" : "Generate AI Suggestions"}
            </button>

            <button
              className="btn-secondary"
              onClick={() => loadSuggestions(selectedCourse)}
              disabled={loading}
            >
              Refresh
            </button>
          </div>
        </div>
      )}

      {/* Errors */}
      {error && (
        <div className="card" style={{ borderLeft: "4px solid #ef4444" }}>
          <div className="card-content" style={{ color: "#b91c1c" }}>
            {error}
          </div>
        </div>
      )}

      {/* Suggestions list */}
      {selectedCourse && (
        <div className="card">
          <div className="card-header">
            <h2 className="card-title">Improvement Suggestions</h2>
          </div>
          <div className="card-content">
            {loading ? (
              <p style={{ color: "#64748b" }}>Loading suggestions…</p>
            ) : suggestions.length === 0 ? (
              <p style={{ color: "#64748b" }}>
                No suggestions available for this course.
              </p>
            ) : (
              suggestions.map((s, i) => (
                <div
                  key={s.id || i}
                  style={{
                    padding: 16,
                    borderRadius: 10,
                    marginBottom: 16,
                    borderLeft: `4px solid ${
                      s.priority === "high"
                        ? "#ef4444"
                        : s.priority === "medium"
                        ? "#f59e0b"
                        : "#10b981"
                    }`,
                    background: "#f8fafc",
                    border: "1px solid #e5e7eb",
                  }}
                >
                  <div style={{ fontWeight: 600, marginBottom: 4 }}>
                    Suggestion {i + 1}
                  </div>

                  <div style={{ fontSize: 14, marginBottom: 8 }}>
                    {s.text}
                  </div>

                  <div style={{ fontSize: 12, color: "#64748b" }}>
                    <strong>Priority:</strong> {s.priority} ·{" "}
                    <strong>Status:</strong> {s.status} ·{" "}
                    <strong>Source:</strong>{" "}
                    {s.source === "quality_engine"
                      ? "AI Engine"
                      : "Manual (QEC)"}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
}

export default Suggestions;
