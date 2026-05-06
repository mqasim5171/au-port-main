// frontend/src/pages/Admin.jsx

import React, { useEffect, useMemo, useState } from "react";
import api from "../api";

const styles = {
  page: { display: "grid", gap: 16 },
  headerCard: {
    background: "#fff",
    borderRadius: 14,
    border: "1px solid #e5e7eb",
    padding: 16,
  },
  card: {
    background: "#fff",
    borderRadius: 14,
    border: "1px solid #e5e7eb",
    padding: 16,
  },
  titleRow: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    gap: 10,
    flexWrap: "wrap",
  },
  h2: { margin: 0, fontSize: 22 },
  h3: { margin: 0, fontSize: 18 },
  hint: { marginTop: 6, opacity: 0.75, lineHeight: 1.4 },
  grid: { display: "grid", gap: 10 },
  row: { display: "flex", gap: 10, alignItems: "center", flexWrap: "wrap" },
  input: {
    width: "100%",
    padding: "10px 12px",
    borderRadius: 10,
    border: "1px solid #d1d5db",
    outline: "none",
    boxSizing: "border-box",
  },
  textarea: {
    width: "100%",
    padding: "10px 12px",
    borderRadius: 10,
    border: "1px solid #d1d5db",
    outline: "none",
    minHeight: 90,
    boxSizing: "border-box",
    resize: "vertical",
  },
  select: {
    width: "100%",
    padding: "10px 12px",
    borderRadius: 10,
    border: "1px solid #d1d5db",
    outline: "none",
    background: "#fff",
    boxSizing: "border-box",
  },
  btn: {
    padding: "10px 14px",
    borderRadius: 10,
    border: "1px solid #d1d5db",
    background: "#fff",
    cursor: "pointer",
  },
  btnDanger: {
    padding: "10px 14px",
    borderRadius: 10,
    border: "1px solid #dc2626",
    background: "#dc2626",
    color: "#fff",
    cursor: "pointer",
  },
  btnPrimary: {
    padding: "10px 14px",
    borderRadius: 10,
    border: "1px solid #1d4ed8",
    background: "#2563eb",
    color: "#fff",
    cursor: "pointer",
  },
  chip: {
    display: "inline-block",
    padding: "4px 10px",
    borderRadius: 999,
    border: "1px solid #e5e7eb",
    background: "#f9fafb",
    fontSize: 12,
    opacity: 0.9,
    whiteSpace: "nowrap",
  },
  divider: { height: 1, background: "#e5e7eb", margin: "12px 0" },
  small: { fontSize: 12, opacity: 0.8, lineHeight: 1.4 },
};

function safeParseClos(raw) {
  if (!raw) return [];

  try {
    const data = JSON.parse(raw);

    if (!Array.isArray(data)) return [];

    return data
      .map((x) => {
        if (typeof x === "string") {
          return { code: x, description: "" };
        }

        return {
          code: (x?.code || "").toString(),
          description: (x?.description || "").toString(),
        };
      })
      .filter((c) => c.code || c.description);
  } catch {
    return [];
  }
}

function normalizeRoleLabel(role) {
  const r = (role || "").toString().toLowerCase();

  if (r.includes("course") && r.includes("lead")) return "course_lead";
  if (r.includes("instructor")) return "instructor";
  if (r.includes("faculty")) return "faculty";
  if (r.includes("admin")) return "admin";
  if (r.includes("qec")) return "qec";
  if (r.includes("hod")) return "hod";

  return role || "unknown";
}

function formatUserOption(u) {
  const role = normalizeRoleLabel(u?.role);
  const name = u?.full_name || "Unknown";
  const username = u?.username ? `@${u.username}` : "";

  return `${name} ${username} (${role})`;
}

