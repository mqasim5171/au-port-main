import React, { useEffect, useMemo, useState } from "react";
import api from "../api";
import { useParams } from "react-router-dom";

const styles = {
  page: {
    maxWidth: 1180,
    margin: "0 auto",
    display: "grid",
    gap: 16,
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
  muted: {
    color: "#6b7280",
    fontSize: 13,
    lineHeight: 1.5,
  },
  btnPrimary: {
    border: "none",
    background: "#2563eb",
    color: "#fff",
    borderRadius: 12,
    padding: "10px 14px",
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
  badge: {
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
  successBadge: {
    display: "inline-flex",
    alignItems: "center",
    borderRadius: 999,
    padding: "5px 10px",
    fontSize: 12,
    fontWeight: 800,
    background: "#f0fdf4",
    color: "#166534",
    border: "1px solid #bbf7d0",
    whiteSpace: "nowrap",
  },
  dangerBadge: {
    display: "inline-flex",
    alignItems: "center",
    borderRadius: 999,
    padding: "5px 10px",
    fontSize: 12,
    fontWeight: 800,
    background: "#fff1f2",
    color: "#991b1b",
    border: "1px solid #fecaca",
    whiteSpace: "nowrap",
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
  stepGrid: {
    display: "grid",
    gridTemplateColumns: "repeat(4, minmax(0, 1fr))",
    gap: 12,
  },
  step: {
    border: "1px solid #e5e7eb",
    borderRadius: 16,
    padding: 14,
    background: "#fff",
  },
  panel: {
    border: "1px solid #e5e7eb",
    borderRadius: 16,
    padding: 16,
    background: "#fff",
  },
  tableWrap: {
    overflowX: "auto",
    border: "1px solid #e5e7eb",
    borderRadius: 14,
  },
  table: {
    width: "100%",
    borderCollapse: "collapse",
  },
  th: {
    textAlign: "left",
    padding: 12,
    background: "#f9fafb",
    borderBottom: "1px solid #e5e7eb",
    color: "#374151",
    fontSize: 13,
  },
  td: {
    padding: 12,
    borderBottom: "1px solid #f3f4f6",
    color: "#111827",
    verticalAlign: "top",
    fontSize: 14,
  },
};

function StatusBadge({ ok, children }) {
  return <span style={ok ? styles.successBadge : styles.dangerBadge}>{children}</span>;
}

function StepCard({ no, title, status, children }) {
  return (
    <div style={styles.step}>
      <div style={{ display: "flex", justifyContent: "space-between", gap: 10 }}>
        <span style={styles.badge}>Step {no}</span>
        {status}
      </div>

      <div style={{ fontWeight: 900, color: "#111827", marginTop: 12 }}>
        {title}
      </div>

      <div style={{ ...styles.muted, marginTop: 8 }}>{children}</div>
    </div>
  );
}

function getRollNo(row) {
  const direct =
    row.roll_no ||
    row.rollNo ||
    row.student_roll_no ||
    row.studentRollNo ||
    row.student?.roll_no ||
    row.student?.rollNo ||
    row.student?.roll_number ||
    row.student?.rollNumber ||
    row.student?.reg_no ||
    row.evidence_json?.reg_no;

  if (direct) return String(direct);

  const name =
    row.filename_original ||
    row.filename ||
    row.file_name ||
    row.submission_filename ||
    row.upload?.filename_original ||
    row.evidence_json?.filename_original ||
    "";

  if (!name) return "-";

  const m1 = name.match(/(\d{2}[-_ ]?[A-Za-z]{1,4}[-_ ]?\d{2,4})/);

  if (m1) return m1[1].replace(/[_ ]/g, "-").toUpperCase();

  const m2 = name.match(/(\d{6,12})/);

  if (m2) return m2[1];

  return "-";
}

function shortFileName(row) {
  const name =
    row.filename_original ||
    row.filename ||
    row.file_name ||
    row.submission_filename ||
    row.upload?.filename_original ||
    row.evidence_json?.filename_original ||
    "";

  if (!name) return "-";

  const base = name.split("/").pop();

  return base.length > 38 ? base.slice(0, 38) + "…" : base;
}

function statusTone(status) {
  const s = String(status || "").toLowerCase();

  if (s === "graded") return styles.successBadge;
  if (s === "error") return styles.dangerBadge;

  return styles.badge;
}

export default function AssessmentDetail() {
  const { id } = useParams();

  const [data, setData] = useState(null);
  const [qFile, setQFile] = useState(null);
  const [zipFile, setZipFile] = useState(null);

  const [submissionsRefreshKey, setSubmissionsRefreshKey] = useState(0);
  const [subStats, setSubStats] = useState({
    total: 0,
    graded: 0,
    uploaded: 0,
    error: 0,
  });

  const [err, setErr] = useState("");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);

  const load = async () => {
    setErr("");

    const res = await api.get(`/assessments/${id}`);
    setData(res.data);
  };

  useEffect(() => {
    load().catch((e) => setErr(e?.response?.data?.detail || "Load failed"));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  const uploadQuestions = async () => {
    setErr("");
    setMessage("");

    if (!qFile) {
      setErr("Select a questions PDF/DOCX first.");
      return;
    }

    const name = qFile.name || "";

    if (!name.toLowerCase().endsWith(".pdf") && !name.toLowerCase().endsWith(".docx")) {
      setErr("Only PDF and DOCX question files are allowed.");
      return;
    }

    setBusy(true);

    try {
      const form = new FormData();
      form.append("file", qFile);

      const res = await api.post(`/assessments/${id}/questions/upload`, form, {
        headers: { "Content-Type": "multipart/form-data" },
      });

      setQFile(null);
      setMessage(
        `Questions uploaded successfully. Extracted text length: ${
          res?.data?.extracted_len ?? 0
        } characters.`
      );

      await load();
    } catch (e) {
      setErr(e?.response?.data?.detail || "Upload questions failed");
    } finally {
      setBusy(false);
    }
  };

  const generateExpected = async () => {
    setErr("");
    setMessage("");
    setBusy(true);

    try {
      const res = await api.post(`/assessments/${id}/generate-expected-answers`);

      setMessage(
        `Expected answers generated. CLO coverage: ${
          res?.data?.clo_coverage_percent ?? 0
        }%.`
      );

      await load();
    } catch (e) {
      setErr(e?.response?.data?.detail || "Generate expected answers failed");
    } finally {
      setBusy(false);
    }
  };

  const uploadSubmissionsZip = async () => {
    setErr("");
    setMessage("");

    if (!zipFile) {
      setErr("Select a submissions ZIP file first.");
      return;
    }

    if (!zipFile.name.toLowerCase().endsWith(".zip")) {
      setErr("Only ZIP files are allowed for student submissions.");
      return;
    }

    setBusy(true);

    try {
      const form = new FormData();
      form.append("file", zipFile);

      const res = await api.post(`/assessments/${id}/submissions/upload-zip`, form, {
        headers: { "Content-Type": "multipart/form-data" },
      });

      setZipFile(null);

      setMessage(
        `ZIP extracted successfully. Files seen: ${
          res?.data?.files_seen ?? 0
        }, created: ${res?.data?.created ?? 0}, updated: ${
          res?.data?.updated ?? 0
        }, skipped: ${res?.data?.skipped ?? 0}.`
      );

      setSubmissionsRefreshKey((k) => k + 1);
    } catch (e) {
      setErr(e?.response?.data?.detail || "Upload ZIP failed");
    } finally {
      setBusy(false);
    }
  };

  const gradeAllSubmissions = async () => {
    setErr("");
    setMessage("");
    setBusy(true);

    try {
      const res = await api.post(`/assessments/${id}/grade-all`);

      setMessage(
        `Grading completed. Graded: ${res?.data?.graded ?? 0}, failed: ${
          res?.data?.failed ?? 0
        }.`
      );

      setSubmissionsRefreshKey((k) => k + 1);
    } catch (e) {
      setErr(e?.response?.data?.detail || "Grade all failed");
    } finally {
      setBusy(false);
    }
  };

  const meta = useMemo(() => {
    if (!data) return null;

    const { assessment, expected, clo_alignment } = data;

    return {
      assessment,
      expected,
      clo_alignment,
    };
  }, [data]);

  if (!data || !meta) {
    return (
      <div style={styles.page}>
        <div style={styles.card}>Loading assessment...</div>
      </div>
    );
  }

  const { assessment, files, expected, clo_alignment } = data;

  const expectedOk = !!expected?.parsed_json;
  const questionsOk = !!(files || []).length;
  const coverPct = Number(clo_alignment?.coverage_percent || 0);

  return (
    <div style={styles.page}>
      <div style={styles.hero}>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          <span style={styles.badge}>Assessment Workspace</span>
          <span style={styles.badge}>Bulk ZIP Grading</span>
          <span style={styles.badge}>AI Expected Answers</span>
        </div>

        <h2 style={{ ...styles.title, marginTop: 14 }}>{assessment.title}</h2>

        <p style={styles.subtitle}>
          Upload the assessment question paper, generate AI expected answers,
          upload student solutions as one ZIP file, and grade all submissions in
          one run.
        </p>

        <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginTop: 14 }}>
          <span style={styles.badge}>Type: {assessment.type}</span>
          <span style={styles.badge}>Max Marks: {assessment.max_marks}</span>
          <span style={styles.badge}>Weightage: {assessment.weightage ?? "-"}</span>
          <span style={styles.badge}>
            Date: {assessment.date ? String(assessment.date).slice(0, 10) : "-"}
          </span>
          <StatusBadge ok={questionsOk}>
            {questionsOk ? "Questions Uploaded" : "Questions Missing"}
          </StatusBadge>
          <StatusBadge ok={expectedOk}>
            {expectedOk ? "Expected Ready" : "Expected Missing"}
          </StatusBadge>
          <StatusBadge ok={coverPct >= 40}>CLO: {coverPct.toFixed(1)}%</StatusBadge>
        </div>
      </div>

      {err && <div style={styles.alert}>{err}</div>}
      {message && <div style={styles.success}>{message}</div>}

      <div style={styles.card}>
        <h3 style={styles.h3}>Workflow</h3>

        <div style={{ ...styles.stepGrid, marginTop: 14 }}>
          <StepCard
            no="1"
            title="Upload Questions"
            status={
              <StatusBadge ok={questionsOk}>
                {questionsOk ? "Done" : "Pending"}
              </StatusBadge>
            }
          >
            Upload the PDF/DOCX question file. The backend extracts its text.
          </StepCard>

          <StepCard
            no="2"
            title="Generate Expected"
            status={
              <StatusBadge ok={expectedOk}>
                {expectedOk ? "Ready" : "Pending"}
              </StatusBadge>
            }
          >
            AI generates expected answers and maps the assessment with CLOs.
          </StepCard>

          <StepCard
            no="3"
            title="Upload ZIP"
            status={
              <span style={styles.badge}>
                {subStats.total ? `${subStats.total} submissions` : "Pending"}
              </span>
            }
          >
            Upload all student solutions in one ZIP. Backend extracts and parses them.
          </StepCard>

          <StepCard
            no="4"
            title="Grade All"
            status={
              <span style={subStats.graded ? styles.successBadge : styles.badge}>
                {subStats.graded ? `${subStats.graded} graded` : "Pending"}
              </span>
            }
          >
            AI grades every parsed submission against expected answers.
          </StepCard>
        </div>
      </div>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "1fr 1fr",
          gap: 16,
        }}
      >
        <div style={styles.card}>
          <h3 style={styles.h3}>Questions & Expected Answers</h3>

          <div style={{ ...styles.panel, marginTop: 14 }}>
            <div style={{ fontWeight: 900, color: "#111827" }}>
              Upload Question File
            </div>

            <p style={styles.muted}>
              Accepted formats: PDF, DOCX. This file is used to generate expected
              answers and CLO alignment.
            </p>

            <input
              type="file"
              accept=".pdf,.docx"
              onChange={(e) => setQFile(e.target.files?.[0] || null)}
            />

            <div style={{ ...styles.muted, marginTop: 8 }}>
              Selected: <b>{qFile?.name || "No file selected"}</b>
            </div>

            <button
              type="button"
              style={{
                ...styles.btnPrimary,
                marginTop: 12,
                opacity: busy ? 0.65 : 1,
              }}
              onClick={uploadQuestions}
              disabled={busy}
            >
              {busy ? "Working..." : "Upload Questions"}
            </button>
          </div>

          <div style={{ ...styles.panel, marginTop: 14 }}>
            <div style={{ fontWeight: 900, color: "#111827" }}>
              Generate Expected Answers + CLO Alignment
            </div>

            <p style={styles.muted}>
              This uses the uploaded question file to create a marking reference
              and calculate CLO coverage.
            </p>

            <button
              type="button"
              style={{
                ...styles.btn,
                opacity: busy || !questionsOk ? 0.65 : 1,
              }}
              onClick={generateExpected}
              disabled={busy || !questionsOk}
            >
              {busy ? "Working..." : "Generate Expected + CLO Align"}
            </button>

            <div style={{ marginTop: 12 }}>
              <div style={{ fontWeight: 800, color: "#111827" }}>
                Uploaded Question Files
              </div>

              {!!(files || []).length ? (
                <ul style={{ marginTop: 8, paddingLeft: 18 }}>
                  {(files || []).map((f) => (
                    <li key={f.id}>
                      {f.filename_original}{" "}
                      <span style={styles.muted}>(ext: {f.ext})</span>
                    </li>
                  ))}
                </ul>
              ) : (
                <div style={{ ...styles.muted, marginTop: 8 }}>
                  No question file uploaded yet.
                </div>
              )}
            </div>
          </div>
        </div>

        <div style={styles.card}>
          <h3 style={styles.h3}>AI Results</h3>

          <div
            style={{
              marginTop: 14,
              display: "grid",
              gridTemplateColumns: "1fr 1fr",
              gap: 12,
            }}
          >
            <div style={styles.panel}>
              <div style={styles.muted}>Expected Answers</div>
              <div style={{ fontWeight: 900, color: "#111827", marginTop: 6 }}>
                {expectedOk ? "Generated" : "Not Generated"}
              </div>
              {expected?.model && (
                <div style={{ ...styles.muted, marginTop: 6 }}>
                  Model: <b>{expected.model}</b>
                </div>
              )}
            </div>

            <div style={styles.panel}>
              <div style={styles.muted}>CLO Coverage</div>
              <div style={{ fontWeight: 900, color: "#111827", marginTop: 6 }}>
                {coverPct.toFixed(1)}%
              </div>
            </div>
          </div>

          {clo_alignment?.per_clo ? (
            <details style={{ marginTop: 14 }}>
              <summary style={{ cursor: "pointer", fontWeight: 900 }}>
                View CLO Breakdown
              </summary>

              <pre
                style={{
                  marginTop: 10,
                  maxHeight: 220,
                  overflow: "auto",
                  background: "#f9fafb",
                  border: "1px solid #e5e7eb",
                  borderRadius: 12,
                  padding: 12,
                }}
              >
                {JSON.stringify(clo_alignment.per_clo, null, 2)}
              </pre>
            </details>
          ) : null}

          {expectedOk ? (
            <details style={{ marginTop: 14 }}>
              <summary style={{ cursor: "pointer", fontWeight: 900 }}>
                View Expected Answers JSON
              </summary>

              <pre
                style={{
                  marginTop: 10,
                  maxHeight: 260,
                  overflow: "auto",
                  background: "#f9fafb",
                  border: "1px solid #e5e7eb",
                  borderRadius: 12,
                  padding: 12,
                }}
              >
                {JSON.stringify(expected.parsed_json, null, 2)}
              </pre>
            </details>
          ) : null}
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
            <h3 style={styles.h3}>Student Submissions ZIP</h3>
            <p style={{ ...styles.muted, marginTop: 4 }}>
              Upload one ZIP containing all student solutions. The backend will
              unzip it, parse supported files, infer roll numbers, create/update
              submissions, and then grade them.
            </p>
          </div>

          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
            <span style={styles.badge}>Total: {subStats.total}</span>
            <span style={styles.successBadge}>Graded: {subStats.graded}</span>
            <span style={styles.badge}>Uploaded: {subStats.uploaded}</span>
            <span style={styles.dangerBadge}>Errors: {subStats.error}</span>
          </div>
        </div>

        <div style={{ ...styles.panel, marginTop: 14 }}>
          <div
            style={{
              display: "flex",
              gap: 12,
              alignItems: "center",
              flexWrap: "wrap",
            }}
          >
            <div style={{ minWidth: 280 }}>
              <div style={{ fontWeight: 900, color: "#111827" }}>
                Select ZIP File
              </div>

              <input
                type="file"
                accept=".zip"
                onChange={(e) => setZipFile(e.target.files?.[0] || null)}
                style={{ marginTop: 8 }}
              />

              <div style={{ ...styles.muted, marginTop: 8 }}>
                Selected: <b>{zipFile?.name || "No ZIP selected"}</b>
              </div>
            </div>

            <button
              type="button"
              style={{
                ...styles.btnPrimary,
                opacity: busy || !zipFile ? 0.65 : 1,
              }}
              onClick={uploadSubmissionsZip}
              disabled={busy || !zipFile}
            >
              {busy ? "Working..." : "Upload & Extract ZIP"}
            </button>

            <button
              type="button"
              style={{
                ...styles.btn,
                opacity: busy || !expectedOk ? 0.65 : 1,
              }}
              onClick={gradeAllSubmissions}
              disabled={busy || !expectedOk}
            >
              {busy ? "Working..." : "Grade All"}
            </button>

            <button
              type="button"
              style={styles.btn}
              onClick={() => setSubmissionsRefreshKey((k) => k + 1)}
              disabled={busy}
            >
              Refresh
            </button>
          </div>
        </div>

        <SubmissionsTable
          assessmentId={assessment.id}
          refreshKey={submissionsRefreshKey}
          onStats={setSubStats}
        />
      </div>

      <div style={styles.card}>
        <h3 style={styles.h3}>Viva Explanation</h3>

        <p style={styles.muted}>
          In this module, the teacher first uploads the question paper. The
          system extracts text from the question file and generates expected
          answers using AI. Then the teacher uploads all student solutions as a
          single ZIP file. The backend safely extracts the ZIP, ignores unsafe
          paths, reads supported files, detects student roll numbers from the
          document text or filename, stores each submission, and grades every
          submission against the generated expected answers.
        </p>
      </div>
    </div>
  );
}


function SubmissionsTable({ assessmentId, refreshKey, onStats }) {
  const [rows, setRows] = useState([]);
  const [err, setErr] = useState("");
  const [loading, setLoading] = useState(false);

  const calculateStats = (items) => {
    const total = items.length;
    const graded = items.filter((x) => String(x.status || "").toLowerCase() === "graded").length;
    const uploaded = items.filter((x) => String(x.status || "").toLowerCase() === "uploaded").length;
    const error = items.filter((x) => String(x.status || "").toLowerCase() === "error").length;

    return {
      total,
      graded,
      uploaded,
      error,
    };
  };

  const load = async () => {
    setErr("");
    setLoading(true);

    try {
      const res = await api.get(`/assessments/${assessmentId}/submissions`);
      const list = res.data || [];

      setRows(list);

      if (onStats) {
        onStats(calculateStats(list));
      }
    } catch (e) {
      setErr(e?.response?.data?.detail || "Failed to load submissions");

      if (onStats) {
        onStats({
          total: 0,
          graded: 0,
          uploaded: 0,
          error: 0,
        });
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [assessmentId, refreshKey]);

  return (
    <div style={{ marginTop: 16 }}>
      {err && <div style={styles.alert}>{err}</div>}

      <div style={{ ...styles.muted, marginBottom: 8 }}>
        Total submissions: <b>{rows.length}</b>
        {loading ? " · Loading..." : ""}
      </div>

      <div style={styles.tableWrap}>
        <table style={styles.table}>
          <thead>
            <tr>
              <th style={{ ...styles.th, width: 140 }}>Roll No</th>
              <th style={{ ...styles.th, width: 210 }}>File</th>
              <th style={{ ...styles.th, width: 120 }}>Status</th>
              <th style={{ ...styles.th, width: 100 }}>Marks</th>
              <th style={styles.th}>Feedback</th>
            </tr>
          </thead>

          <tbody>
            {rows.map((r) => {
              const fb = r.ai_feedback || "";
              const marks = r.ai_marks ?? "-";
              const roll = getRollNo(r);
              const file = shortFileName(r);

              return (
                <tr key={r.id}>
                  <td style={{ ...styles.td, fontWeight: 900 }}>{roll}</td>

                  <td
                    style={{ ...styles.td, color: "#6b7280" }}
                    title={r.filename_original || r.filename || ""}
                  >
                    {file}
                  </td>

                  <td style={styles.td}>
                    <span style={statusTone(r.status)}>{r.status || "-"}</span>
                  </td>

                  <td style={{ ...styles.td, fontWeight: 900 }}>{marks}</td>

                  <td style={{ ...styles.td, maxWidth: 720 }} title={fb}>
                    {fb ? (
                      <>
                        {fb.slice(0, 260)}
                        {fb.length > 260 ? "..." : ""}
                      </>
                    ) : (
                      <span style={styles.muted}>No feedback yet</span>
                    )}
                  </td>
                </tr>
              );
            })}

            {!rows.length && (
              <tr>
                <td colSpan={5} style={{ ...styles.td, color: "#6b7280" }}>
                  No submissions yet. Upload a ZIP file to create submissions.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}