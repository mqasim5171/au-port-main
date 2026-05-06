import React from "react";

export default function CourseProgressGrid({ weeks }) {
  return (
    <div className="grid-16">
      {weeks.map((w) => (
        <div key={w.week_no} className="week-card">
          <h4>Week {w.week_no}</h4>

          <div className="bar">
            <div
              className="bar-fill"
              style={{
                width: `${w.coverage_percent || 0}%`,
                background:
                  w.coverage_percent >= 80 ? "#22c55e" : "#ef4444",
              }}
            />
          </div>

          <div className="meta">
            <span>{(w.coverage_percent || 0).toFixed(1)}%</span>
            <span className={w.coverage_status}>
              {w.coverage_status}
            </span>
          </div>
        </div>
      ))}
    </div>
  );
}
