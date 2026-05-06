import React, { useEffect, useState } from "react";
import api from "../api";

const categories = [
  { value: "all", label: "All Categories" },
  { value: "policy", label: "Policy" },
  { value: "contract", label: "Contract" },
  { value: "budget", label: "Budget" },
  { value: "rules", label: "Rules" },
  { value: "template", label: "Template" },
  { value: "accreditation", label: "Accreditation" },
  { value: "meeting_minutes", label: "Meeting Minutes" },
  { value: "other", label: "Other" },
];

export default function AdminDocuments() {
  const [documents, setDocuments] = useState([]);
  const [categoryFilter, setCategoryFilter] = useState("all");
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);

  const [form, setForm] = useState({
    title: "",
    category: "policy",
    description: "",
    file: null,
  });

  useEffect(() => {
    loadDocuments();
  }, [categoryFilter]);

  const loadDocuments = async () => {
    try {
      setLoading(true);
      const res = await api.get("/admin-documents/", {
        params: {
          category: categoryFilter,
        },
      });

      setDocuments(res.data || []);
    } catch (err) {
      console.error(err);
      alert("Failed to load administrative documents.");
    } finally {
      setLoading(false);
    }
  };

  const handleChange = (e) => {
    const { name, value, files } = e.target;

    if (name === "file") {
      setForm((prev) => ({
        ...prev,
        file: files?.[0] || null,
      }));
      return;
    }

    setForm((prev) => ({
      ...prev,
      [name]: value,
    }));
  };

  const handleUpload = async (e) => {
    e.preventDefault();

    if (!form.title.trim()) {
      alert("Please enter document title.");
      return;
    }

    if (!form.file) {
      alert("Please select a file.");
      return;
    }

    const data = new FormData();
    data.append("title", form.title);
    data.append("category", form.category);
    data.append("description", form.description || "");
    data.append("file", form.file);

    try {
      setUploading(true);

      await api.post("/admin-documents/", data, {
        headers: {
          "Content-Type": "multipart/form-data",
        },
      });

      setForm({
        title: "",
        category: "policy",
        description: "",
        file: null,
      });

      const fileInput = document.getElementById("admin-document-file");
      if (fileInput) fileInput.value = "";

      await loadDocuments();
      alert("Document uploaded successfully.");
    } catch (err) {
      console.error(err);
      alert(err?.response?.data?.detail || "Failed to upload document.");
    } finally {
      setUploading(false);
    }
  };

  const downloadDocument = async (doc) => {
    try {
      const res = await api.get(`/admin-documents/${doc.id}/download`, {
        responseType: "blob",
      });

      const url = window.URL.createObjectURL(new Blob([res.data]));
      const link = document.createElement("a");

      link.href = url;
      link.setAttribute("download", doc.original_filename || "document");
      document.body.appendChild(link);
      link.click();

      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      console.error(err);
      alert("Failed to download document.");
    }
  };

  const deleteDocument = async (doc) => {
    const ok = window.confirm(
      `Delete "${doc.title}" v${doc.version}? This cannot be undone.`
    );

    if (!ok) return;

    try {
      await api.delete(`/admin-documents/${doc.id}`);
      await loadDocuments();
      alert("Document deleted successfully.");
    } catch (err) {
      console.error(err);
      alert(err?.response?.data?.detail || "Failed to delete document.");
    }
  };

  const formatDate = (value) => {
    if (!value) return "-";

    try {
      return new Date(value).toLocaleString();
    } catch {
      return value;
    }
  };

  return (
    <div className="fade-in">
      <h1 className="page-title">Administrative Document Manager</h1>
      <p className="page-subtitle">
        Upload, organize, version, and manage administrative QA documents.
      </p>

      <div className="card" style={{ marginBottom: "24px" }}>
        <h2>Upload New Document</h2>

        <form onSubmit={handleUpload}>
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
              gap: "16px",
              marginTop: "16px",
            }}
          >
            <div>
              <label className="form-label">Document Title</label>
              <input
                className="form-control"
                name="title"
                value={form.title}
                onChange={handleChange}
                placeholder="Example: QEC Policy Manual"
              />
            </div>

            <div>
              <label className="form-label">Category</label>
              <select
                className="form-control"
                name="category"
                value={form.category}
                onChange={handleChange}
              >
                {categories
                  .filter((c) => c.value !== "all")
                  .map((c) => (
                    <option key={c.value} value={c.value}>
                      {c.label}
                    </option>
                  ))}
              </select>
            </div>

            <div>
              <label className="form-label">File</label>
              <input
                id="admin-document-file"
                className="form-control"
                name="file"
                type="file"
                onChange={handleChange}
              />
            </div>
          </div>

          <div style={{ marginTop: "16px" }}>
            <label className="form-label">Description</label>
            <textarea
              className="form-control"
              name="description"
              value={form.description}
              onChange={handleChange}
              placeholder="Optional description or notes"
              rows="3"
            />
          </div>

          <button
            className="btn btn-primary"
            type="submit"
            disabled={uploading}
            style={{ marginTop: "16px" }}
          >
            {uploading ? "Uploading..." : "Upload Document"}
          </button>
        </form>
      </div>

      <div className="card">
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            gap: "16px",
            alignItems: "center",
            marginBottom: "16px",
            flexWrap: "wrap",
          }}
        >
          <div>
            <h2>Document Repository</h2>
            <p style={{ margin: 0, color: "#64748b" }}>
              Filter by category and download stored versions.
            </p>
          </div>

          <select
            className="form-control"
            value={categoryFilter}
            onChange={(e) => setCategoryFilter(e.target.value)}
            style={{ maxWidth: "240px" }}
          >
            {categories.map((c) => (
              <option key={c.value} value={c.value}>
                {c.label}
              </option>
            ))}
          </select>
        </div>

        {loading ? (
          <p>Loading documents...</p>
        ) : documents.length === 0 ? (
          <div
            style={{
              padding: "24px",
              background: "#f8fafc",
              borderRadius: "12px",
              textAlign: "center",
              color: "#64748b",
            }}
          >
            No administrative documents found.
          </div>
        ) : (
          <div style={{ overflowX: "auto" }}>
            <table className="table">
              <thead>
                <tr>
                  <th>Title</th>
                  <th>Category</th>
                  <th>Version</th>
                  <th>File</th>
                  <th>Uploaded By</th>
                  <th>Date</th>
                  <th>Actions</th>
                </tr>
              </thead>

              <tbody>
                {documents.map((doc) => (
                  <tr key={doc.id}>
                    <td>
                      <strong>{doc.title}</strong>
                      {doc.description ? (
                        <div style={{ color: "#64748b", fontSize: "13px" }}>
                          {doc.description}
                        </div>
                      ) : null}
                    </td>

                    <td>
                      <span className="badge">
                        {String(doc.category || "").replace("_", " ")}
                      </span>
                    </td>

                    <td>v{doc.version}</td>
                    <td>{doc.original_filename}</td>
                    <td>{doc.uploaded_by_name || "-"}</td>
                    <td>{formatDate(doc.created_at)}</td>

                    <td>
                      <button
                        className="btn btn-secondary"
                        onClick={() => downloadDocument(doc)}
                        style={{ marginRight: "8px" }}
                      >
                        Download
                      </button>

                      <button
                        className="btn btn-danger"
                        onClick={() => deleteDocument(doc)}
                      >
                        Delete
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}