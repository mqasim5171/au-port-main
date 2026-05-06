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


export default api;
