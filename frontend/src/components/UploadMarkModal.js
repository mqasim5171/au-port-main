// src/components/UploadMarksModal.js
import React, { useState } from "react";
import { bulkUploadMarks } from "../api";

export default function UploadMarksModal({ assessmentId, onClose }) {
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!file) return;
    setLoading(true);
    bulkUploadMarks(assessmentId, file)
      .then((res) => {
        setMessage(`Uploaded / updated: ${res.data.updated} rows`);
      })
      .finally(() => setLoading(false));
  };

  return (
    <div className="modal-backdrop">
      <div className="modal">
        <header className="modal-header">
          <h3>Upload Marks</h3>
          <button onClick={onClose}>&times;</button>
        </header>
        <form onSubmit={handleSubmit} className="modal-body">
          <p>Upload CSV with columns: <b>reg_no, obtained_marks</b></p>
          <input
            type="file"
            accept=".csv"
            onChange={(e) => setFile(e.target.files?.[0] || null)}
          />
          <button className="btn-primary" type="submit" disabled={loading}>
            {loading ? "Uploading..." : "Upload"}
          </button>
          {message && <p className="info-text">{message}</p>}
        </form>
      </div>
    </div>
  );
}