export default function Admin({ user }) {
  const isAdmin = useMemo(
    () => (user?.role || "").toLowerCase().includes("admin"),
    [user]
  );

  const [courses, setCourses] = useState([]);
  const [instructors, setInstructors] = useState([]);
  const [courseLeads, setCourseLeads] = useState([]);
  const [selectedCourseId, setSelectedCourseId] = useState("");

  const [form, setForm] = useState({
    course_code: "",
    course_name: "",
    semester: "Fall",
    year: "2026",
    department: "",
  });

  const [clos, setClos] = useState([{ code: "CLO1", description: "" }]);

  const [assign, setAssign] = useState({
    instructorId: "",
    courseLeadId: "",
  });

  const [newUser, setNewUser] = useState({
    full_name: "",
    username: "",
    email: "",
    department: "",
    role: "instructor",
    password: "Teacher@12345",
  });

  const [allTeachers, setAllTeachers] = useState([]);
  const [editUserId, setEditUserId] = useState("");
  const [editForm, setEditForm] = useState({
    full_name: "",
    username: "",
    email: "",
    department: "",
    password: "",
  });

  const [editCourseId, setEditCourseId] = useState("");
  const [editCourseForm, setEditCourseForm] = useState({
    course_code: "",
    course_name: "",
    semester: "",
    year: "",
    department: "",
    instructor: "",
    clos: "[]",
  });

  const [savingEdit, setSavingEdit] = useState(false);
  const [savingCourseEdit, setSavingCourseEdit] = useState(false);
  const [loading, setLoading] = useState(false);

  const load = async () => {
    setLoading(true);

    try {
      const [cRes, iRes, lRes] = await Promise.all([
        api.get("/courses"),
        api.get("/admin/users?role=instructor"),
        api.get("/admin/users?role=course_lead"),
      ]);

      const cList = cRes.data || [];
      const instr = iRes.data || [];
      const leads = lRes.data || [];

      setCourses(cList);
      setInstructors(instr);
      setCourseLeads(leads);
      setAllTeachers([...(instr || []), ...(leads || [])]);

      if (!selectedCourseId && cList.length) {
        setSelectedCourseId(cList[0].id);
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (!isAdmin) return;

    load().catch(console.error);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isAdmin]);

  useEffect(() => {
    if (!selectedCourseId) return;

    const course = courses.find((c) => c.id === selectedCourseId);
    const parsed = safeParseClos(course?.clos);

    if (parsed.length) {
      setClos(parsed);
    } else {
      setClos([{ code: "CLO1", description: "" }]);
    }
  }, [selectedCourseId, courses]);

  if (!isAdmin) {
    return (
      <div style={styles.card}>
        <h2 style={styles.h2}>Admin</h2>
        <p style={styles.hint}>You do not have access to this page.</p>
      </div>
    );
  }

  const createCourse = async (e) => {
    e.preventDefault();

    try {
      await api.post("/admin/courses", {
        ...form,
        instructor: "",
        clos: "[]",
      });

      alert("Course created successfully");

      setForm({
        course_code: "",
        course_name: "",
        semester: "Fall",
        year: "2026",
        department: "",
      });

      await load();
    } catch (err) {
      console.error(err);
      alert(err.response?.data?.detail || "Failed to create course");
    }
  };

  const assignStaff = async () => {
    if (!selectedCourseId) {
      alert("Select a course first");
      return;
    }

    try {
      if (assign.instructorId) {
        await api.post(`/admin/courses/${selectedCourseId}/assign`, {
          user_id: assign.instructorId,
          role: "INSTRUCTOR",
        });
      }

      if (assign.courseLeadId) {
        await api.post(`/admin/courses/${selectedCourseId}/assign`, {
          user_id: assign.courseLeadId,
          role: "COURSE_LEAD",
        });
      }

      alert("Staff assigned successfully");
      await load();
    } catch (err) {
      console.error(err);
      alert(err.response?.data?.detail || "Failed to assign staff");
    }
  };

  const saveClos = async () => {
    if (!selectedCourseId) {
      alert("Select a course first");
      return;
    }

    const cleaned = clos
      .map((c) => ({
        code: (c.code || "").trim(),
        description: (c.description || "").trim(),
      }))
      .filter((c) => c.code && c.description);

    try {
      await api.put(`/admin/courses/${selectedCourseId}/clos`, {
        clos: cleaned,
      });

      alert("CLOs saved for this course");
      await load();
    } catch (err) {
      console.error(err);
      alert(err.response?.data?.detail || "Failed to save CLOs");
    }
  };

  const createTeacherUser = async (e) => {
    e.preventDefault();

    try {
      await api.post("/admin/users", {
        full_name: newUser.full_name,
        username: newUser.username,
        email: newUser.email,
        department: newUser.department || null,
        role: newUser.role,
        password: newUser.password,
      });

      alert(`User created successfully. Password: ${newUser.password}`);

      setNewUser({
        full_name: "",
        username: "",
        email: "",
        department: "",
        role: "instructor",
        password: "Teacher@12345",
      });

      await load();
    } catch (err) {
      console.error(err);
      alert(err.response?.data?.detail || "Failed to create user");
    }
  };

  const selectUserForEdit = (id) => {
    setEditUserId(id);

    const u = allTeachers.find((x) => x.id === id);

    if (!u) {
      setEditForm({
        full_name: "",
        username: "",
        email: "",
        department: "",
        password: "",
      });
      return;
    }

    setEditForm({
      full_name: u.full_name || "",
      username: u.username || "",
      email: u.email || "",
      department: u.department || "",
      password: "",
    });
  };

  const saveEditedUser = async () => {
    if (!editUserId) {
      alert("Select a teacher first");
      return;
    }

    if (!editForm.full_name.trim()) {
      alert("Full name is required");
      return;
    }

    if (!editForm.username.trim()) {
      alert("Username is required");
      return;
    }

    if (!editForm.email.trim()) {
      alert("Email is required");
      return;
    }

    const payload = {
      full_name: editForm.full_name.trim(),
      username: editForm.username.trim(),
      email: editForm.email.trim(),
      department: (editForm.department || "").trim() || null,
    };

    if ((editForm.password || "").trim()) {
      payload.password = editForm.password.trim();
    }

    setSavingEdit(true);

    try {
      await api.put(`/admin/users/${editUserId}`, payload);

      alert("User updated successfully");

      setEditUserId("");
      setEditForm({
        full_name: "",
        username: "",
        email: "",
        department: "",
        password: "",
      });

      await load();
    } catch (err) {
      console.error(err);
      alert(err.response?.data?.detail || "Failed to update user");
    } finally {
      setSavingEdit(false);
    }
  };

  const deleteEditedUser = async () => {
    if (!editUserId) {
      alert("Select a teacher first");
      return;
    }

    const selectedUser = allTeachers.find((u) => u.id === editUserId);

    const confirmDelete = window.confirm(
      `Are you sure you want to delete ${
        selectedUser?.full_name || "this user"
      }? Their course assignments will also be removed.`
    );

    if (!confirmDelete) return;

    try {
      await api.delete(`/admin/users/${editUserId}`);

      alert("User deleted successfully");

      setEditUserId("");
      setEditForm({
        full_name: "",
        username: "",
        email: "",
        department: "",
        password: "",
      });

      await load();
    } catch (err) {
      console.error(err);
      alert(err.response?.data?.detail || "Failed to delete user");
    }
  };

  const selectCourseForEdit = (id) => {
    setEditCourseId(id);

    const c = courses.find((x) => x.id === id);

    if (!c) {
      setEditCourseForm({
        course_code: "",
        course_name: "",
        semester: "",
        year: "",
        department: "",
        instructor: "",
        clos: "[]",
      });
      return;
    }

    setEditCourseForm({
      course_code: c.course_code || "",
      course_name: c.course_name || "",
      semester: c.semester || "",
      year: c.year || "",
      department: c.department || "",
      instructor: c.instructor || "",
      clos: c.clos || "[]",
    });
  };

  const saveEditedCourse = async () => {
    if (!editCourseId) {
      alert("Select a course first");
      return;
    }

    if (!editCourseForm.course_code.trim()) {
      alert("Course code is required");
      return;
    }

    if (!editCourseForm.course_name.trim()) {
      alert("Course name is required");
      return;
    }

    if (!editCourseForm.department.trim()) {
      alert("Department is required");
      return;
    }

    const payload = {
      course_code: editCourseForm.course_code.trim(),
      course_name: editCourseForm.course_name.trim(),
      semester: editCourseForm.semester.trim(),
      year: editCourseForm.year.trim(),
      department: editCourseForm.department.trim(),
      instructor: editCourseForm.instructor.trim(),
      clos: editCourseForm.clos || "[]",
    };

    setSavingCourseEdit(true);

    try {
      await api.put(`/admin/courses/${editCourseId}`, payload);

      alert("Course updated successfully");

      await load();
    } catch (err) {
      console.error(err);
      alert(err.response?.data?.detail || "Failed to update course");
    } finally {
      setSavingCourseEdit(false);
    }
  };

  const deleteEditedCourse = async () => {
    if (!editCourseId) {
      alert("Select a course first");
      return;
    }

    const selected = courses.find((c) => c.id === editCourseId);

    const confirmDelete = window.confirm(
      `Are you sure you want to delete ${
        selected?.course_code || "this course"
      }? Its staff assignments will also be removed.`
    );

    if (!confirmDelete) return;

    try {
      await api.delete(`/admin/courses/${editCourseId}`);

      alert("Course deleted successfully");

      setEditCourseId("");
      setEditCourseForm({
        course_code: "",
        course_name: "",
        semester: "",
        year: "",
        department: "",
        instructor: "",
        clos: "[]",
      });

      await load();
    } catch (err) {
      console.error(err);
      alert(err.response?.data?.detail || "Failed to delete course");
    }
  };

  const selectedCourse = courses.find((c) => c.id === selectedCourseId);

  return (
    <div style={styles.page}>
      <div style={styles.headerCard}>
        <div style={styles.titleRow}>
          <h2 style={styles.h2}>Admin Panel</h2>
          <span style={styles.chip}>Role: {user?.role || "admin"}</span>
        </div>

        <p style={styles.hint}>
          Create courses, create teacher users, edit/delete records, assign
          staff, and set course-specific CLOs.
        </p>

        {loading && (
          <div style={{ ...styles.small, marginTop: 8 }}>
            Loading admin data...
          </div>
        )}
      </div>

      {/* CREATE TEACHER USER */}
      <div style={styles.card}>
        <div style={styles.titleRow}>
          <h3 style={styles.h3}>Create Teacher User</h3>
          <span style={styles.chip}>Instructor / Course Lead</span>
        </div>

        <p style={styles.hint}>
          Create Instructor or Course Lead accounts. After creation, assign them
          to specific courses.
        </p>

        <form onSubmit={createTeacherUser} style={styles.grid}>
          <div style={styles.row}>
            <input
              style={styles.input}
              placeholder="Full Name"
              value={newUser.full_name}
              onChange={(e) =>
                setNewUser({ ...newUser, full_name: e.target.value })
              }
              required
            />

            <select
              style={{ ...styles.select, width: 220 }}
              value={newUser.role}
              onChange={(e) =>
                setNewUser({ ...newUser, role: e.target.value })
              }
            >
              <option value="instructor">Instructor</option>
              <option value="course_lead">Course Lead</option>
            </select>
          </div>

          <div style={styles.row}>
            <input
              style={styles.input}
              placeholder="Username"
              value={newUser.username}
              onChange={(e) =>
                setNewUser({ ...newUser, username: e.target.value })
              }
              required
            />

            <input
              style={styles.input}
              placeholder="Email"
              type="email"
              value={newUser.email}
              onChange={(e) =>
                setNewUser({ ...newUser, email: e.target.value })
              }
              required
            />
          </div>

          <div style={styles.row}>
            <input
              style={styles.input}
              placeholder="Department"
              value={newUser.department}
              onChange={(e) =>
                setNewUser({ ...newUser, department: e.target.value })
              }
            />

            <input
              style={styles.input}
              placeholder="Password"
              value={newUser.password}
              onChange={(e) =>
                setNewUser({ ...newUser, password: e.target.value })
              }
              required
            />
          </div>

          <button style={styles.btnPrimary} type="submit">
            Create Teacher
          </button>
        </form>
      </div>

      {/* EDIT / DELETE TEACHER */}
      <div style={styles.card}>
        <div style={styles.titleRow}>
          <h3 style={styles.h3}>Edit / Delete Teacher or Course Lead</h3>
          <span style={styles.chip}>Admin Only</span>
        </div>

        <p style={styles.hint}>
          Update teacher details, reset password, or delete a non-admin account.
        </p>

        <div style={styles.grid}>
          <select
            style={styles.select}
            value={editUserId}
            onChange={(e) => selectUserForEdit(e.target.value)}
          >
            <option value="">Select Teacher…</option>
            {allTeachers.map((u) => (
              <option key={u.id} value={u.id}>
                {formatUserOption(u)}
              </option>
            ))}
          </select>

          <div style={styles.row}>
            <input
              style={styles.input}
              placeholder="Full Name"
              value={editForm.full_name}
              onChange={(e) =>
                setEditForm({ ...editForm, full_name: e.target.value })
              }
            />

            <input
              style={styles.input}
              placeholder="Username"
              value={editForm.username}
              onChange={(e) =>
                setEditForm({ ...editForm, username: e.target.value })
              }
            />
          </div>

          <div style={styles.row}>
            <input
              style={styles.input}
              placeholder="Email"
              type="email"
              value={editForm.email}
              onChange={(e) =>
                setEditForm({ ...editForm, email: e.target.value })
              }
            />

            <input
              style={styles.input}
              placeholder="Department"
              value={editForm.department}
              onChange={(e) =>
                setEditForm({ ...editForm, department: e.target.value })
              }
            />
          </div>

          <input
            style={styles.input}
            type="password"
            placeholder="New Password Optional"
            value={editForm.password}
            onChange={(e) =>
              setEditForm({ ...editForm, password: e.target.value })
            }
          />

          <div style={styles.row}>
            <button
              style={styles.btnPrimary}
              onClick={saveEditedUser}
              type="button"
              disabled={savingEdit}
            >
              {savingEdit ? "Saving..." : "Save User Changes"}
            </button>

            <button
              style={styles.btnDanger}
              onClick={deleteEditedUser}
              type="button"
              disabled={savingEdit}
            >
              Delete User
            </button>

            <button
              style={styles.btn}
              type="button"
              onClick={() => {
                setEditUserId("");
                setEditForm({
                  full_name: "",
                  username: "",
                  email: "",
                  department: "",
                  password: "",
                });
              }}
              disabled={savingEdit}
            >
              Clear
            </button>
          </div>

          <div style={styles.small}>
            Password reset is optional. If left empty, the old password remains
            unchanged.
          </div>
        </div>
      </div>

      {/* CREATE COURSE */}
      <div style={styles.card}>
        <h3 style={styles.h3}>Create Course</h3>

        <form onSubmit={createCourse} style={styles.grid}>
          <input
            style={styles.input}
            placeholder="Course Code e.g. CS-401"
            value={form.course_code}
            onChange={(e) => setForm({ ...form, course_code: e.target.value })}
            required
          />

          <input
            style={styles.input}
            placeholder="Course Name"
            value={form.course_name}
            onChange={(e) => setForm({ ...form, course_name: e.target.value })}
            required
          />

          <input
            style={styles.input}
            placeholder="Department"
            value={form.department}
            onChange={(e) => setForm({ ...form, department: e.target.value })}
            required
          />

          <div style={styles.row}>
            <input
              style={styles.input}
              placeholder="Semester"
              value={form.semester}
              onChange={(e) => setForm({ ...form, semester: e.target.value })}
            />

            <input
              style={styles.input}
              placeholder="Year"
              value={form.year}
              onChange={(e) => setForm({ ...form, year: e.target.value })}
            />
          </div>

          <button style={styles.btnPrimary} type="submit">
            Create Course
          </button>
        </form>
      </div>

      {/* EDIT / DELETE COURSE */}
      <div style={styles.card}>
        <div style={styles.titleRow}>
          <h3 style={styles.h3}>Edit / Delete Course</h3>
          <span style={styles.chip}>Course Management</span>
        </div>

        <p style={styles.hint}>
          Update course information or delete a course. Deleting a course will
          also remove staff assignments.
        </p>

        <div style={styles.grid}>
          <select
            style={styles.select}
            value={editCourseId}
            onChange={(e) => selectCourseForEdit(e.target.value)}
          >
            <option value="">Select Course…</option>
            {courses.map((c) => (
              <option key={c.id} value={c.id}>
                {c.course_code} — {c.course_name}
              </option>
            ))}
          </select>

          <div style={styles.row}>
            <input
              style={styles.input}
              placeholder="Course Code"
              value={editCourseForm.course_code}
              onChange={(e) =>
                setEditCourseForm({
                  ...editCourseForm,
                  course_code: e.target.value,
                })
              }
            />

            <input
              style={styles.input}
              placeholder="Course Name"
              value={editCourseForm.course_name}
              onChange={(e) =>
                setEditCourseForm({
                  ...editCourseForm,
                  course_name: e.target.value,
                })
              }
            />
          </div>

          <div style={styles.row}>
            <input
              style={styles.input}
              placeholder="Semester"
              value={editCourseForm.semester}
              onChange={(e) =>
                setEditCourseForm({
                  ...editCourseForm,
                  semester: e.target.value,
                })
              }
            />

            <input
              style={styles.input}
              placeholder="Year"
              value={editCourseForm.year}
              onChange={(e) =>
                setEditCourseForm({
                  ...editCourseForm,
                  year: e.target.value,
                })
              }
            />
          </div>

          <div style={styles.row}>
            <input
              style={styles.input}
              placeholder="Department"
              value={editCourseForm.department}
              onChange={(e) =>
                setEditCourseForm({
                  ...editCourseForm,
                  department: e.target.value,
                })
              }
            />

            <input
              style={styles.input}
              placeholder="Instructor Display Name"
              value={editCourseForm.instructor}
              onChange={(e) =>
                setEditCourseForm({
                  ...editCourseForm,
                  instructor: e.target.value,
                })
              }
            />
          </div>

          <textarea
            style={styles.textarea}
            placeholder='CLO JSON e.g. [{"code":"CLO1","description":"..."}]'
            value={editCourseForm.clos}
            onChange={(e) =>
              setEditCourseForm({
                ...editCourseForm,
                clos: e.target.value,
              })
            }
          />

          <div style={styles.row}>
            <button
              style={styles.btnPrimary}
              onClick={saveEditedCourse}
              type="button"
              disabled={savingCourseEdit}
            >
              {savingCourseEdit ? "Saving..." : "Save Course Changes"}
            </button>

            <button
              style={styles.btnDanger}
              onClick={deleteEditedCourse}
              type="button"
              disabled={savingCourseEdit}
            >
              Delete Course
            </button>

            <button
              style={styles.btn}
              type="button"
              onClick={() => {
                setEditCourseId("");
                setEditCourseForm({
                  course_code: "",
                  course_name: "",
                  semester: "",
                  year: "",
                  department: "",
                  instructor: "",
                  clos: "[]",
                });
              }}
              disabled={savingCourseEdit}
            >
              Clear
            </button>
          </div>
        </div>
      </div>

      {/* ASSIGN STAFF */}
      <div style={styles.card}>
        <h3 style={styles.h3}>Assign Staff</h3>

        <div style={styles.grid}>
          <select
            style={styles.select}
            value={selectedCourseId}
            onChange={(e) => setSelectedCourseId(e.target.value)}
          >
            <option value="">Select course…</option>
            {courses.map((c) => (
              <option key={c.id} value={c.id}>
                {c.course_code} — {c.course_name}
              </option>
            ))}
          </select>

          <div style={styles.row}>
            <select
              style={styles.select}
              value={assign.instructorId}
              onChange={(e) =>
                setAssign({ ...assign, instructorId: e.target.value })
              }
            >
              <option value="">Assign Instructor…</option>
              {instructors.map((u) => (
                <option key={u.id} value={u.id}>
                  {u.full_name} ({u.username})
                </option>
              ))}
            </select>

            <select
              style={styles.select}
              value={assign.courseLeadId}
              onChange={(e) =>
                setAssign({ ...assign, courseLeadId: e.target.value })
              }
            >
              <option value="">Assign Course Lead…</option>
              {courseLeads.map((u) => (
                <option key={u.id} value={u.id}>
                  {u.full_name} ({u.username})
                </option>
              ))}
            </select>
          </div>

          <button style={styles.btnPrimary} onClick={assignStaff} type="button">
            Save Assignments
          </button>

          {selectedCourse ? (
            <div style={styles.small}>
              Selected: <b>{selectedCourse.course_code}</b> —{" "}
              {selectedCourse.course_name}
            </div>
          ) : null}
        </div>
      </div>

      {/* SET CLOS */}
      <div style={styles.card}>
        <div style={styles.titleRow}>
          <h3 style={styles.h3}>Set CLOs Course-Specific</h3>
          <span style={styles.chip}>Used in CLO Alignment</span>
        </div>

        <p style={styles.hint}>
          Select a course, then add CLOs. These are stored in courses.clos as
          JSON and used by alignment.
        </p>

        <select
          style={styles.select}
          value={selectedCourseId}
          onChange={(e) => setSelectedCourseId(e.target.value)}
        >
          <option value="">Select course…</option>
          {courses.map((c) => (
            <option key={c.id} value={c.id}>
              {c.course_code} — {c.course_name}
            </option>
          ))}
        </select>

        <div style={styles.divider} />

        {clos.map((c, idx) => (
          <div key={idx} style={{ ...styles.row, marginBottom: 8 }}>
            <input
              style={{ ...styles.input, width: 130 }}
              placeholder="CLO1"
              value={c.code}
              onChange={(e) => {
                const next = [...clos];
                next[idx] = { ...next[idx], code: e.target.value };
                setClos(next);
              }}
            />

            <input
              style={styles.input}
              placeholder="Description"
              value={c.description}
              onChange={(e) => {
                const next = [...clos];
                next[idx] = {
                  ...next[idx],
                  description: e.target.value,
                };
                setClos(next);
              }}
            />

            <button
              style={styles.btn}
              onClick={() => setClos(clos.filter((_, i) => i !== idx))}
              type="button"
              title="Remove"
            >
              ✕
            </button>
          </div>
        ))}

        <div style={styles.row}>
          <button
            style={styles.btn}
            type="button"
            onClick={() =>
              setClos([
                ...clos,
                {
                  code: `CLO${clos.length + 1}`,
                  description: "",
                },
              ])
            }
          >
            + Add CLO
          </button>

          <button style={styles.btnPrimary} type="button" onClick={saveClos}>
            Save CLOs
          </button>
        </div>

        <div style={{ ...styles.small, marginTop: 10 }}>
          Tip: Keep CLO code like <b>CLO1</b>, <b>CLO2</b>, and write meaningful
          descriptions.
        </div>
      </div>
    </div>
  );
}