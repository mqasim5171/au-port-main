import React, { useEffect, useMemo, useState } from "react";
import api from "../api";

const FOLDERS = [
  { value: "lecture_notes", label: "Lecture Notes" },
  { value: "slides", label: "Slides" },
  { value: "assignments", label: "Assignments" },
  { value: "quizzes", label: "Quizzes" },
  { value: "midterm", label: "Midterm" },
  { value: "finalterm", label: "Final Term" },
  { value: "other", label: "Other Material" },
];

const styles = {
  page: {
    maxWidth: 1180,
    margin: "0 auto",
    display: "grid",
    gap: 16,
  },
  header: {
    background: "#fff",
    border: "1px solid #e5e7eb",
    borderRadius: 18,
    padding: 20,
    boxShadow: "0 10px 25px rgba(15,23,42,0.05)",
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
  card: {
    background: "#fff",
    border: "1px solid #e5e7eb",
    borderRadius: 18,
    padding: 18,
    boxShadow: "0 10px 25px rgba(15,23,42,0.05)",
  },
  grid: {
    display: "grid",
    gridTemplateColumns: "320px 1fr",
    gap: 16,
    alignItems: "start",
  },
  h3: {
    margin: 0,
    color: "#111827",
    fontSize: 18,
    fontWeight: 900,
  },
  muted: {
    color: "#6b7280",
    fontSize: 13,
    lineHeight: 1.5,
  },
  label: {
    display: "block",
    fontSize: 13,
    fontWeight: 800,
    color: "#374151",
    marginBottom: 7,
  },
  input: {
    width: "100%",
    border: "1px solid #d1d5db",
    borderRadius: 12,
    padding: "11px 12px",
    outline: "none",
    boxSizing: "border-box",
  },
  textarea: {
    width: "100%",
    border: "1px solid #d1d5db",
    borderRadius: 12,
    padding: "11px 12px",
    outline: "none",
    boxSizing: "border-box",
    minHeight: 90,
    resize: "vertical",
  },
  select: {
    width: "100%",
    border: "1px solid #d1d5db",
    borderRadius: 12,
    padding: "11px 12px",
    outline: "none",
    background: "#fff",
    boxSizing: "border-box",
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
    padding: "10px 14px",
    fontWeight: 800,
    cursor: "pointer",
  },
  danger: {
    border: "1px solid #dc2626",
    background: "#dc2626",
    color: "#fff",
    borderRadius: 12,
    padding: "10px 14px",
    fontWeight: 800,
    cursor: "pointer",
  },
  chip: {
    display: "inline-flex",
    alignItems: "center",
    borderRadius: 999,
    padding: "5px 10px",
    fontSize: 12,
    fontWeight: 800,
    background: "#eff6ff",
    color: "#1d4ed8",
    border: "1px solid #bfdbfe",
    whiteSpace: "nowrap",
  },
  weekButton: {
    width: "100%",
    border: "1px solid #e5e7eb",
    borderRadius: 14,
    padding: 12,
    background: "#fff",
    cursor: "pointer",
    textAlign: "left",
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    gap: 10,
  },
  materialCard: {
    border: "1px solid #e5e7eb",
    borderRadius: 16,
    padding: 16,
    background: "#fff",
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

function fmtBytes(n) {
  const v = Number(n || 0);
  if (v < 1024) return `${v} B`;
  if (v < 1024 * 1024) return `${(v / 1024).toFixed(1)} KB`;
  return `${(v / (1024 * 1024)).toFixed(1)} MB`;
}

function formatDate(value) {
  if (!value) return "-";
  try {
    return new Date(value).toLocaleString();
  } catch {
    return String(value);
  }
}

function fileUrl(file) {
  if (!file?.url) return "#";
  const base = api.defaults.baseURL || "";
  if (file.url.startsWith("http")) return file.url;
  return `${base}${file.url}`;
}

function folderLabel(folder) {
  return FOLDERS.find((x) => x.value === folder)?.label || "Other Material";
}

function weekPrefix(weekNo) {
  return `[W${String(weekNo).padStart(2, "0")}]`;
}

function getMaterialWeek(material) {
  const title = material?.title || "";
  const match = title.match(/^\[W(\d{1,2})\]/i);
  if (!match) return null;
  const n = Number(match[1]);
  return Number.isFinite(n) ? n : null;
}

function cleanMaterialTitle(title) {
  return String(title || "").replace(/^\[W\d{1,2}\]\s*/i, "");
}

export default function WeeklyUpload() {
  const [courses, setCourses] = useState([]);
  const [courseId, setCourseId] = useState("");

  const [weekNo, setWeekNo] = useState(1);
  const [weeklyPlans, setWeeklyPlans] = useState([]);
  const [materials, setMaterials] = useState([]);

  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [folder, setFolder] = useState("lecture_notes");
  const [files, setFiles] = useState([]);

  const [loading, setLoading] = useState(false);
  const [creating, setCreating] = useState(false);
  const [err, setErr] = useState("");
  const [message, setMessage] = useState("");

  const selectedCourse = useMemo(
    () => courses.find((c) => c.id === courseId),
    [courses, courseId]
  );

  const selectedPlan = useMemo(() => {
    return weeklyPlans.find((p) => Number(p.week_number) === Number(weekNo));
  }, [weeklyPlans, weekNo]);

  const weekMaterialCounts = useMemo(() => {
    const counts = {};
    for (let i = 1; i <= 16; i += 1) counts[i] = 0;

    materials.forEach((m) => {
      const w = getMaterialWeek(m);
      if (w && counts[w] !== undefined) counts[w] += 1;
    });

    return counts;
  }, [materials]);

  const visibleMaterials = useMemo(() => {
    return materials.filter((m) => getMaterialWeek(m) === Number(weekNo));
  }, [materials, weekNo]);

  const loadCourses = async () => {
    const res = await api.get("/courses");
    const list = res.data || [];

    setCourses(list);

    if (!courseId && list.length) {
      setCourseId(list[0].id);
    }
  };

  const loadMaterials = async (id = courseId) => {
    if (!id) return;

    const res = await api.get(`/courses/${id}/materials`);
    setMaterials(res.data || []);
  };

  const loadWeeklyPlans = async (id = courseId) => {
    if (!id) return;

    try {
      const res = await api.get(`/courses/${id}/weekly-plans`);
      setWeeklyPlans(res.data || []);
    } catch {
      setWeeklyPlans([]);
    }
  };

  const refreshAll = async (id = courseId) => {
    if (!id) return;

    setLoading(true);
    setErr("");

    try {
      await Promise.all([loadMaterials(id), loadWeeklyPlans(id)]);
    } catch (e) {
      setErr(e?.response?.data?.detail || "Failed to load weekly upload data");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadCourses().catch((e) =>
      setErr(e?.response?.data?.detail || "Failed to load courses")
    );
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!courseId) return;
    refreshAll(courseId);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [courseId]);

  const resetForm = () => {
    setTitle("");
    setDescription("");
    setFolder("lecture_notes");
    setFiles([]);
  };

  const createMaterial = async () => {
    setErr("");
    setMessage("");

    if (!courseId) {
      setErr("Select a course first.");
      return;
    }

    if (!title.trim()) {
      setErr("Material title is required.");
      return;
    }

    if (!files.length) {
      setErr("Please attach at least one file.");
      return;
    }

    setCreating(true);

    try {
      const fd = new FormData();

      fd.append("title", `${weekPrefix(weekNo)} ${title.trim()}`);
      fd.append("description", description.trim());
      fd.append("folder_hint", folder);

      files.forEach((f) => {
        fd.append("files", f);
      });

      await api.post(`/courses/${courseId}/materials`, fd, {
        headers: { "Content-Type": "multipart/form-data" },
      });

      setMessage(`Material added to Week ${weekNo}.`);
      resetForm();
      await refreshAll(courseId);
    } catch (e) {
      setErr(e?.response?.data?.detail || "Failed to create material");
    } finally {
      setCreating(false);
    }
  };

  const deleteMaterial = async (materialId) => {
    const ok = window.confirm("Delete this material and all attached files?");
    if (!ok) return;

    setErr("");
    setMessage("");

    try {
      await api.delete(`/courses/${courseId}/materials/${materialId}`);
      setMessage("Material deleted successfully.");
      await refreshAll(courseId);
    } catch (e) {
      setErr(e?.response?.data?.detail || "Failed to delete material");
    }
  };

  const deleteFile = async (materialId, fileId) => {
    const ok = window.confirm("Delete this file?");
    if (!ok) return;

    setErr("");
    setMessage("");

    try {
      await api.delete(
        `/courses/${courseId}/materials/${materialId}/files/${fileId}`
      );
      setMessage("File deleted successfully.");
      await refreshAll(courseId);
    } catch (e) {
      setErr(e?.response?.data?.detail || "Failed to delete file");
    }
  };

  return (
    <div style={styles.page}>
      <div style={styles.header}>
        <h2 style={styles.title}>Weekly Upload</h2>
        <p style={styles.subtitle}>
          Upload and manage course material according to the weekly course plan.
          Select a week, review the planned topics, and attach the delivered
          teaching material for that week.
        </p>
      </div>

      {err && <div style={styles.alert}>{err}</div>}
      {message && <div style={styles.success}>{message}</div>}

      <div style={styles.grid}>
        <div style={{ display: "grid", gap: 16 }}>
          <div style={styles.card}>
            <h3 style={styles.h3}>Course</h3>

            <div style={{ marginTop: 14 }}>
              <label style={styles.label}>Select Course</label>
              <select
                style={styles.select}
                value={courseId}
                onChange={(e) => {
                  setCourseId(e.target.value);
                  setMessage("");
                  setErr("");
                  resetForm();
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
            <h3 style={styles.h3}>Weeks</h3>
            <p style={styles.muted}>Select the week for material upload.</p>

            <div
              style={{
                display: "grid",
                gap: 8,
                marginTop: 14,
                maxHeight: 560,
                overflow: "auto",
                paddingRight: 4,
              }}
            >
              {Array.from({ length: 16 }, (_, i) => i + 1).map((w) => {
                const isActive = Number(weekNo) === Number(w);
                const count = weekMaterialCounts[w] || 0;
                const hasPlan = weeklyPlans.some(
                  (p) => Number(p.week_number) === Number(w)
                );

                return (
                  <button
                    key={w}
                    type="button"
                    onClick={() => {
                      setWeekNo(w);
                      setMessage("");
                      setErr("");
                      resetForm();
                    }}
                    style={{
                      ...styles.weekButton,
                      border: isActive
                        ? "2px solid #2563eb"
                        : "1px solid #e5e7eb",
                      background: isActive ? "#eff6ff" : "#fff",
                    }}
                  >
                    <div>
                      <div style={{ fontWeight: 900, color: "#111827" }}>
                        Week {w}
                      </div>
                      <div style={styles.muted}>
                        {hasPlan ? "Plan available" : "No guide plan"}
                      </div>
                    </div>

                    <span style={styles.chip}>{count}</span>
                  </button>
                );
              })}
            </div>
          </div>
        </div>

        <div style={{ display: "grid", gap: 16 }}>
          <div style={styles.card}>
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                gap: 12,
                alignItems: "start",
                flexWrap: "wrap",
              }}
            >
              <div>
                <h3 style={styles.h3}>Week {weekNo} Planned Topics</h3>
                <p style={{ ...styles.muted, marginTop: 4 }}>
                  These topics come from the uploaded course guide.
                </p>
              </div>

              <span style={styles.chip}>
                Materials: {visibleMaterials.length}
              </span>
            </div>

            <div
              style={{
                marginTop: 14,
                padding: 14,
                borderRadius: 14,
                background: "#f9fafb",
                border: "1px solid #e5e7eb",
                minHeight: 80,
                whiteSpace: "pre-wrap",
                color: "#374151",
                lineHeight: 1.6,
              }}
            >
              {selectedPlan?.planned_topics ||
                "No weekly plan found for this week. Upload the course guide first to generate Week 1–16 plan."}
            </div>
          </div>

          <div style={styles.card}>
            <h3 style={styles.h3}>Add Material for Week {weekNo}</h3>

            <div
              style={{
                marginTop: 14,
                display: "grid",
                gridTemplateColumns: "1fr 220px",
                gap: 12,
              }}
            >
              <div>
                <label style={styles.label}>Title</label>
                <input
                  style={styles.input}
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  placeholder="e.g. Lecture slides, lab manual, reading material"
                />
              </div>

              <div>
                <label style={styles.label}>Material Type</label>
                <select
                  style={styles.select}
                  value={folder}
                  onChange={(e) => setFolder(e.target.value)}
                >
                  {FOLDERS.map((f) => (
                    <option key={f.value} value={f.value}>
                      {f.label}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <div style={{ marginTop: 12 }}>
              <label style={styles.label}>Description</label>
              <textarea
                style={styles.textarea}
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Add a short note about this material..."
              />
            </div>

            <div
              style={{
                marginTop: 12,
                padding: 14,
                borderRadius: 16,
                background: "#f8fafc",
                border: "1px dashed #cbd5e1",
              }}
            >
              <label style={styles.label}>Attach Files</label>

              <input
                type="file"
                multiple
                onChange={(e) => setFiles(Array.from(e.target.files || []))}
              />

              {files.length > 0 && (
                <div style={{ marginTop: 12, display: "grid", gap: 6 }}>
                  {files.map((f, index) => (
                    <div
                      key={`${f.name}-${index}`}
                      style={{
                        display: "flex",
                        justifyContent: "space-between",
                        gap: 10,
                        padding: 8,
                        borderRadius: 10,
                        background: "#fff",
                        border: "1px solid #e5e7eb",
                      }}
                    >
                      <span style={{ fontWeight: 800, color: "#111827" }}>
                        {f.name}
                      </span>
                      <span style={styles.muted}>{fmtBytes(f.size)}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>

            <div
              style={{
                display: "flex",
                gap: 10,
                flexWrap: "wrap",
                marginTop: 14,
              }}
            >
              <button
                type="button"
                style={{
                  ...styles.btnPrimary,
                  opacity: creating || !courseId ? 0.65 : 1,
                }}
                onClick={createMaterial}
                disabled={creating || !courseId}
              >
                {creating ? "Saving..." : "Save Material"}
              </button>

              <button type="button" style={styles.btn} onClick={resetForm}>
                Clear
              </button>

              <button
                type="button"
                style={styles.btn}
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
                <h3 style={styles.h3}>Week {weekNo} Uploaded Material</h3>
                <p style={{ ...styles.muted, marginTop: 4 }}>
                  Files uploaded for the selected week.
                </p>
              </div>

              <span style={styles.chip}>Total: {visibleMaterials.length}</span>
            </div>

            {loading ? (
              <div
                style={{
                  marginTop: 16,
                  padding: 20,
                  borderRadius: 16,
                  background: "#f8fafc",
                  border: "1px solid #e5e7eb",
                  color: "#6b7280",
                  textAlign: "center",
                }}
              >
                Loading materials...
              </div>
            ) : visibleMaterials.length === 0 ? (
              <div
                style={{
                  marginTop: 16,
                  padding: 24,
                  borderRadius: 16,
                  background: "#f8fafc",
                  border: "1px dashed #cbd5e1",
                  textAlign: "center",
                }}
              >
                <div style={{ fontWeight: 900, color: "#111827" }}>
                  No material uploaded for Week {weekNo}
                </div>
                <p style={styles.muted}>
                  Add lecture material, slides, notes, assignments, or quizzes
                  using the form above.
                </p>
              </div>
            ) : (
              <div style={{ marginTop: 16, display: "grid", gap: 12 }}>
                {visibleMaterials.map((m) => (
                  <div key={m.id} style={styles.materialCard}>
                    <div
                      style={{
                        display: "flex",
                        justifyContent: "space-between",
                        gap: 12,
                        alignItems: "start",
                        flexWrap: "wrap",
                      }}
                    >
                      <div style={{ minWidth: 0 }}>
                        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                          <span style={styles.chip}>
                            {folderLabel(m.folder_type || m.folder)}
                          </span>
                          <span style={styles.chip}>
                            Files: {(m.files || []).length}
                          </span>
                        </div>

                        <h3
                          style={{
                            margin: "10px 0 0",
                            color: "#111827",
                            fontSize: 18,
                            fontWeight: 900,
                          }}
                        >
                          {cleanMaterialTitle(m.title)}
                        </h3>

                        {m.description && (
                          <p style={{ ...styles.muted, marginTop: 8 }}>
                            {m.description}
                          </p>
                        )}

                        <div style={{ ...styles.muted, marginTop: 8 }}>
                          Uploaded: {formatDate(m.created_at)}
                        </div>
                      </div>

                      <button
                        type="button"
                        style={styles.danger}
                        onClick={() => deleteMaterial(m.id)}
                      >
                        Delete
                      </button>
                    </div>

                    <div style={{ marginTop: 14, display: "grid", gap: 8 }}>
                      {(m.files || []).map((f) => (
                        <div
                          key={f.id}
                          style={{
                            border: "1px solid #e5e7eb",
                            borderRadius: 12,
                            padding: 10,
                            background: "#f9fafb",
                            display: "flex",
                            justifyContent: "space-between",
                            gap: 12,
                            alignItems: "center",
                            flexWrap: "wrap",
                          }}
                        >
                          <div style={{ minWidth: 0 }}>
                            <div
                              style={{
                                fontWeight: 900,
                                color: "#111827",
                                overflow: "hidden",
                                textOverflow: "ellipsis",
                                whiteSpace: "nowrap",
                              }}
                            >
                              {f.filename || f.display_name}
                            </div>

                            <div style={styles.muted}>
                              {f.content_type || "file"} ·{" "}
                              {fmtBytes(f.size_bytes)} · Uploaded:{" "}
                              {formatDate(f.uploaded_at)}
                            </div>
                          </div>

                          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                            <a
                              href={fileUrl(f)}
                              target="_blank"
                              rel="noreferrer"
                              style={{
                                ...styles.btn,
                                textDecoration: "none",
                                display: "inline-flex",
                              }}
                            >
                              Open
                            </a>

                            <button
                              type="button"
                              style={styles.btn}
                              onClick={() => deleteFile(m.id, f.id)}
                            >
                              Delete File
                            </button>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}