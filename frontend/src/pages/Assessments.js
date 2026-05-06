import React, { useEffect, useMemo, useState } from "react";
import api from "../api";
import { useNavigate, useLocation } from "react-router-dom";

function Chip({ children, tone = "gray" }) {
  const bg =
    tone === "blue" ? "rgba(13,110,253,0.12)" :
    tone === "green" ? "rgba(25,135,84,0.12)" :
    tone === "red" ? "rgba(220,53,69,0.12)" :
    "rgba(0,0,0,0.04)";

  const border =
    tone === "blue" ? "rgba(13,110,253,0.22)" :
    tone === "green" ? "rgba(25,135,84,0.22)" :
    tone === "red" ? "rgba(220,53,69,0.22)" :
    "rgba(0,0,0,0.08)";

  return (
    <span style={{
      display: "inline-flex",
      alignItems: "center",
      gap: 6,
      padding: "6px 10px",
      borderRadius: 999,
      background: bg,
      border: `1px solid ${border}`,
      fontSize: 12,
      whiteSpace: "nowrap"
    }}>
      {children}
    </span>
  );
}

function Card({ title, right, children, style }) {
  return (
    <div className="card" style={{ padding: 18, borderRadius: 14, ...style }}>
      <div style={{
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        gap: 12,
        flexWrap: "wrap",
        marginBottom: 10
      }}>
        <h2 style={{ margin: 0, fontSize: 20 }}>{title}</h2>
        {right}
      </div>
      {children}
    </div>
  );
}

