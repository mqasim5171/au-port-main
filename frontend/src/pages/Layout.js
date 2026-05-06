import React, { useEffect, useMemo, useState } from "react";
import { Outlet, Link, useLocation, useNavigate } from "react-router-dom";
import {
  HomeIcon,
  DocumentCheckIcon,
  ChatBubbleLeftRightIcon,
  LightBulbIcon,
  DocumentTextIcon,
  ArrowRightOnRectangleIcon,
  ChartBarIcon,
  Cog6ToothIcon,
  AcademicCapIcon,
  ArrowUpTrayIcon,
  ClipboardDocumentListIcon,
  ShieldCheckIcon,
  ScaleIcon,
  FireIcon,
} from "@heroicons/react/24/outline";

import api from "../api";
import "../App.css";

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

function hasRole(user, roles = []) {
  if (!roles.length) return true;
  const role = normalizeRole(user?.role);
  return roles.map(normalizeRole).includes(role);
}

const Layout = ({ user: userProp, onLogout }) => {
  const location = useLocation();
  const navigate = useNavigate();

  const [user, setUser] = useState(userProp || null);

  useEffect(() => {
    const token = localStorage.getItem("token");

    if (!token) {
      navigate("/login");
      return;
    }

    if (userProp) {
      setUser(userProp);
      return;
    }

    api
      .get("/auth/me")
      .then((res) => setUser(res.data))
      .catch(() => {
        localStorage.removeItem("token");
        delete api.defaults.headers.common.Authorization;
        navigate("/login");
      });
  }, [userProp, navigate]);

  const navigation = useMemo(() => {
    const links = [
      {
        name: "Dashboard",
        href: "/dashboard",
        icon: HomeIcon,
        roles: [],
      },
      {
        name: "Analytics",
        href: "/analytics",
        icon: ChartBarIcon,
        roles: ["admin", "qec", "hod", "course_lead"],
      },
      {
        name: "Admin",
        href: "/admin",
        icon: Cog6ToothIcon,
        roles: ["admin"],
      },

      // Academic upload/teacher work:
      // Admin/QEC/HOD should not see these in sidebar.
      {
        name: "Course Guide",
        href: "/course-guide",
        icon: AcademicCapIcon,
        roles: ["course_lead"],
      },
      {
        name: "Weekly Upload",
        href: "/weekly-upload",
        icon: ArrowUpTrayIcon,
        roles: ["course_lead", "faculty"],
      },
      {
        name: "Assessments",
        href: "/assessments",
        icon: ClipboardDocumentListIcon,
        roles: ["course_lead", "faculty"],
      },

      // QA/monitoring/reporting areas:
      {
        name: "CLO Alignment",
        href: "/clo-alignment",
        icon: DocumentCheckIcon,
        roles: ["admin", "qec", "hod", "course_lead", "faculty"],
      },
      {
        name: "CLO Heatmap",
        href: "/heatmap",
        icon: FireIcon,
        roles: ["admin", "qec", "hod", "course_lead"],
      },
      {
        name: "Grading Fairness",
        href: "/fairness",
        icon: ScaleIcon,
        roles: ["admin", "qec", "hod", "course_lead"],
      },
      {
        name: "Student Feedback",
        href: "/student-feedback",
        icon: ChatBubbleLeftRightIcon,
        roles: ["admin", "qec", "hod", "course_lead"],
      },
      {
        name: "Execution Monitor",
        href: "/execution",
        icon: ChartBarIcon,
        roles: ["admin", "qec", "hod", "course_lead", "faculty"],
      },
      {
        name: "Suggestions",
        href: "/suggestions",
        icon: LightBulbIcon,
        roles: ["admin", "qec", "hod", "course_lead", "faculty"],
      },
      {
        name: "QA Reports",
        href: "/reports",
        icon: DocumentTextIcon,
        roles: ["admin", "qec", "hod", "course_lead"],
      },
      {
        name: "Admin Documents",
        href: "/admin-documents",
        icon: DocumentTextIcon,
        roles: ["admin", "qec", "hod"],
      },
      {
        name: "Explainability",
        href: "/explainability",
        icon: ShieldCheckIcon,
        roles: ["admin", "qec", "hod", "course_lead"],
      },
      {
        name: "Admin QA Control",
        href: "/admin-qa-control",
        icon: ShieldCheckIcon,
        roles: ["admin", "qec"],
      },
    ];

    return links.filter((item) => hasRole(user, item.roles));
  }, [user]);

  const isActive = (href) =>
    location.pathname === href || location.pathname.startsWith(href + "/");

  const handleLogout = () => {
    try {
      if (onLogout) onLogout();
    } catch {}

    localStorage.removeItem("token");
    delete api.defaults.headers.common.Authorization;
    navigate("/login");
  };

  const initial =
    user?.full_name?.trim?.()[0] || user?.username?.trim?.()[0] || "U";

  return (
    <div className="layout-container">
      <div className="sidebar">
        <div className="sidebar-header">
          <h1 className="sidebar-title">AIR QA Portal</h1>
          <p className="sidebar-subtitle">Quality Assurance System</p>
        </div>

        <nav className="sidebar-nav">
          {navigation.map((item) => {
            const Icon = item.icon;

            return (
              <Link
                key={item.name}
                to={item.href}
                className={`nav-item ${isActive(item.href) ? "active" : ""}`}
              >
                <Icon className="nav-icon" />
                {item.name}
              </Link>
            );
          })}
        </nav>

        <div className="sidebar-footer">
          <div className="user-info">
            <div className="user-avatar">{initial}</div>

            <div className="user-details">
              <h4>{user?.full_name || user?.username || "User"}</h4>
              <p>
                {normalizeRole(user?.role) || "user"}
                {user?.department ? ` • ${user.department}` : ""}
              </p>
            </div>
          </div>

          <button onClick={handleLogout} className="btn-logout">
            <ArrowRightOnRectangleIcon
              style={{ width: "16px", marginRight: "8px" }}
            />
            Logout
          </button>
        </div>
      </div>

      <main className="main-content">
        <Outlet />
      </main>
    </div>
  );
};

export default Layout;