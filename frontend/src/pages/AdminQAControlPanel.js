import React, { useEffect, useMemo, useState } from "react";
import api from "../api";
import "../App.css";

const badge = (type, value) => {
  const v = (value || "").toLowerCase();

  const styles = {
    critical: ["#fee2e2", "#991b1b"],
    high: ["#ffedd5", "#9a3412"],
    medium: ["#fef9c3", "#854d0e"],
    low: ["#dcfce7", "#166534"],
    open: ["#fee2e2", "#991b1b"],
    resolved: ["#dcfce7", "#166534"],
    ignored: ["#e5e7eb", "#374151"],
  };

  const [bg, fg] = styles[v] || ["#e0f2fe", "#075985"];

  return {
    display: "inline-flex",
    padding: "5px 10px",
    borderRadius: 999,
    background: bg,
    color: fg,
    fontWeight: 800,
    fontSize: 12,
    textTransform: "capitalize",
  };
};

export default function AdminQAControlPanel() {
  const [exceptions, setExceptions] = useState([]);
  const [summary, setSummary] = useState(null);

  const [statusFilter, setStatusFilter] = useState("open");
  const [moduleFilter, setModuleFilter] = useState("");
  const [severityFilter, setSeverityFilter] = useState("");

  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState("");

  const loadData = async () => {
    setErr("");
    setLoading(true);

    try {
      const params = {};

      if (statusFilter) params.status = statusFilter;
      if (moduleFilter) params.module = moduleFilter;
      if (severityFilter) params.severity = severityFilter;

      const [listRes, summaryRes] = await Promise.all([
        api.get("/exceptions/", { params }),
        api.get("/exceptions/summary"),
      ]);

      setExceptions(listRes.data || []);
      setSummary(summaryRes.data || null);
    } catch (e) {
      setErr(e?.response?.data?.detail || "Failed to load QA control panel.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
    // eslint-disable-next-line
  }, [statusFilter, moduleFilter, severityFilter]);

  const updateStatus = async (id, status) => {
    try {
      await api.patch(`/exceptions/${id}/status`, { status });
      await loadData();
    } catch (e) {
      setErr(e?.response?.data?.detail || "Failed to update exception status.");
    }
  };

  const modules = useMemo(() => {
    const set = new Set();

    exceptions.forEach((e) => {
      if (e.module) set.add(e.module);
    });

    return Array.from(set);
  }, [exceptions]);

  return (
    <div className="fade-in">
      <div className="page-header">
        <h1 className="page-title">Admin QA Control Panel</h1>
        <p className="page-subtitle">
          Monitor system exceptions, fallback cases, parsing failures, quality issues,
          and manual QA actions.
        </p>
      </div>

      {err && (
        <div
          className="card"
          style={{
            padding: 14,
            marginBottom: 16,
            background: "#fff1f2",
            border: "1px solid #fecaca",
            color: "#991b1b",
            fontWeight: 800,
          }}
        >
          {err}
        </div>
      )}

      <div className="dashboard-grid" style={{ marginBottom: 24 }}>
        <div className="stats-card">
          <div className="stats-number">{summary?.total ?? "—"}</div>
          <div className="stats-label">Total Exceptions</div>
        </div>

        <div className="stats-card">
          <div className="stats-number">{summary?.open ?? "—"}</div>
          <div className="stats-label">Open</div>
        </div>

        <div className="stats-card">
          <div className="stats-number">{summary?.critical ?? "—"}</div>
          <div className="stats-label">Critical</div>
        </div>

        <div className="stats-card">
          <div className="stats-number">{summary?.resolved ?? "—"}</div>
          <div className="stats-label">Resolved</div>
        </div>
      </div>

      <div className="card" style={{ marginBottom: 24 }}>
        <div className="card-header">
          <h2 className="card-title">Filters</h2>
        </div>

        <div
          className="card-content"
          style={{
            display: "grid",
            gridTemplateColumns: "1fr 1fr 1fr auto",
            gap: 12,
            alignItems: "center",
          }}
        >
          <select
            className="form-input"
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
          >
            <option value="">All Statuses</option>
            <option value="open">Open</option>
            <option value="resolved">Resolved</option>
            <option value="ignored">Ignored</option>
          </select>

          <select
            className="form-input"
            value={moduleFilter}
            onChange={(e) => setModuleFilter(e.target.value)}
          >
            <option value="">All Modules</option>
            {modules.map((m) => (
              <option key={m} value={m}>
                {m}
              </option>
            ))}
          </select>

          <select
            className="form-input"
            value={severityFilter}
            onChange={(e) => setSeverityFilter(e.target.value)}
          >
            <option value="">All Severities</option>
            <option value="critical">Critical</option>
            <option value="high">High</option>
            <option value="medium">Medium</option>
            <option value="low">Low</option>
          </select>

          <button className="btn btn-secondary" onClick={loadData}>
            Refresh
          </button>
        </div>
      </div>

      <div className="card">
        <div className="card-header">
          <h2 className="card-title">Exception Logbook</h2>
        </div>

        <div className="card-content">
          {loading ? (
            <div style={{ color: "#64748b" }}>Loading exceptions...</div>
          ) : exceptions.length === 0 ? (
            <div
              style={{
                padding: 24,
                textAlign: "center",
                color: "#64748b",
                background: "#f8fafc",
                border: "1px dashed #cbd5e1",
                borderRadius: 14,
              }}
            >
              No exceptions found for the selected filters.
            </div>
          ) : (
            <div style={{ overflowX: "auto" }}>
              <table
                style={{
                  width: "100%",
                  borderCollapse: "collapse",
                  fontSize: 14,
                }}
              >
                <thead>
                  <tr style={{ background: "#f8fafc" }}>
                    <th style={th}>Module</th>
                    <th style={th}>Error Type</th>
                    <th style={th}>Message</th>
                    <th style={th}>Severity</th>
                    <th style={th}>Status</th>
                    <th style={th}>Created</th>
                    <th style={th}>Actions</th>
                  </tr>
                </thead>

                <tbody>
                  {exceptions.map((item) => (
                    <tr key={item.id}>
                      <td style={td}>{item.module}</td>
                      <td style={td}>{item.error_type}</td>
                      <td style={{ ...td, minWidth: 260 }}>{item.message}</td>
                      <td style={td}>
                        <span style={badge("severity", item.severity)}>
                          {item.severity}
                        </span>
                      </td>
                      <td style={td}>
                        <span style={badge("status", item.status)}>
                          {item.status}
                        </span>
                      </td>
                      <td style={td}>
                        {item.created_at
                          ? new Date(item.created_at).toLocaleString()
                          : "—"}
                      </td>
                      <td style={td}>
                        <div style={{ display: "flex", gap: 8 }}>
                          {item.status !== "resolved" && (
                            <button
                              className="btn btn-success"
                              style={{ padding: "6px 10px", fontSize: 12 }}
                              onClick={() => updateStatus(item.id, "resolved")}
                            >
                              Resolve
                            </button>
                          )}

                          {item.status !== "ignored" && (
                            <button
                              className="btn btn-secondary"
                              style={{ padding: "6px 10px", fontSize: 12 }}
                              onClick={() => updateStatus(item.id, "ignored")}
                            >
                              Ignore
                            </button>
                          )}

                          {item.status !== "open" && (
                            <button
                              className="btn btn-primary"
                              style={{ padding: "6px 10px", fontSize: 12 }}
                              onClick={() => updateStatus(item.id, "open")}
                            >
                              Reopen
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

const th = {
  padding: "12px",
  textAlign: "left",
  borderBottom: "1px solid #e2e8f0",
  color: "#475569",
  fontWeight: 900,
};

const td = {
  padding: "12px",
  borderBottom: "1px solid #e2e8f0",
  verticalAlign: "top",
};