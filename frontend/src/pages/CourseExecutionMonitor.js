// src/pages/CourseExecutionMonitor.js

import React, { useEffect, useState } from "react";
import api from "../api";
import "../App.css";

const statusColors = {
  on_track: "#22c55e",
  ahead: "#3b82f6",
  behind: "#f97316",
  skipped: "#ef4444",

  missing_delivery: "#ef4444",
  not_started: "#6b7280",
  uploaded_pending_review: "#f59e0b",
};

const statusLabels = {
  on_track: "ON TRACK",
  ahead: "AHEAD",
  behind: "BEHIND",
  skipped: "SKIPPED",

  missing_delivery: "MISSING DELIVERY",
  not_started: "NOT STARTED",
  uploaded_pending_review: "UPLOADED / REVIEW PENDING",
};

const normalizeStatus = (status) => {
  return String(status || "not_started").toLowerCase();
};

const getStatusLabel = (status) => {
  const key = normalizeStatus(status);
  return statusLabels[key] || key.replaceAll("_", " ").toUpperCase();
};

const EvidencePill = ({ children }) => {
  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        padding: "4px 9px",
        borderRadius: 999,
        background: "#eff6ff",
        color: "#1d4ed8",
        border: "1px solid #bfdbfe",
        fontSize: 12,
        fontWeight: 700,
        marginRight: 6,
        marginBottom: 6,
      }}
    >
      {children}
    </span>
  );
};