export default function Assessments() {
  const [courses, setCourses] = useState([]);
  const [courseId, setCourseId] = useState("");
  const [items, setItems] = useState([]);
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);

  const [type, setType] = useState("quiz");
  const [title, setTitle] = useState("");
  const [maxMarks, setMaxMarks] = useState(10);
  const [weightage, setWeightage] = useState(10);

  const todayStr = new Date().toISOString().slice(0, 10);
  const [date, setDate] = useState(todayStr);

  const nav = useNavigate();
  const location = useLocation();

  const queryCourseId = useMemo(() => {
    const sp = new URLSearchParams(location.search);
    return sp.get("courseId") || "";
  }, [location.search]);

  useEffect(() => {
    (async () => {
      try {
        const res = await api.get("/courses");
        const list = res.data || [];
        setCourses(list);

        // ✅ if coming from CourseFolder => /assessments?courseId=...
        const preferred = queryCourseId && list.some(c => c.id === queryCourseId)
          ? queryCourseId
          : (list[0]?.id || "");

        setCourseId(preferred);
      } catch (e) {
        setErr(e?.response?.data?.detail || "Failed to load courses");
      }
    })();
  }, [queryCourseId]);

  useEffect(() => {
    if (!courseId) return;
    (async () => {
      setErr("");
      try {
        const res = await api.get(`/courses/${courseId}/assessments`);
        setItems(res.data || []);
      } catch (e) {
        setErr(e?.response?.data?.detail || "Failed to load assessments");
      }
    })();
  }, [courseId]);

  const stats = useMemo(() => {
    const byType = { quiz: 0, assignment: 0, mid: 0, final: 0 };
    (items || []).forEach((a) => {
      const t = (a.type || "").toLowerCase();
      if (byType[t] !== undefined) byType[t] += 1;
    });
    return byType;
  }, [items]);

  const create = async () => {
    setErr("");
    setBusy(true);
    try {
      const payload = {
        type,
        title,
        max_marks: Number(maxMarks),
        weightage: Number(weightage),
        date,
      };

      const res = await api.post(`/courses/${courseId}/assessments`, payload);
      const created = res.data;

      setTitle("");
      setMaxMarks(10);
      setWeightage(10);
      setDate(todayStr);

      setItems([created, ...items]);
    } catch (e) {
      const detail = e?.response?.data?.detail;
      if (Array.isArray(detail)) {
        setErr(detail.map((d) => d?.msg || "Validation error").join(", "));
      } else {
        setErr(detail || "Create failed");
      }
    } finally {
      setBusy(false);
    }
  };

  const canCreate =
    !!courseId &&
    !!title &&
    Number.isFinite(Number(maxMarks)) &&
    Number.isFinite(Number(weightage)) &&
    !!date;

  return (
    <div className="page" style={{ maxWidth: 1150, margin: "0 auto" }}>
      <Card
        title="Assessments"
        right={
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
            <Chip tone="blue">Total: {items.length}</Chip>
            <Chip>Quizzes: {stats.quiz}</Chip>
            <Chip>Assignments: {stats.assignment}</Chip>
            <Chip>Mid: {stats.mid}</Chip>
            <Chip>Final: {stats.final}</Chip>
          </div>
        }
      >
        {err && <div className="alert alert-danger" style={{ marginTop: 10 }}>{err}</div>}

        <div style={{ display: "grid", gridTemplateColumns: "1fr auto", gap: 12, alignItems: "end" }}>
          <div className="field">
            <label>Course</label>
            <select className="select" value={courseId} onChange={(e) => setCourseId(e.target.value)}>
              {courses.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.course_code} — {c.course_name}
                </option>
              ))}
            </select>
          </div>

          <button
            className="btn"
            onClick={async () => {
              if (!courseId) return;
              setErr("");
              try {
                const res = await api.get(`/courses/${courseId}/assessments`);
                setItems(res.data || []);
              } catch (e) {
                setErr(e?.response?.data?.detail || "Failed to refresh assessments");
              }
            }}
            disabled={!courseId || busy}
            style={{ height: 40 }}
          >
            Refresh
          </button>
        </div>

        <div style={{
          marginTop: 14,
          padding: 14,
          borderRadius: 14,
          border: "1px solid rgba(0,0,0,0.06)",
          background: "rgba(255,255,255,0.65)"
        }}>
          <div style={{ display: "flex", justifyContent: "space-between", gap: 10, flexWrap: "wrap", alignItems: "center" }}>
            <div>
              <div style={{ fontWeight: 800 }}>Create new assessment</div>
              <div className="muted" style={{ fontSize: 12, marginTop: 4 }}>
                Use consistent titles like <b>Q_1</b>, <b>A_1</b> for ZIP matching.
              </div>
            </div>
            <Chip tone={canCreate ? "green" : "red"}>{canCreate ? "Ready" : "Missing fields"}</Chip>
          </div>

          <div style={{
            marginTop: 12,
            display: "grid",
            gridTemplateColumns: "repeat(12, 1fr)",
            gap: 12
          }}>
            <div className="field" style={{ gridColumn: "span 3" }}>
              <label>Type</label>
              <select className="select" value={type} onChange={(e) => setType(e.target.value)}>
                <option value="quiz">Quiz</option>
                <option value="assignment">Assignment</option>
                <option value="mid">Mid</option>
                <option value="final">Final</option>
              </select>
            </div>

            <div className="field" style={{ gridColumn: "span 5" }}>
              <label>Title</label>
              <input
                className="input"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="e.g., Q_1 — Week 2 Quiz"
              />
            </div>

            <div className="field" style={{ gridColumn: "span 2" }}>
              <label>Max Marks</label>
              <input className="input" type="number" min="0" value={maxMarks} onChange={(e) => setMaxMarks(e.target.value)} />
            </div>

            <div className="field" style={{ gridColumn: "span 2" }}>
              <label>Weightage</label>
              <input className="input" type="number" min="0" value={weightage} onChange={(e) => setWeightage(e.target.value)} />
            </div>

            <div className="field" style={{ gridColumn: "span 3" }}>
              <label>Date</label>
              <input className="input" type="date" value={date} onChange={(e) => setDate(e.target.value)} />
            </div>

            <div style={{ gridColumn: "span 9", display: "flex", gap: 10, alignItems: "end", flexWrap: "wrap" }}>
              <button className="btn-primary" onClick={create} disabled={busy || !canCreate} style={{ height: 40 }}>
                {busy ? "Creating..." : "Create"}
              </button>
              <button
                className="btn"
                onClick={() => {
                  setType("quiz");
                  setTitle("");
                  setMaxMarks(10);
                  setWeightage(10);
                  setDate(todayStr);
                }}
                disabled={busy}
                style={{ height: 40 }}
              >
                Reset
              </button>
            </div>
          </div>
        </div>
      </Card>

      <Card title="Assessment List" style={{ marginTop: 16 }} right={<span className="muted" style={{ fontSize: 12 }}>Open to upload questions & grade</span>}>
        <div style={{ overflowX: "auto" }}>
          <table className="table" style={{ marginTop: 0 }}>
            <thead>
              <tr>
                <th style={{ width: 120 }}>Type</th>
                <th>Title</th>
                <th style={{ width: 90 }}>Marks</th>
                <th style={{ width: 110 }}>Weightage</th>
                <th style={{ width: 120 }}>Date</th>
                <th style={{ width: 90 }}></th>
              </tr>
            </thead>
            <tbody>
              {items.map((a) => (
                <tr key={a.id}>
                  <td><Chip tone="blue">{a.type}</Chip></td>
                  <td style={{ fontWeight: 700 }}>{a.title}</td>
                  <td>{a.max_marks}</td>
                  <td>{a.weightage ?? "-"}</td>
                  <td>{a.date ? String(a.date).slice(0, 10) : "-"}</td>
                  <td>
                    <button className="btn" onClick={() => nav(`/assessments/${a.id}`)}>
                      Open
                    </button>
                  </td>
                </tr>
              ))}

              {!items.length && (
                <tr>
                  <td colSpan={6} className="muted" style={{ padding: 16 }}>
                    No assessments yet.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}
