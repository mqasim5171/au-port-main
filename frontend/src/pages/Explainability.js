import React, { useState } from "react";
import CLOHeatmap from "./CLOHeatmap";
import GradingFairness from "./GradingFairness";
import AuditLogs from "./AuditLogs";

export default function Explainability({ user }) {
  const [tab, setTab] = useState("clo");

  return (
    <div className="fade-in">
      <h1 className="page-title">Explainability & QA</h1>
      <p className="page-subtitle">
        Transparent AI decisions, grading fairness, and audit trails
      </p>

      {/* Tabs */}
      <div className="tabs">
        <button className={tab === "clo" ? "active" : ""} onClick={() => setTab("clo")}>
          CLO Heatmap
        </button>
        <button className={tab === "fairness" ? "active" : ""} onClick={() => setTab("fairness")}>
          Grading Fairness
        </button>

        {(user?.role === "QEC" || user?.role === "Admin") && (
          <button className={tab === "audit" ? "active" : ""} onClick={() => setTab("audit")}>
            Audit Logs
          </button>
        )}
      </div>

      {/* Content */}
      <div className="tab-content">
        {tab === "clo" && <CLOHeatmap />}
        {tab === "fairness" && <GradingFairness />}
        {tab === "audit" && <AuditLogs />}
      </div>
    </div>
  );
}