const CourseExecutionMonitor = () => {
  const [courses, setCourses] = useState([]);
  const [selectedCourse, setSelectedCourse] = useState(null);

  const [summary, setSummary] = useState(null);
  const [loadingSummary, setLoadingSummary] = useState(false);

  const [deviations, setDeviations] = useState([]);
  const [loadingDeviations, setLoadingDeviations] = useState(false);

  const [showModal, setShowModal] = useState(false);
  const [modalWeek, setModalWeek] = useState(null);

  const [modalForm, setModalForm] = useState({
    delivered_topics: "",
    delivered_assessments: "",
    evidence_links: "",
    coverage_status: "on_track",
  });

  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);

  // ---------- helpers ----------

  const loadCourses = () => {
    api
      .get("/courses")
      .then((res) => {
        setCourses(res.data || []);
      })
      .catch(() => setCourses([]));
  };

  const loadSummary = (courseId) => {
    if (!courseId) return;

    setLoadingSummary(true);

    api
      .get(`/courses/${courseId}/weekly-status-summary`)
      .then((res) => setSummary(res.data))
      .catch(() => setSummary(null))
      .finally(() => setLoadingSummary(false));
  };

  const loadDeviations = (courseId) => {
    if (!courseId) return;

    setLoadingDeviations(true);

    api
      .get(`/courses/${courseId}/deviations`)
      .then((res) => setDeviations(res.data || []))
      .catch(() => setDeviations([]))
      .finally(() => setLoadingDeviations(false));
  };

  useEffect(() => {
    loadCourses();
  }, []);

  useEffect(() => {
    if (!selectedCourse) {
      setSummary(null);
      setDeviations([]);
      return;
    }

    loadSummary(selectedCourse);
    loadDeviations(selectedCourse);
  }, [selectedCourse]);

  const openModalForWeek = (week) => {
    if (!summary) return;

    const existing = summary.items.find((i) => i.week_number === week);

    setModalWeek(week);

    setModalForm({
      delivered_topics: existing?.delivered_topics || "",
      delivered_assessments: existing?.delivered_assessments || "",
      evidence_links: existing?.latest_upload_id || "",
      coverage_status:
        existing?.coverage_status &&
        !["missing_delivery", "not_started", "uploaded_pending_review"].includes(
          normalizeStatus(existing.coverage_status)
        )
          ? existing.coverage_status
          : "on_track",
    });

    setError(null);
    setShowModal(true);
  };

  const handleSaveExecution = () => {
    if (!selectedCourse || !modalWeek) return;

    setSaving(true);
    setError(null);

    api
      .post(`/courses/${selectedCourse}/weekly-execution/${modalWeek}`, {
        week_number: modalWeek,
        delivered_topics: modalForm.delivered_topics,
        delivered_assessments: modalForm.delivered_assessments,
        coverage_status: modalForm.coverage_status,
        evidence_links: modalForm.evidence_links,
      })
      .then(() => {
        setShowModal(false);
        loadSummary(selectedCourse);
        loadDeviations(selectedCourse);
      })
      .catch((e) => {
        const msg =
          e?.response?.data?.detail ||
          e?.message ||
          "Failed to save execution.";

        setError(msg);
      })
      .finally(() => setSaving(false));
  };

  const handleResolveDeviation = (id, currentResolved) => {
    api
      .put(`/courses/deviations/${id}/resolve`, {
        resolved: !currentResolved,
      })
      .then(() => loadDeviations(selectedCourse));
  };

  const renderStatusHint = (statusKey, item) => {
    if (statusKey === "missing_delivery") {
      return (
        <div
          className="alert alert-error"
          style={{
            marginTop: 8,
            padding: 8,
            borderRadius: 8,
            fontSize: 13,
          }}
        >
          Planned content exists, but no delivered content, weekly upload, or
          assessment evidence has been recorded.
        </div>
      );
    }

    if (statusKey === "uploaded_pending_review") {
      return (
        <div
          className="alert"
          style={{
            marginTop: 8,
            padding: 8,
            borderRadius: 8,
            fontSize: 13,
            background: "#fffbeb",
            border: "1px solid #fde68a",
            color: "#92400e",
          }}
        >
          Evidence exists for this week. Review the uploaded material or add
          delivered topics to confirm whether it is on track.
        </div>
      );
    }

    if (statusKey === "not_started") {
      return (
        <div
          className="alert"
          style={{
            marginTop: 8,
            padding: 8,
            borderRadius: 8,
            fontSize: 13,
            background: "#f8fafc",
            border: "1px solid #e5e7eb",
            color: "#475569",
          }}
        >
          No plan, upload, assessment, or delivery update exists for this week.
        </div>
      );
    }

    return null;
  };

  // ---------- render ----------

  return (
    <div className="page-container">
      <h1 className="page-title">Course Execution Monitor</h1>

      <p className="page-subtitle">
        Track weekly delivery against the planned course guide. A week is only
        considered on track after actual delivered topics or upload evidence is
        added.
      </p>

      {/* Course selector */}
      <div className="card" style={{ marginBottom: "16px" }}>
        <label className="form-label">Select Course</label>

        <select
          className="form-select"
          value={selectedCourse || ""}
          onChange={(e) => setSelectedCourse(e.target.value || null)}
        >
          <option value="">-- Choose a course --</option>

          {courses.map((c) => (
            <option key={c.id} value={c.id}>
              {c.course_code} – {c.course_name}
            </option>
          ))}
        </select>
      </div>

      {selectedCourse && (
        <>
          {/* Timeline view */}
          <div className="card">
            <div className="card-header">
              <h2>Weekly Timeline (Weeks 1–16)</h2>
            </div>

            {loadingSummary ? (
              <div>Loading weekly status…</div>
            ) : summary && summary.items && summary.items.length > 0 ? (
              <div className="timeline-grid">
                {summary.items.map((item) => {
                  const statusKey = normalizeStatus(item.coverage_status);

                  return (
                    <div key={item.week_number} className="week-card">
                      <div className="week-card-header">
                        <span className="week-number">
                          Week {item.week_number}
                        </span>

                        <span
                          className="status-badge"
                          style={{
                            backgroundColor:
                              statusColors[statusKey] || "#6b7280",
                          }}
                        >
                          {getStatusLabel(statusKey)}
                        </span>
                      </div>

                      <div className="week-section">
                        <div className="week-label">Planned Topics</div>

                        <div className="week-text">
                          {item.planned_topics || <em>— not set —</em>}
                        </div>
                      </div>

                      <div className="week-section">
                        <div className="week-label">Delivered Topics</div>

                        <div className="week-text">
                          {item.delivered_topics || <em>— no update —</em>}
                        </div>
                      </div>

                      <div className="week-section">
                        <div className="week-label">Auto Evidence</div>

                        <div className="week-text">
                          {item.upload_count > 0 && (
                            <EvidencePill>
                              {item.upload_count} weekly upload
                              {item.upload_count > 1 ? "s" : ""}
                            </EvidencePill>
                          )}

                          {item.assessment_count > 0 && (
                            <EvidencePill>
                              {item.assessment_count} assessment
                              {item.assessment_count > 1 ? "s" : ""}
                            </EvidencePill>
                          )}

                          {!item.upload_count && !item.assessment_count && (
                            <em>— no auto evidence —</em>
                          )}

                          {item.latest_upload_name && (
                            <div style={{ marginTop: 6 }}>
                              Latest upload: <b>{item.latest_upload_name}</b>
                            </div>
                          )}

                          {item.evidence_summary && (
                            <div style={{ marginTop: 6 }}>
                              {item.evidence_summary}
                            </div>
                          )}
                        </div>
                      </div>

                      {item.assessment_titles &&
                        item.assessment_titles.length > 0 && (
                          <div className="week-section">
                            <div className="week-label">Assessments</div>

                            <div className="week-text">
                              {item.assessment_titles.map((a, idx) => (
                                <div key={idx}>• {a}</div>
                              ))}
                            </div>
                          </div>
                        )}

                      {item.auto_reason && (
                        <div
                          className="alert"
                          style={{
                            marginTop: 8,
                            padding: 8,
                            borderRadius: 8,
                            fontSize: 13,
                            background: "#f8fafc",
                            border: "1px solid #e5e7eb",
                            color: "#334155",
                          }}
                        >
                          {item.auto_reason}
                        </div>
                      )}

                      {renderStatusHint(statusKey, item)}

                      <button
                        className="btn-primary"
                        style={{ marginTop: "8px" }}
                        onClick={() => openModalForWeek(item.week_number)}
                      >
                        Update execution
                      </button>
                    </div>
                  );
                })}
              </div>
            ) : (
              <div>No weekly plan/status found for this course yet.</div>
            )}
          </div>

          {/* Deviation dashboard */}
          <div className="card" style={{ marginTop: "16px" }}>
            <div className="card-header">
              <h2>Deviation Dashboard</h2>
            </div>

            {loadingDeviations ? (
              <div>Loading deviations…</div>
            ) : deviations.length === 0 ? (
              <div>No deviations logged for this course.</div>
            ) : (
              <table className="table">
                <thead>
                  <tr>
                    <th>Week</th>
                    <th>Issue</th>
                    <th>Details</th>
                    <th>Status</th>
                    <th>Resolve</th>
                  </tr>
                </thead>

                <tbody>
                  {deviations.map((d) => (
                    <tr key={d.id}>
                      <td>Week {d.week_number}</td>
                      <td>{d.type}</td>
                      <td style={{ maxWidth: "350px" }}>{d.details}</td>
                      <td>{d.resolved ? "Resolved" : "Open"}</td>
                      <td>
                        <button
                          className="btn-secondary"
                          onClick={() =>
                            handleResolveDeviation(d.id, d.resolved)
                          }
                        >
                          {d.resolved ? "Mark as open" : "Resolve"}
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>

          {/* Modal */}
          {showModal && (
            <div className="modal-backdrop">
              <div className="modal">
                <div className="modal-header">
                  <h3>Update Week {modalWeek} Execution</h3>

                  <button
                    className="icon-button"
                    onClick={() => setShowModal(false)}
                  >
                    ✕
                  </button>
                </div>

                <div className="modal-body">
                  {error && (
                    <div className="alert alert-error" style={{ marginBottom: 8 }}>
                      {error}
                    </div>
                  )}

                  <label className="form-label">Delivered Topics</label>

                  <textarea
                    className="form-textarea"
                    rows={4}
                    value={modalForm.delivered_topics}
                    placeholder="Write what was actually delivered in this week..."
                    onChange={(e) =>
                      setModalForm((f) => ({
                        ...f,
                        delivered_topics: e.target.value,
                      }))
                    }
                  />

                  <label className="form-label" style={{ marginTop: 8 }}>
                    Delivered Assessments
                  </label>

                  <textarea
                    className="form-textarea"
                    rows={3}
                    value={modalForm.delivered_assessments}
                    placeholder="Example: Quiz 1 conducted, Assignment 1 discussed..."
                    onChange={(e) =>
                      setModalForm((f) => ({
                        ...f,
                        delivered_assessments: e.target.value,
                      }))
                    }
                  />

                  <label className="form-label" style={{ marginTop: 8 }}>
                    Evidence Links / Upload IDs
                  </label>

                  <input
                    className="form-input"
                    value={modalForm.evidence_links}
                    placeholder="Paste upload IDs, links, or notes as evidence..."
                    onChange={(e) =>
                      setModalForm((f) => ({
                        ...f,
                        evidence_links: e.target.value,
                      }))
                    }
                  />

                  <label className="form-label" style={{ marginTop: 8 }}>
                    Coverage Status
                  </label>

                  <select
                    className="form-select"
                    value={modalForm.coverage_status}
                    onChange={(e) =>
                      setModalForm((f) => ({
                        ...f,
                        coverage_status: e.target.value,
                      }))
                    }
                  >
                    <option value="on_track">On track</option>
                    <option value="behind">Behind</option>
                    <option value="ahead">Ahead</option>
                    <option value="skipped">Skipped</option>
                    <option value="missing_delivery">Missing delivery</option>
                    <option value="uploaded_pending_review">
                      Uploaded pending review
                    </option>
                    <option value="not_started">Not started</option>
                  </select>

                  <p className="page-subtitle" style={{ marginTop: 8 }}>
                    Note: if delivered topics, delivered assessments, and evidence
                    are all empty, the backend will automatically save this week
                    as missing delivery.
                  </p>
                </div>

                <div className="modal-footer">
                  <button
                    className="btn-secondary"
                    onClick={() => setShowModal(false)}
                    disabled={saving}
                  >
                    Cancel
                  </button>

                  <button
                    className="btn-primary"
                    onClick={handleSaveExecution}
                    disabled={saving}
                  >
                    {saving ? "Saving…" : "Save"}
                  </button>
                </div>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
};

export default CourseExecutionMonitor;