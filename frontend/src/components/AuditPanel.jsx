import React, { useState } from "react";

export default function AuditPanel({ audit }) {
  const [open, setOpen] = useState(false);

  if (!audit) return null;

  return (
    <div className="card">
      <button onClick={() => setOpen(!open)}>
        {open ? "Hide Audit" : "Why is this week behind?"}
      </button>

      {open && (
        <pre className="audit-box">
          {JSON.stringify(audit, null, 2)}
        </pre>
      )}
    </div>
  );
}
