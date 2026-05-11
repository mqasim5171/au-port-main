import React, { useEffect, useMemo, useState } from "react";
import api from "../api";

export default function CourseGuideUpload({ user }) {
  const isCourseLead = useMemo(() => {
    const r = (user?.role || "").toLowerCase();
    return r.includes("course_lead") || r.includes("admin");
  }, [user]);

  const [courses, setCourses] = useState([]);
  const [courseId, setCourseId] = useState("");
  const [file, setFile] = useState(null);
  const [plans, setPlans] = useState([]);
  const [busy, setBusy] = useState(false);

  const loadCourses = async () => {
    const res = await api.get("/course-lead/my-courses");
    const list = res.data || [];
    setCourses(list);
    if (!courseId && list.length) setCourseId(list[0].id);
  };

  const loadPlans = async (id) => {
    if (!id) return;
    const res = await api.get(`/course-lead/courses/${id}/weekly-plans`);
    setPlans(res.data || []);
  };

  useEffect(() => {
    if (!isCourseLead) return;
    loadCourses().catch(console.error);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isCourseLead]);

  useEffect(() => {
    if (!courseId) return;
    loadPlans(courseId).catch(() => setPlans([]));
  }, [courseId]);

  if (!isCourseLead) {
    return (
      <div className="card">
        <h2>Course Guide Upload</h2>
        <p style={{ opacity: 0.8 }}>Only Course Lead can access this.</p>
      </div>
    );
  }

  const upload = async () => {
    if (!courseId) return alert("Select course");
    if (!file) return alert("Choose file");

    setBusy(true);
    try {
      const fd = new FormData();
      fd.append("file", file);

      await api.post(`/course-lead/courses/${courseId}/course-guide/upload`, fd, {
        headers: { "Content-Type": "multipart/form-data" },
      });

      alert("Uploaded + weekly plans generated");
      await loadPlans(courseId);
    } catch (e) {
      console.error(e);
      alert(e?.response?.data?.detail || "Upload failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div style={{ display: "grid", gap: 16 }}>
      <div className="card">
        <h2>Course Guide Upload</h2>
        <p style={{ opacity: 0.8 }}>
          Upload master course guide (PDF/DOCX). System generates Week 1–16 plans.
        </p>
      </div>

      <div className="card" style={{ display: "grid", gap: 10 }}>
        <select value={courseId} onChange={(e) => setCourseId(e.target.value)}>
          {courses.map((c) => (
            <option key={c.id} value={c.id}>
              {c.course_code} — {c.course_name}
            </option>
          ))}
        </select>

        <input type="file" accept=".pdf,.docx" onChange={(e) => setFile(e.target.files?.[0] || null)} />

        <button className="btn-primary" onClick={upload} disabled={busy}>
          {busy ? "Uploading..." : "Upload & Generate Weekly Plan"}
        </button>
      </div>

      <div className="card">
        <h3>Weekly Plan (Week 1–16)</h3>
        {plans.length === 0 ? (
          <p style={{ opacity: 0.7 }}>No weekly plans yet. Upload a course guide first.</p>
        ) : (
          <div style={{ display: "grid", gap: 10 }}>
            {plans.map((p) => (
              <div key={p.id} className="card" style={{ padding: 12 }}>
                <strong>Week {p.week_number}</strong>
                <div style={{ opacity: 0.8, marginTop: 6, whiteSpace: "pre-wrap" }}>
                  {p.planned_topics || ""}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
