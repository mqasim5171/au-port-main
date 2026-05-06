import React, { useState, useEffect } from "react";
import {
  BrowserRouter as Router,
  Routes,
  Route,
  Navigate,
} from "react-router-dom";

import Login from "./pages/Login";
import Layout from "./pages/Layout";
import Dashboard from "./pages/Dashboard";
import AnalyticsDashboard from "./pages/AnalyticsDashboard";
import AdminQAControlPanel from "./pages/AdminQAControlPanel";
import AdminDocuments from "./pages/AdminDocuments";
import CLOAlignment from "./pages/CLOAlignment";
import StudentFeedback from "./pages/StudentFeedback";
import Suggestions from "./pages/Suggestions";
import Reports from "./pages/Reports";
import CourseExecutionMonitor from "./pages/CourseExecutionMonitor";
import Admin from "./pages/Admin";
import CourseGuideUpload from "./pages/CourseGuideUpload";
import WeeklyUpload from "./pages/WeeklyUpload";
import GradingFairness from "./pages/GradingFairness";
import CLOHeatmap from "./pages/CLOHeatmap";
import AuditLogs from "./pages/AuditLogs";
import Explainability from "./pages/Explainability";
import Assessments from "./pages/Assessments";
import AssessmentDetail from "./pages/AssessmentsDetail";

import api from "./api";

const ROLE_ALIASES = {
  administrator: "admin",
  superadmin: "admin",
  "qec officer": "qec",
  "quality officer": "qec",
  "course lead": "course_lead",
  "faculty member": "faculty",
  instructor: "faculty",
};

function normalizeRole(role) {
  const r = String(role || "").trim().toLowerCase();
  return ROLE_ALIASES[r] || r;
}

function canAccess(user, allowedRoles = []) {
  if (!allowedRoles.length) return true;
  const role = normalizeRole(user?.role);
  return allowedRoles.map(normalizeRole).includes(role);
}

function ProtectedRoute({ user, allowedRoles, children }) {
  if (!user) return <Navigate to="/login" replace />;

  if (!canAccess(user, allowedRoles)) {
    return <Navigate to="/dashboard" replace />;
  }

  return children;
}

