import React, { useEffect, useMemo, useState } from "react";
import api from "../api";

const styles = {
  page: {
    display: "grid",
    gap: 16,
    maxWidth: 1180,
    margin: "0 auto",
  },
  hero: {
    background:
      "linear-gradient(135deg, rgba(37,99,235,0.10), rgba(16,185,129,0.08))",
    border: "1px solid #e5e7eb",
    borderRadius: 20,
    padding: 22,
  },
  card: {
    background: "#fff",
    border: "1px solid #e5e7eb",
    borderRadius: 18,
    padding: 18,
    boxShadow: "0 10px 25px rgba(15,23,42,0.05)",
  },
  grid2: {
    display: "grid",
    gridTemplateColumns: "360px 1fr",
    gap: 16,
    alignItems: "start",
  },
  row: {
    display: "flex",
    gap: 10,
    alignItems: "center",
    flexWrap: "wrap",
  },
  title: {
    margin: 0,
    color: "#111827",
    fontSize: 26,
    fontWeight: 900,
  },
  subtitle: {
    marginTop: 8,
    color: "#6b7280",
    lineHeight: 1.6,
  },
  h3: {
    margin: 0,
    color: "#111827",
    fontSize: 18,
    fontWeight: 900,
  },
  label: {
    display: "block",
    fontSize: 13,
    fontWeight: 800,
    color: "#374151",
    marginBottom: 7,
  },
  select: {
    width: "100%",
    border: "1px solid #d1d5db",
    borderRadius: 12,
    padding: "11px 12px",
    outline: "none",
    background: "#fff",
  },
  fileBox: {
    border: "1px dashed #cbd5e1",
    borderRadius: 16,
    padding: 16,
    background: "#f8fafc",
  },
  btnPrimary: {
    border: "none",
    background: "#2563eb",
    color: "#fff",
    borderRadius: 12,
    padding: "11px 16px",
    fontWeight: 800,
    cursor: "pointer",
  },
  btn: {
    border: "1px solid #d1d5db",
    background: "#fff",
    color: "#111827",
    borderRadius: 12,
    padding: "11px 16px",
    fontWeight: 800,
    cursor: "pointer",
  },
  chip: {
    display: "inline-flex",
    alignItems: "center",
    gap: 6,
    borderRadius: 999,
    padding: "5px 10px",
    fontSize: 12,
    fontWeight: 800,
    background: "#eff6ff",
    color: "#1d4ed8",
    border: "1px solid #bfdbfe",
  },
  muted: {
    color: "#6b7280",
    fontSize: 13,
    lineHeight: 1.5,
  },
  weekCard: {
    border: "1px solid #e5e7eb",
    borderRadius: 14,
    padding: 14,
    background: "#fff",
  },
  weekNo: {
    width: 44,
    height: 44,
    borderRadius: 14,
    background: "#eff6ff",
    color: "#1d4ed8",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    fontWeight: 900,
  },
  alert: {
    border: "1px solid #fecaca",
    background: "#fff1f2",
    color: "#991b1b",
    borderRadius: 14,
    padding: 12,
    fontWeight: 700,
  },
  success: {
    border: "1px solid #bbf7d0",
    background: "#f0fdf4",
    color: "#166534",
    borderRadius: 14,
    padding: 12,
    fontWeight: 700,
  },
};

function normalizeRole(role) {
  const r = String(role || "").trim().toLowerCase();

  if (r === "course lead") return "course_lead";
  if (r === "faculty member") return "faculty";
  if (r === "instructor") return "faculty";

  return r;
}

function shortPath(path) {
  if (!path) return "No course guide uploaded yet";
  const parts = String(path).split(/[\\/]/);
  return parts[parts.length - 1] || path;
}

function formatDate(value) {
  if (!value) return "-";
  try {
    return new Date(value).toLocaleString();
  } catch {
    return String(value);
  }
}

