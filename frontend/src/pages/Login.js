import React, { useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import api from "../api";
import "../App.css";
import { DotLottieReact } from "@lottiefiles/dotlottie-react";

const Login = ({ onLogin }) => {
  const [username, setUsername] = useState(""); // username OR email
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const navigate = useNavigate();
  const submittedRef = useRef(false); // prevent double submits

  const extractErr = (err) => {
    const status = err?.response?.status;
    const data = err?.response?.data;
    // FastAPI common shapes: detail (string | list[{msg}]) or message
    const detailList =
      Array.isArray(data?.detail) ? data.detail.map((x) => x?.msg).filter(Boolean).join(", ") : null;

    return (
      detailList ||
      data?.detail ||
      data?.message ||
      (status === 401 ? "Invalid username/email or password" : null) ||
      err?.message ||
      "Login failed"
    );
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (submittedRef.current || busy) return; // guard
    setError("");

    const u = (username || "").trim();
    if (!u || !password) {
      setError("Please enter username/email and password");
      return;
    }

    setBusy(true);
    submittedRef.current = true;

    try {
      // --- STEP 1: Login (authoritative)
      const { data } = await api.post(
        "/auth/login",
        { username: u, password },
        { headers: { "Content-Type": "application/json" } }
      );

      const token = data?.access_token || data?.token;
      if (!token) throw new Error("No token returned by server");

      // Persist token for subsequent calls
      localStorage.setItem("token", token);
      api.defaults.headers.common.Authorization = `Bearer ${token}`;

      // --- STEP 2: Try to fetch /auth/me (non-fatal)
      try {
        const meResp = await api.get("/auth/me", {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (onLogin) {
          try {
            onLogin(meResp.data);
          } catch (onLoginErr) {
            // Don't block navigation if parent handler throws
            // eslint-disable-next-line no-console
            console.warn("onLogin handler error:", onLoginErr);
          }
        }
      } catch (meErr) {
        // Do NOT show "Login failed" here—login already succeeded.
        // eslint-disable-next-line no-console
        console.warn("Non-fatal /auth/me error:", meErr?.response?.status, meErr?.response?.data || meErr?.message);
      }

      // Navigate even if /auth/me failed; token is saved and app can rehydrate on load
      navigate("/", { replace: true });
    } catch (err) {
      // Only show error if the LOGIN step failed
      const msg = extractErr(err);
      setError(msg);
      submittedRef.current = false; // allow retry
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="login-container">
      <div className="login-animation">
        <DotLottieReact
          src="https://lottie.host/8e27a9ca-5930-40a4-b5dc-f9e769ad09b2/2JJ5qDWACb.lottie"
          loop
          autoplay
          className="login-lottie"
        />
      </div>

      <div className="login-card">
        <div className="login-header">
          <h1 className="login-title">AIR QA Portal</h1>
        <p className="login-subtitle">Sign in to continue</p>
        </div>

        {error && <div className="error-message">{error}</div>}

        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label className="form-label">USERNAME / EMAIL</label>
            <input
              className="form-input"
              placeholder="Enter username or email"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              autoComplete="username"
              disabled={busy}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !busy) handleSubmit(e);
              }}
            />
          </div>

          <div className="form-group">
            <label className="form-label">PASSWORD</label>
            <input
              className="form-input"
              type="password"
              placeholder="Enter password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="current-password"
              disabled={busy}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !busy) handleSubmit(e);
              }}
            />
          </div>

          <button className="btn-primary" type="submit" disabled={busy}>
            {busy ? "Signing in..." : "Login"}
          </button>
        </form>
      </div>
    </div>
  );
};

export default Login;
