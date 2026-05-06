// StudentFeedback.jsx  ✅ FULL MODIFIED FILE (admin-only upload + better token/role detection + debug-ready)

import React, { useEffect, useMemo, useState } from "react";
import axios from "axios";
import {
  PieChart,
  Pie,
  Cell,
  Tooltip,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Legend,
  ResponsiveContainer,
} from "recharts";

const API = "http://127.0.0.1:8000";

// ✅ exact colors you asked
const COLORS = {
  positive: "#22c55e",
  neutral: "#f59e0b",
  negative: "#ef4444",
};

/* -------------------- AUTH HELPERS -------------------- */

function getToken() {
  // ✅ robust: checks common keys in both localStorage + sessionStorage
  const t1 = localStorage.getItem("access_token");
  const t2 = localStorage.getItem("token");
  const t3 = localStorage.getItem("jwt");
  const t4 = sessionStorage.getItem("access_token");
  const t5 = sessionStorage.getItem("token");
  return t1 || t2 || t3 || t4 || t5 || "";
}

function authHeaders() {
  const t = getToken();
  return t ? { Authorization: `Bearer ${t}` } : {};
}

/* -------------------- MODAL -------------------- */

function Modal({ open, title, onClose, children }) {
  if (!open) return null;
  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(0,0,0,0.45)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 9999,
      }}
    >
      <div
        style={{
          width: "min(980px, 92vw)",
          maxHeight: "82vh",
          overflow: "auto",
          background: "#fff",
          borderRadius: 12,
          padding: 16,
        }}
      >
        <div style={{ display: "flex", justifyContent: "space-between", gap: 12 }}>
          <h3 style={{ margin: 0 }}>{title}</h3>
          <button onClick={onClose} className="bg-gray-200 px-3 py-1 rounded">
            Close
          </button>
        </div>
        <div style={{ marginTop: 12 }}>{children}</div>
      </div>
    </div>
  );
}

/* -------------------- TOPIC EXTRACTION -------------------- */

const STOP = new Set([
  "the",
  "and",
  "was",
  "were",
  "with",
  "that",
  "this",
  "have",
  "has",
  "had",
  "too",
  "very",
  "course",
  "teacher",
  "instructor",
  "sir",
  "maam",
  "student",
  "students",
  "class",
  "classes",
  "good",
  "bad",
  "nice",
  "okay",
  "ok",
  "great",
]);

function extractTopics(comments, topN = 6) {
  const freq = {};
  comments.forEach((t) => {
    String(t || "")
      .toLowerCase()
      .replace(/[^a-z0-9\s]/g, " ")
      .split(/\s+/)
      .filter((w) => w.length >= 4 && !STOP.has(w))
      .forEach((w) => (freq[w] = (freq[w] || 0) + 1));
  });

  return Object.entries(freq)
    .sort((a, b) => b[1] - a[1])
    .slice(0, topN)
    .map(([w]) => w);
}

/* -------------------- MAIN COMPONENT -------------------- */

