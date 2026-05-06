// src/api.js
import axios from "axios";

// CRA does NOT support import.meta.env, so only use REACT_APP_ vars
const API_BASE =
  process.env.REACT_APP_API_URL ||
  "http://localhost:8000";

const api = axios.create({
  baseURL: API_BASE,
  withCredentials: false,
});

// Attach token automatically on each request
api.interceptors.request.use((config) => {
  const token = localStorage.getItem("token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }

  if (process.env.NODE_ENV !== "production") {
    console.log("API REQUEST ->", `${config.baseURL}${config.url}`);
  }

  return config;
});
export const fetchCourseAssessments = (courseId) =>
  api.get(`/courses/${courseId}/assessments`);

export const createAssessment = (courseId, data) =>
  api.post(`/courses/${courseId}/assessments`, data);

export const fetchAssessment = (assessmentId) =>
  api.get(`/assessments/${assessmentId}`);

export const updateAssessment = (assessmentId, data) =>
  api.put(`/assessments/${assessmentId}`, data);

// Submissions
export const bulkUploadMarks = (assessmentId, file) => {
  const formData = new FormData();
  formData.append("file", file);
  return api.post(`/assessments/${assessmentId}/submissions/bulk-upload`, formData);
};

export const uploadSolutionFile = (assessmentId, regNo, file) => {
  const formData = new FormData();
  formData.append("reg_no", regNo);
  formData.append("file", file);
  return api.post(`/assessments/${assessmentId}/submissions/file`, formData);
};

// Grading Audit
export const runGradingAudit = (assessmentId) =>
  api.post(`/assessments/${assessmentId}/run-grading-audit`);

export const getGradingAudit = (assessmentId) =>
  api.get(`/assessments/${assessmentId}/grading-audit`);

export default api;