export default function CourseGuideUpload({ user }) {
  const role = normalizeRole(user?.role);

  const isCourseLead = useMemo(() => {
    return role === "course_lead";
  }, [role]);

  const [courses, setCourses] = useState([]);
  const [courseId, setCourseId] = useState("");
  const [file, setFile] = useState(null);
  const [plans, setPlans] = useState([]);
  const [status, setStatus] = useState(null);

  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState("");
  const [message, setMessage] = useState("");

  const selectedCourse = useMemo(
    () => courses.find((c) => c.id === courseId),
    [courses, courseId]
  );

  const planStats = useMemo(() => {
    const total = plans.length;
    const withTopics = plans.filter((p) =>
      String(p.planned_topics || "").trim()
    ).length;

    return {
      total,
      withTopics,
      empty: Math.max(0, total - withTopics),
      percent: total ? Math.round((withTopics / total) * 100) : 0,
    };
  }, [plans]);

  const loadCourses = async () => {
    setErr("");
    const res = await api.get("/course-lead/my-courses");
    const list = res.data || [];

    setCourses(list);

    if (!courseId && list.length) {
      setCourseId(list[0].id);
    }
  };

  const loadPlans = async (id) => {
    if (!id) return;

    const res = await api.get(`/course-lead/courses/${id}/weekly-plans`);
    setPlans(res.data || []);
  };

  const loadStatus = async (id) => {
    if (!id) return;

    try {
      const res = await api.get(`/course-lead/courses/${id}/course-guide/status`);
      setStatus(res.data || null);
    } catch {
      setStatus(null);
    }
  };

  const refreshAll = async (id = courseId) => {
    if (!id) return;

    setLoading(true);
    setErr("");

    try {
      await Promise.all([loadPlans(id), loadStatus(id)]);
    } catch (e) {
      setErr(e?.response?.data?.detail || "Failed to load course guide data");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (!isCourseLead) return;

    setLoading(true);

    loadCourses()
      .catch((e) => setErr(e?.response?.data?.detail || "Failed to load courses"))
      .finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isCourseLead]);

  useEffect(() => {
    if (!courseId) return;
    refreshAll(courseId);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [courseId]);

  const upload = async () => {
    setErr("");
    setMessage("");

    if (!courseId) {
      setErr("Select a course first.");
      return;
    }

    if (!file) {
      setErr("Choose a PDF or DOCX course guide first.");
      return;
    }

    const name = file.name || "";
    const isAllowed = name.toLowerCase().endsWith(".pdf") || name.toLowerCase().endsWith(".docx");

    if (!isAllowed) {
      setErr("Only PDF and DOCX files are allowed.");
      return;
    }

    setBusy(true);

    try {
      const fd = new FormData();
      fd.append("file", file);

      const res = await api.post(
        `/course-lead/courses/${courseId}/course-guide/upload`,
        fd,
        {
          headers: { "Content-Type": "multipart/form-data" },
        }
      );

      setFile(null);
      setMessage(
        `Course guide uploaded successfully. Weekly plan generated for ${
          res?.data?.weeks_created || 16
        } weeks.`
      );

      await refreshAll(courseId);
    } catch (e) {
      console.error(e);
      setErr(e?.response?.data?.detail || "Course guide upload failed");
    } finally {
      setBusy(false);
    }
  };

  if (!isCourseLead) {
    return (
      <div style={styles.page}>
        <div style={styles.card}>
          <h2 style={styles.title}>Course Guide Upload</h2>
          <p style={styles.subtitle}>
            Only the assigned Course Lead can access and upload the course guide.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div style={styles.page}>
      <div style={styles.hero}>
        <div style={styles.row}>
          <span style={styles.chip}>Course Lead Workspace</span>
          <span style={styles.chip}>Week 1–16 Plan Generator</span>
        </div>

        <h2 style={{ ...styles.title, marginTop: 14 }}>
          Course Guide Management
        </h2>

        <p style={styles.subtitle}>
          Upload the official course guide once, and the system will extract the
          content and generate structured weekly plans. These plans are then used
          to compare weekly uploads against the planned course execution.
        </p>
      </div>

      {err && <div style={styles.alert}>{err}</div>}
      {message && <div style={styles.success}>{message}</div>}

      <div style={styles.grid2}>
        <div style={{ display: "grid", gap: 16 }}>
          <div style={styles.card}>
            <h3 style={styles.h3}>1. Select Course</h3>
            <p style={styles.muted}>
              You will only see courses where you are assigned as Course Lead.
            </p>

            <div style={{ marginTop: 14 }}>
              <label style={styles.label}>Course</label>

              <select
                style={styles.select}
                value={courseId}
                onChange={(e) => {
                  setCourseId(e.target.value);
                  setFile(null);
                  setMessage("");
                  setErr("");
                }}
              >
                {courses.length === 0 ? (
                  <option value="">No assigned courses</option>
                ) : (
                  courses.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.course_code} — {c.course_name}
                    </option>
                  ))
                )}
              </select>
            </div>

            {selectedCourse && (
              <div
                style={{
                  marginTop: 14,
                  padding: 12,
                  borderRadius: 14,
                  background: "#f9fafb",
                  border: "1px solid #e5e7eb",
                }}
              >
                <div style={{ fontWeight: 900, color: "#111827" }}>
                  {selectedCourse.course_code}
                </div>
                <div style={styles.muted}>{selectedCourse.course_name}</div>
                <div style={{ ...styles.muted, marginTop: 4 }}>
                  Department: <b>{selectedCourse.department || "-"}</b>
                </div>
              </div>
            )}
          </div>

          <div style={styles.card}>
            <h3 style={styles.h3}>2. Upload Course Guide</h3>
            <p style={styles.muted}>
              Upload a PDF or DOCX file. The system will extract text and create
              Week 1 to Week 16 plans.
            </p>

            <div style={{ ...styles.fileBox, marginTop: 14 }}>
              <label style={styles.label}>Course Guide File</label>

              <input
                type="file"
                accept=".pdf,.docx"
                onChange={(e) => {
                  setFile(e.target.files?.[0] || null);
                  setMessage("");
                  setErr("");
                }}
              />

              <div style={{ ...styles.muted, marginTop: 10 }}>
                Selected: <b>{file?.name || "No file selected"}</b>
              </div>

              <button
                style={{
                  ...styles.btnPrimary,
                  marginTop: 14,
                  width: "100%",
                  opacity: busy || !file || !courseId ? 0.65 : 1,
                }}
                onClick={upload}
                disabled={busy || !file || !courseId}
              >
                {busy ? "Uploading & Generating..." : "Upload & Generate Weekly Plan"}
              </button>
            </div>
          </div>

          <div style={styles.card}>
            <h3 style={styles.h3}>Current Course Guide</h3>

            <div style={{ marginTop: 12 }}>
              <div style={styles.muted}>Uploaded File</div>
              <div style={{ fontWeight: 900, color: "#111827", marginTop: 4 }}>
                {shortPath(status?.course_guide_path)}
              </div>
            </div>

            <div style={{ marginTop: 12 }}>
              <div style={styles.muted}>Extracted Text Length</div>
              <div style={{ fontWeight: 900, color: "#111827", marginTop: 4 }}>
                {status?.text_length ?? 0} characters
              </div>
            </div>

            <div style={{ marginTop: 12 }}>
              <div style={styles.muted}>Weekly Plans</div>
              <div style={{ fontWeight: 900, color: "#111827", marginTop: 4 }}>
                {status?.weekly_plan_count ?? plans.length} generated
              </div>
            </div>

            <button
              style={{ ...styles.btn, marginTop: 14, width: "100%" }}
              onClick={() => refreshAll(courseId)}
              disabled={!courseId || loading}
            >
              {loading ? "Refreshing..." : "Refresh"}
            </button>
          </div>
        </div>

        <div style={styles.card}>
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              gap: 12,
              alignItems: "center",
              flexWrap: "wrap",
            }}
          >
            <div>
              <h3 style={styles.h3}>Weekly Plan</h3>
              <p style={{ ...styles.muted, marginTop: 4 }}>
                Generated from the uploaded course guide.
              </p>
            </div>

            <div style={styles.row}>
              <span style={styles.chip}>Weeks: {planStats.total}</span>
              <span style={styles.chip}>Filled: {planStats.withTopics}</span>
              <span style={styles.chip}>{planStats.percent}% Ready</span>
            </div>
          </div>

          {plans.length === 0 ? (
            <div
              style={{
                marginTop: 18,
                border: "1px dashed #cbd5e1",
                background: "#f8fafc",
                borderRadius: 16,
                padding: 24,
                textAlign: "center",
              }}
            >
              <div style={{ fontWeight: 900, color: "#111827" }}>
                No weekly plan yet
              </div>
              <p style={styles.muted}>
                Upload a course guide to generate Week 1–16 execution plan.
              </p>
            </div>
          ) : (
            <div
              style={{
                marginTop: 16,
                display: "grid",
                gap: 10,
                maxHeight: 720,
                overflow: "auto",
                paddingRight: 4,
              }}
            >
              {plans.map((p) => (
                <div key={p.id || p.week_number} style={styles.weekCard}>
                  <div style={{ display: "flex", gap: 12, alignItems: "start" }}>
                    <div style={styles.weekNo}>{p.week_number}</div>

                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div
                        style={{
                          display: "flex",
                          justifyContent: "space-between",
                          gap: 10,
                          flexWrap: "wrap",
                        }}
                      >
                        <div style={{ fontWeight: 900, color: "#111827" }}>
                          Week {p.week_number}
                        </div>

                        <span style={styles.chip}>
                          {String(p.planned_topics || "").trim()
                            ? "Planned"
                            : "Empty"}
                        </span>
                      </div>

                      <div
                        style={{
                          ...styles.muted,
                          marginTop: 8,
                          whiteSpace: "pre-wrap",
                          color: "#374151",
                        }}
                      >
                        {p.planned_topics || "No planned topics extracted for this week."}
                      </div>

                      {p.created_at && (
                        <div style={{ ...styles.muted, marginTop: 10, fontSize: 12 }}>
                          Created: {formatDate(p.created_at)}
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      <div style={styles.card}>
        <h3 style={styles.h3}>Viva Explanation</h3>
        <p style={styles.muted}>
          The Course Guide module is used by the assigned Course Lead to upload
          the official course guide. The system extracts the text and generates a
          structured Week 1–16 plan. Later, weekly teacher uploads are compared
          with this plan to detect whether course execution is on track, behind,
          or missing planned topics.
        </p>
      </div>
    </div>
  );
}