export default function StudentFeedback() {
  const [me, setMe] = useState(null);

  const [summary, setSummary] = useState(null);

  // filters
  const [batches, setBatches] = useState([]);
  const [departments, setDepartments] = useState([]);
  const [courses, setCourses] = useState([]);

  const [batch, setBatch] = useState("");
  const [department, setDepartment] = useState("");
  const [course, setCourse] = useState("");

  // topics + conclusion
  const [mainTopics, setMainTopics] = useState([]);
  const [mainConclusion, setMainConclusion] = useState("");

  // upload
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);

  // modal drilldown
  const [modalOpen, setModalOpen] = useState(false);
  const [modalTitle, setModalTitle] = useState("");
  const [modalData, setModalData] = useState({ total: 0, items: [] });
  const [modalLoading, setModalLoading] = useState(false);

  // ✅ Robust Admin Detection (handles many backend response shapes)
  const isAdmin = useMemo(() => {
    const role =
      (me?.role ||
        me?.user_role ||
        me?.role_name ||
        me?.userType ||
        me?.user?.role ||
        me?.user?.user_role ||
        "")
        .toString()
        .toLowerCase();

    return (
      me?.is_admin === true ||
      me?.is_superuser === true ||
      ["admin", "qec", "superadmin"].includes(role)
    );
  }, [me]);

  /* -------------------- API CALLS -------------------- */

  const fetchMe = async () => {
    try {
      const res = await axios.get(`${API}/auth/me`, { headers: authHeaders() });
      console.log("ME:", res.data); // ✅ check role field in console
      setMe(res.data);
    } catch (e) {
      console.log("ME ERROR:", e?.response?.status, e?.response?.data);
      setMe(null);
    }
  };

  const fetchFilters = async () => {
    try {
      const [bRes, dRes] = await Promise.all([
        axios.get(`${API}/feedback/batches`, { headers: authHeaders() }),
        axios.get(`${API}/feedback/departments`, { headers: authHeaders() }),
      ]);
      setBatches(bRes.data || []);
      setDepartments(dRes.data || []);
    } catch (err) {
      console.error("Failed to fetch filters", err);
    }
  };

  const fetchCourses = async () => {
    try {
      const params = {};
      if (batch) params.batch = Number(batch);
      if (department) params.department = department;

      const res = await axios.get(`${API}/feedback/courses`, {
        params,
        headers: authHeaders(),
      });

      const list = res.data || [];
      setCourses(list);

      // reset invalid selected course
      if (course && !list.includes(course)) setCourse("");
    } catch (err) {
      console.error("Failed to fetch courses", err);
    }
  };

  const fetchSummary = async () => {
    try {
      const params = {};
      if (batch) params.batch = Number(batch);
      if (department) params.department = department;
      if (course) params.course = course;

      const res = await axios.get(`${API}/feedback/summary`, {
        params,
        headers: authHeaders(),
      });
      setSummary(res.data);
    } catch (e) {
      console.error("Failed to fetch summary", e);
    }
  };

  // ✅ topics + conclusion (computed from detail records)
  const fetchTopics = async () => {
    try {
      const params = { limit: 500, offset: 0 };
      if (batch) params.batch = Number(batch);
      if (department) params.department = department;
      if (course) params.course = course;

      const res = await axios.get(`${API}/feedback/details-v2`, {
        params,
        headers: authHeaders(),
      });

      const items = res.data?.items || [];

      const pos = items.filter((x) => x.sentiment === "positive").length;
      const neu = items.filter((x) => x.sentiment === "neutral").length;
      const neg = items.filter((x) => x.sentiment === "negative").length;

      if (pos >= neg) {
        setMainConclusion(`Overall Positive Reviews — ${pos} positive vs ${neg} negative`);
      } else {
        setMainConclusion(`Overall Negative Reviews — ${neg} negative vs ${pos} positive`);
      }

      // extract topics from negative comments
      const negComments = items
        .filter((x) => x.sentiment === "negative")
        .map((x) => x.comments);

      const topics = extractTopics(negComments, 6);
      setMainTopics(topics);
    } catch (e) {
      console.error("Failed to fetch topics", e);
      setMainTopics([]);
      setMainConclusion("");
    }
  };

  /* -------------------- EFFECTS -------------------- */

  useEffect(() => {
    fetchMe();
    fetchFilters();
    // eslint-disable-next-line
  }, []);

  useEffect(() => {
    fetchCourses();
    // eslint-disable-next-line
  }, [batch, department]);

  useEffect(() => {
    fetchSummary();
    fetchTopics();
    // eslint-disable-next-line
  }, [batch, department, course]);

  /* -------------------- UPLOAD (ADMIN ONLY) -------------------- */

  const handleFileUpload = async () => {
    if (!file) return alert("Please select a CSV file");
    setUploading(true);
    try {
      const form = new FormData();
      form.append("file", file);

      await axios.post(`${API}/feedback/upload-csv`, form, {
        headers: { ...authHeaders(), "Content-Type": "multipart/form-data" },
      });

      setFile(null);
      await fetchFilters();
      await fetchCourses();
      await fetchSummary();
      await fetchTopics();

      alert("✅ CSV uploaded and analyzed!");
    } catch (e) {
      console.error(e);
      alert("Upload failed. Check backend logs.");
    } finally {
      setUploading(false);
    }
  };

  /* -------------------- CHART DATA -------------------- */

  const sentimentData = useMemo(() => {
    if (!summary?.sentiment) return [];
    return [
      { name: "positive", value: summary.sentiment.positive || 0 },
      { name: "neutral", value: summary.sentiment.neutral || 0 },
      { name: "negative", value: summary.sentiment.negative || 0 },
    ];
  }, [summary]);

  const courseData = useMemo(() => {
    if (!summary?.courses) return [];
    return Object.entries(summary.courses).map(([k, v]) => ({
      course: k,
      positive: v.pos || 0,
      neutral: v.neu || 0,
      negative: v.neg || 0,
    }));
  }, [summary]);

  /* -------------------- MODAL DETAILS -------------------- */

  const openDetails = async ({ title, extraParams }) => {
    setModalOpen(true);
    setModalTitle(title);
    setModalLoading(true);
    try {
      const params = { limit: 120, offset: 0, ...extraParams };
      if (batch) params.batch = Number(batch);
      if (department) params.department = department;
      if (course) params.course = course;

      const res = await axios.get(`${API}/feedback/details-v2`, {
        params,
        headers: authHeaders(),
      });
      setModalData(res.data);
    } catch (e) {
      console.error(e);
      alert("Failed to load details.");
    } finally {
      setModalLoading(false);
    }
  };

  if (!summary) return <p className="p-6">Loading feedback summary...</p>;

  /* -------------------- UI -------------------- */

  return (
    <div className="p-6">
      {/* Header */}
      <div className="flex flex-wrap items-end gap-4 mb-5">
        <div className="flex-1">
          <h2 className="text-2xl font-bold">Student Feedback Analyzer</h2>
          <div className="text-sm opacity-80">
            Total records: <b>{summary.total}</b>
          </div>
        </div>

        {/* Filters */}
        <div>
          <label className="block text-sm mb-1">Batch</label>
          <select className="border rounded px-3 py-2" value={batch} onChange={(e) => setBatch(e.target.value)}>
            <option value="">All</option>
            {batches.map((b) => (
              <option key={b} value={String(b)}>
                {b}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label className="block text-sm mb-1">Department</label>
          <select className="border rounded px-3 py-2" value={department} onChange={(e) => setDepartment(e.target.value)}>
            <option value="">All</option>
            {departments.map((d) => (
              <option key={d} value={d}>
                {d}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label className="block text-sm mb-1">Course</label>
          <select
            className="border rounded px-3 py-2 min-w-[220px]"
            value={course}
            onChange={(e) => setCourse(e.target.value)}
            disabled={courses.length === 0}
          >
            <option value="">All</option>
            {courses.map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* ✅ Upload Section (ADMIN ONLY) */}
      {isAdmin ? (
        <div className="mb-6 flex flex-wrap items-center gap-3">
          <input
            type="file"
            accept=".csv"
            onChange={(e) => setFile(e.target.files?.[0] || null)}
            className="border rounded px-3 py-2"
          />
          <button
            onClick={handleFileUpload}
            disabled={uploading || !file}
            className="bg-blue-600 text-white px-4 py-2 rounded disabled:opacity-60"
          >
            {uploading ? "Analyzing..." : "Upload & Analyze"}
          </button>

          {file?.name ? (
            <span className="text-sm opacity-80">
              Selected: <b>{file.name}</b>
            </span>
          ) : null}
        </div>
      ) : (
        <div className="mb-6 text-sm opacity-70">
          Upload is available only for Admin/QEC.
        </div>
      )}

      {/* LEFT-RIGHT layout */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* LEFT: Sentiment + topics */}
        <div className="card p-4 border rounded">
          <div className="flex items-start justify-between">
            <h3 className="text-lg font-semibold">Sentiment Analysis</h3>
            <div className="text-sm opacity-80">
              Total: <b>{summary.total}</b>
            </div>
          </div>

          <ResponsiveContainer width="100%" height={280}>
            <PieChart>
              <Pie
                data={sentimentData}
                dataKey="value"
                nameKey="name"
                outerRadius={95}
                innerRadius={55}
                onClick={(data) => {
                  if (!data?.name) return;
                  openDetails({
                    title: `Details • Sentiment: ${data.name}`,
                    extraParams: { sentiment: data.name },
                  });
                }}
              >
                {sentimentData.map((entry) => (
                  <Cell key={entry.name} fill={COLORS[entry.name]} />
                ))}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>

          <div className="mt-4 rounded border bg-gray-50 p-3">
            <div className="text-sm">
              <b>Main Conclusion:</b> {mainConclusion || "—"}
            </div>

            <div className="mt-2 text-sm">
              <b>Main Topics (from negative feedback):</b>{" "}
              {mainTopics.length ? mainTopics.join(", ") : "—"}
            </div>
          </div>
        </div>

        {/* RIGHT: Course-wise */}
        <div className="card p-4 border rounded">
          <h3 className="text-lg font-semibold mb-2">Course-wise Feedback</h3>

          <ResponsiveContainer width="100%" height={320}>
            <BarChart
              data={courseData}
              onClick={(e) => {
                const selectedCourse = e?.activeLabel;
                if (!selectedCourse) return;
                openDetails({
                  title: `Details • Course: ${selectedCourse}`,
                  extraParams: { course: selectedCourse },
                });
              }}
            >
              <XAxis dataKey="course" hide />
              <YAxis />
              <Tooltip />
              <Legend />
              <Bar dataKey="negative" fill={COLORS.negative} />
              <Bar dataKey="neutral" fill={COLORS.neutral} />
              <Bar dataKey="positive" fill={COLORS.positive} />
            </BarChart>
          </ResponsiveContainer>

          <p className="text-xs opacity-70 mt-2">Tip: Click bar to drill down.</p>
        </div>
      </div>

      {/* Drilldown Modal */}
      <Modal open={modalOpen} title={modalTitle} onClose={() => setModalOpen(false)}>
        {modalLoading ? (
          <p>Loading details...</p>
        ) : (
          <>
            <div className="text-sm opacity-80 mb-2">
              Showing {modalData.items?.length || 0} of {modalData.total || 0}
            </div>

            <div className="space-y-3">
              {(modalData.items || []).map((r) => (
                <div
                  key={r.id}
                  className="border rounded p-3"
                  style={{
                    background:
                      r.sentiment === "positive"
                        ? "#ecfdf5"
                        : r.sentiment === "negative"
                        ? "#fef2f2"
                        : "#fffbeb",
                  }}
                >
                  <div className="flex flex-wrap justify-between gap-2">
                    <div>
                      <b>{r.name || "Student"}</b>{" "}
                      <span className="opacity-70">
                        ({r.batch} • {r.department})
                      </span>
                    </div>
                    <div className="text-sm opacity-80">
                      <b style={{ color: COLORS[r.sentiment] }}>{r.sentiment}</b> • {r.emotion} • topic {r.topic}
                    </div>
                  </div>

                  <div className="text-sm opacity-80 mt-1">
                    <div>
                      <b>Course:</b> {r.course_name}
                    </div>
                    <div>
                      <b>Instructor:</b> {r.instructor_name}
                    </div>
                  </div>

                  <div className="mt-2">{r.comments}</div>
                </div>
              ))}
            </div>
          </>
        )}
      </Modal>
    </div>
  );
}