function App() {
  const [user, setUser] = useState(null);
  const [bootstrapped, setBootstrapped] = useState(false);

  useEffect(() => {
    const token = localStorage.getItem("token");

    if (!token) {
      setBootstrapped(true);
      return;
    }

    api.defaults.headers.common.Authorization = `Bearer ${token}`;

    (async () => {
      try {
        const me = await api.get("/auth/me", {
          headers: { Authorization: `Bearer ${token}` },
        });

        setUser(me.data);
      } catch {
        localStorage.removeItem("token");
        delete api.defaults.headers.common.Authorization;
        setUser(null);
      } finally {
        setBootstrapped(true);
      }
    })();
  }, []);

  const handleLogin = (me) => {
    setUser(me);
  };

  const handleLogout = () => {
    setUser(null);
    localStorage.removeItem("token");
    delete api.defaults.headers.common.Authorization;
  };

  if (!bootstrapped) return null;

  return (
    <Router>
      <Routes>
        {!user ? (
          <>
            <Route path="/login" element={<Login onLogin={handleLogin} />} />
            <Route path="*" element={<Navigate to="/login" replace />} />
          </>
        ) : (
          <>
            <Route element={<Layout user={user} onLogout={handleLogout} />}>
              <Route path="/dashboard" element={<Dashboard user={user} />} />

              <Route
                path="/analytics"
                element={
                  <ProtectedRoute
                    user={user}
                    allowedRoles={["admin", "qec", "hod", "course_lead"]}
                  >
                    <AnalyticsDashboard user={user} />
                  </ProtectedRoute>
                }
              />

              <Route
                path="/admin"
                element={
                  <ProtectedRoute user={user} allowedRoles={["admin"]}>
                    <Admin user={user} />
                  </ProtectedRoute>
                }
              />

              <Route
                path="/admin-qa-control"
                element={
                  <ProtectedRoute user={user} allowedRoles={["admin", "qec"]}>
                    <AdminQAControlPanel user={user} />
                  </ProtectedRoute>
                }
              />

              <Route
                path="/admin-documents"
                element={
                  <ProtectedRoute
                    user={user}
                    allowedRoles={["admin", "qec", "hod"]}
                  >
                    <AdminDocuments user={user} />
                  </ProtectedRoute>
                }
              />

              {/* Course Guide upload is academic content work.
                  Only assigned Course Lead should access this page. */}
              <Route
                path="/course-guide"
                element={
                  <ProtectedRoute user={user} allowedRoles={["course_lead"]}>
                    <CourseGuideUpload user={user} />
                  </ProtectedRoute>
                }
              />

              {/* Weekly Upload is teacher/course work.
                  Admin/QEC/HOD should not upload teacher weekly material. */}
              <Route
                path="/weekly-upload"
                element={
                  <ProtectedRoute
                    user={user}
                    allowedRoles={["course_lead", "faculty"]}
                  >
                    <WeeklyUpload user={user} />
                  </ProtectedRoute>
                }
              />

              {/* Assessment creation/upload is teacher/course work.
                  Admin/QEC/HOD should not upload quizzes/assignments. */}
              <Route
                path="/assessments"
                element={
                  <ProtectedRoute
                    user={user}
                    allowedRoles={["course_lead", "faculty"]}
                  >
                    <Assessments user={user} />
                  </ProtectedRoute>
                }
              />

              <Route
                path="/assessments/:id"
                element={
                  <ProtectedRoute
                    user={user}
                    allowedRoles={["course_lead", "faculty"]}
                  >
                    <AssessmentDetail user={user} />
                  </ProtectedRoute>
                }
              />

              <Route
                path="/clo-alignment"
                element={
                  <ProtectedRoute
                    user={user}
                    allowedRoles={[
                      "admin",
                      "qec",
                      "hod",
                      "course_lead",
                      "faculty",
                    ]}
                  >
                    <CLOAlignment user={user} />
                  </ProtectedRoute>
                }
              />

              <Route
                path="/heatmap"
                element={
                  <ProtectedRoute
                    user={user}
                    allowedRoles={["admin", "qec", "hod", "course_lead"]}
                  >
                    <CLOHeatmap user={user} />
                  </ProtectedRoute>
                }
              />

              <Route
                path="/fairness"
                element={
                  <ProtectedRoute
                    user={user}
                    allowedRoles={["admin", "qec", "hod", "course_lead"]}
                  >
                    <GradingFairness user={user} />
                  </ProtectedRoute>
                }
              />

              <Route
                path="/student-feedback"
                element={
                  <ProtectedRoute
                    user={user}
                    allowedRoles={["admin", "qec", "hod", "course_lead"]}
                  >
                    <StudentFeedback user={user} />
                  </ProtectedRoute>
                }
              />

              <Route
                path="/execution"
                element={
                  <ProtectedRoute
                    user={user}
                    allowedRoles={[
                      "admin",
                      "qec",
                      "hod",
                      "course_lead",
                      "faculty",
                    ]}
                  >
                    <CourseExecutionMonitor user={user} />
                  </ProtectedRoute>
                }
              />

              <Route
                path="/suggestions"
                element={
                  <ProtectedRoute
                    user={user}
                    allowedRoles={[
                      "admin",
                      "qec",
                      "hod",
                      "course_lead",
                      "faculty",
                    ]}
                  >
                    <Suggestions user={user} />
                  </ProtectedRoute>
                }
              />

              <Route
                path="/reports"
                element={
                  <ProtectedRoute
                    user={user}
                    allowedRoles={["admin", "qec", "hod", "course_lead"]}
                  >
                    <Reports user={user} />
                  </ProtectedRoute>
                }
              />

              <Route
                path="/audit-logs"
                element={
                  <ProtectedRoute user={user} allowedRoles={["admin", "qec"]}>
                    <AuditLogs user={user} />
                  </ProtectedRoute>
                }
              />

              <Route
                path="/explainability"
                element={
                  <ProtectedRoute
                    user={user}
                    allowedRoles={["admin", "qec", "hod", "course_lead"]}
                  >
                    <Explainability user={user} />
                  </ProtectedRoute>
                }
              />

              <Route path="/" element={<Navigate to="/dashboard" replace />} />
            </Route>

            <Route path="*" element={<Navigate to="/dashboard" replace />} />
          </>
        )}
      </Routes>
    </Router>
  );
}

export default App;