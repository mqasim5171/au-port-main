import React, { useEffect, useState } from "react";
import api from "../pages/api"; // ✅ keep same style as your project

const GradingAuditTab = ({ assessmentId }) => {
  const [auditRows, setAuditRows] = useState([]);
  const [loading, setLoading] = useState(false);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState("");

  const fetchAudit = async () => {
    setLoading(true);
    setError("");
    try {
      // ✅ if your backend router prefix is "/api", api baseURL already includes it or not.
      // We will keep endpoint consistent with backend example:
      const res = await api.get(`/assessments/${assessmentId}/grading-audit`);
      setAuditRows(res.data || []);
    } catch (e) {
      setError(e?.response?.data?.detail || "Failed to load grading audit.");
    } finally {
      setLoading(false);
    }
  };

  const runAudit = async () => {
    setRunning(true);
    setError("");
    try {
      await api.post(`/assessments/${assessmentId}/run-grading-audit`);
      await fetchAudit(); // ✅ refresh after running
    } catch (e) {
      setError(e?.response?.data?.detail || "Failed to run grading audit.");
    } finally {
      setRunning(false);
    }
  };

  useEffect(() => {
    if (assessmentId) fetchAudit();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [assessmentId]);

  // Extract known metrics (latest first since backend returns desc)
  const distribution = auditRows.find(r => r.metric === "distribution")?.value;
  const outliers = auditRows.find(r => r.metric === "outliers")?.value;
  const cloAvg = auditRows.find(r => r.metric === "clo_avg")?.value;

  return (
    <div style={{ marginTop: 24 }}>
      <h3>Grading Audit</h3>

      <div style={{ display: "flex", gap: 10, marginBottom: 12 }}>
        <button onClick={runAudit} disabled={running}>
          {running ? "Running..." : "Run Grading Audit"}
        </button>

        <button onClick={fetchAudit} disabled={loading}>
          {loading ? "Refreshing..." : "Refresh"}
        </button>
      </div>

      {error && (
        <div style={{ color: "crimson", marginBottom: 10 }}>
          {error}
        </div>
      )}

      {/* Distribution */}
      <div style={{ padding: 12, border: "1px solid #ddd", marginBottom: 12 }}>
        <h4>Distribution</h4>
        {distribution ? (
          <ul style={{ margin: 0 }}>
            <li>Mean: {Number(distribution.mean).toFixed(2)}</li>
            <li>Median: {Number(distribution.median).toFixed(2)}</li>
            <li>Std Dev: {Number(distribution.std).toFixed(2)}</li>
            <li>Samples: {distribution.marks?.length || 0}</li>
          </ul>
        ) : (
          <p style={{ margin: 0 }}>No distribution data yet. Run audit.</p>
        )}
      </div>

      {/* Outliers */}
      <div style={{ padding: 12, border: "1px solid #ddd", marginBottom: 12 }}>
        <h4>Outliers</h4>
        {outliers ? (
          <>
            <p style={{ marginTop: 0 }}>
              Count: <b>{outliers.count}</b>
            </p>
            {outliers.values?.length ? (
              <div>
                <p style={{ marginBottom: 6 }}>Values:</p>
                <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                  {outliers.values.map((v, idx) => (
                    <span
                      key={idx}
                      style={{
                        padding: "4px 8px",
                        border: "1px solid #ccc",
                        borderRadius: 6,
                      }}
                    >
                      {v}
                    </span>
                  ))}
                </div>
              </div>
            ) : (
              <p style={{ margin: 0 }}>No outlier values detected.</p>
            )}
          </>
        ) : (
          <p style={{ margin: 0 }}>No outliers data yet. Run audit.</p>
        )}
      </div>

      {/* CLO-wise Average */}
      <div style={{ padding: 12, border: "1px solid #ddd" }}>
        <h4>CLO-wise Average</h4>
        {cloAvg && Object.keys(cloAvg).length ? (
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr>
                <th style={{ textAlign: "left", borderBottom: "1px solid #ddd", padding: 6 }}>
                  CLO ID
                </th>
                <th style={{ textAlign: "left", borderBottom: "1px solid #ddd", padding: 6 }}>
                  Avg %
                </th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(cloAvg).map(([cloId, avg]) => (
                <tr key={cloId}>
                  <td style={{ borderBottom: "1px solid #f0f0f0", padding: 6 }}>
                    {cloId}
                  </td>
                  <td style={{ borderBottom: "1px solid #f0f0f0", padding: 6 }}>
                    {(Number(avg) * 100).toFixed(1)}%
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <p style={{ margin: 0 }}>No CLO average yet. Run audit.</p>
        )}
      </div>
    </div>
  );
};

export default GradingAuditTab;
