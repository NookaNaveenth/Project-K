import React, { useState, useEffect } from "react";
import { getStatus, formatStatus, statusClass } from "../utils/formatters";
import ReportPreviewModal from "../components/modals/ReportPreviewModal";
import {
  STANDARDIZED_DEPARTMENTS,
  STANDARDIZED_PRACTICES,
  SOFTWARE_SERVICES_PRACTICES,
  getTeamsForDepartment,
} from "../utils/constants";

export default function AttendancePage({
  dateAttendanceError,
  selectedDateText,
  selectedDate,
  setSelectedDate,
  dateAttendanceLoading,
  sortedAttendanceEmployees,
  getAttendance,
  openEditShift,
  openEmployeeHistory,
  openReportChooser,
  deleteEmployee,
  deletingEmployeeId,
  search,
  setSearch,
  loadAttendanceByDate,
  handleAttendanceDateChange,
  auth,
  deptFilter,
  setDeptFilter,
  practiceFilter = "ALL",
  setPracticeFilter,
  teamFilter = "ALL",
  setTeamFilter,
  subPracticeFilter = "ALL",
  setSubPracticeFilter,
  allDepartments = STANDARDIZED_DEPARTMENTS,
  allPractices = STANDARDIZED_PRACTICES,
  allSubPractices = [],
  locationFilter,
  setLocationFilter,
  allLocations = [],
  statusFilter,
  setStatusFilter,
  API_URL,
  authFetch,
}) {
  const isHr = auth?.role === "hr";
  const [schedulerStatus, setSchedulerStatus] = useState(null);
  const [schedulerLoading, setSchedulerLoading] = useState(false);
  const [previewModalOpen, setPreviewModalOpen] = useState(false);
  const [previewReportType, setPreviewReportType] = useState("arrival");
  const [profilePics, setProfilePics] = useState({});
  const [imgErrors, setImgErrors] = useState({});
  const [bufferModalOpen, setBufferModalOpen] = useState(false);
  const [currentBufferMinutes, setCurrentBufferMinutes] = useState(0);
  const [bufferSelection, setBufferSelection] = useState("0");
  const [customBufferMinutes, setCustomBufferMinutes] = useState("");
  const [bufferLoading, setBufferLoading] = useState(false);
  const [bufferMessage, setBufferMessage] = useState(null);

  // Load persisted buffer time from backend
  useEffect(() => {
    fetch(`${API_URL || ""}/attendance/buffer-time`)
      .then((res) => (res.ok ? res.json() : null))
      .then((data) => {
        if (data && data.success) {
          const bm = Number(data.buffer_minutes || 0);
          setCurrentBufferMinutes(bm);
          if ([5, 10, 15].includes(bm)) {
            setBufferSelection(String(bm));
          } else if (bm > 0) {
            setBufferSelection("custom");
            setCustomBufferMinutes(String(bm));
          } else {
            setBufferSelection("0");
          }
        }
      })
      .catch(() => {});
  }, [API_URL]);

  const handleSaveBuffer = async (selectedOption, customVal) => {
    const sel = selectedOption !== undefined ? selectedOption : bufferSelection;
    let mins = 0;
    if (sel === "custom") {
      const cVal = customVal !== undefined ? customVal : customBufferMinutes;
      mins = Math.max(0, parseInt(cVal || "0", 10));
    } else {
      mins = parseInt(sel, 10);
    }

    setBufferLoading(true);
    setBufferMessage(null);
    try {
      const res = await fetch(`${API_URL || ""}/attendance/buffer-time`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ buffer_minutes: mins }),
      });
      if (res.ok) {
        const data = await res.json();
        setCurrentBufferMinutes(data.buffer_minutes);
        setBufferMessage({ type: "success", text: `Buffer time set to ${data.buffer_minutes} minutes.` });
        if (loadAttendanceByDate) {
          loadAttendanceByDate(selectedDate);
        }
        setTimeout(() => setBufferModalOpen(false), 700);
      }
    } catch (err) {
      setBufferMessage({ type: "error", text: "Failed to update buffer time." });
    } finally {
      setBufferLoading(false);
    }
  };


  // Dynamically fetch mock Hubble profile pictures for employees if not already attached
  useEffect(() => {
    if (!sortedAttendanceEmployees || sortedAttendanceEmployees.length === 0) return;
    const baseUrl = API_URL || "";
    sortedAttendanceEmployees.forEach((emp) => {
      const empId = String(emp.employee_id || emp.id || emp.login_id || "");
      if (!empId) return;
      if (emp.profile_pic || emp.profilePic || profilePics[empId] || imgErrors[empId]) return;

      const fetchUrl = `${baseUrl}/mock-hubble/profile-picture/${encodeURIComponent(empId)}`;
      const doFetch = authFetch ? authFetch(fetchUrl) : fetch(fetchUrl);
      doFetch
        .then((res) => (res.ok ? res.json() : null))
        .then((data) => {
          if (data && data.profilePic) {
            setProfilePics((prev) => ({ ...prev, [empId]: data.profilePic }));
          }
        })
        .catch(() => {
          // Gracefully fallback to initials on error
        });
    });
  }, [sortedAttendanceEmployees, profilePics, imgErrors, API_URL, authFetch]);

  // Dependent dropdown configuration
  const isSoftwareServices = deptFilter === "Software Services";
  const practiceOptions = isSoftwareServices ? SOFTWARE_SERVICES_PRACTICES : [];
  const isPracticeDisabled = !isSoftwareServices;

  const availableTeams = getTeamsForDepartment(deptFilter);
  const isTeamDisabled =
    !deptFilter ||
    deptFilter === "ALL" ||
    deptFilter === "Executive Board" ||
    isSoftwareServices ||
    availableTeams.length === 0;

  const handleDeptChange = (newDept) => {
    if (setDeptFilter) {
      setDeptFilter(newDept);
    }
    if (setPracticeFilter) {
      setPracticeFilter("ALL");
    }
    if (setTeamFilter) {
      setTeamFilter("ALL");
    }
  };

  const triggerCutoffCheck = async () => {
    setSchedulerLoading(true);
    setSchedulerStatus(null);
    try {
      const url = `${API_URL || ""}/scheduler/run-cutoff?force=true&date=${selectedDate}`;
      const res = authFetch ? await authFetch(url, { method: "POST" }) : await fetch(url, { method: "POST" });
      const data = await res.json();
      setSchedulerStatus({ type: "success", text: `Attendance Cutoff check executed for ${selectedDate}. Reports generated: ${data.hr_reports_processed || 0}.` });
      if (loadAttendanceByDate) loadAttendanceByDate(selectedDate);
    } catch (err) {
      setSchedulerStatus({ type: "error", text: err.message || "Failed to execute cutoff check" });
    } finally {
      setSchedulerLoading(false);
    }
  };

  const triggerEODReport = async () => {
    setSchedulerLoading(true);
    setSchedulerStatus(null);
    try {
      const url = `${API_URL || ""}/scheduler/run-eod?force=true&date=${selectedDate}`;
      const res = authFetch ? await authFetch(url, { method: "POST" }) : await fetch(url, { method: "POST" });
      const data = await res.json();
      setSchedulerStatus({ type: "success", text: `End-of-Day HR report generated for ${selectedDate}. Reports processed: ${data.reports_processed || 0}.` });
    } catch (err) {
      setSchedulerStatus({ type: "error", text: err.message || "Failed to generate EOD report" });
    } finally {
      setSchedulerLoading(false);
    }
  };

  return (
    <div className="miracle-attendance-page">
      {schedulerStatus && (
        <div
          className={`message ${schedulerStatus.type === "success" ? "success-message" : "error-message"}`}
          style={{ marginBottom: "16px", display: "flex", justifyContent: "space-between", alignItems: "center" }}
        >
          <span>{schedulerStatus.text}</span>
          <button
            type="button"
            onClick={() => setSchedulerStatus(null)}
            style={{ background: "none", border: "none", cursor: "pointer", fontWeight: 700, fontSize: "16px" }}
          >
            ×
          </button>
        </div>
      )}
      {dateAttendanceError && (
        <div className="message error-message" style={{ marginBottom: "16px" }}>
          {dateAttendanceError}
        </div>
      )}

      <div className="miracle-attendance-layout">
        {/* Left Column: Vertically Scrollable Alphabetical Employee Cards */}
        <div className="miracle-employee-column">
          <div className="miracle-column-header" style={{ position: "relative", display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
            <div>
              <h2 className="miracle-list-title">Employee Attendance</h2>
              <p className="miracle-list-subtitle">
                Showing attendance records for{" "}
                <strong>{selectedDateText || selectedDate}</strong>
              </p>
            </div>

            <div style={{ position: "relative" }}>
              <button
                type="button"
                onClick={() => setBufferModalOpen((prev) => !prev)}
                className="miracle-buffer-btn"
                style={{
                  background: "#ffffff",
                  color: "#0078d4",
                  border: "2px solid #0078d4",
                  borderRadius: "6px",
                  padding: "8px 16px",
                  fontWeight: "700",
                  fontSize: "13px",
                  letterSpacing: "0.5px",
                  cursor: "pointer",
                  display: "inline-flex",
                  alignItems: "center",
                  gap: "8px",
                  transition: "all 0.15s ease",
                  boxShadow: "0 1px 3px rgba(0, 120, 212, 0.12)",
                }}
                title="Configure attendance buffer grace period"
              >
                <span>SET BUFFER TIME</span>
                {currentBufferMinutes > 0 && (
                  <span
                    style={{
                      background: "#eff6ff",
                      color: "#1d4ed8",
                      border: "1px solid #bfdbfe",
                      borderRadius: "4px",
                      padding: "1px 6px",
                      fontSize: "11px",
                      fontWeight: "700",
                    }}
                  >
                    {currentBufferMinutes}m
                  </span>
                )}
                <svg
                  width="13"
                  height="13"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2.5"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <polyline points="6 9 12 15 18 9"></polyline>
                </svg>
              </button>

              {bufferModalOpen && (
                <div
                  style={{
                    position: "absolute",
                    top: "calc(100% + 8px)",
                    right: 0,
                    width: "221px",
                    background: "#ffffff",
                    border: "1px solid #cbd5e1",
                    borderRadius: "10px",
                    padding: "16px",
                    boxShadow: "0 10px 25px -5px rgba(0, 0, 0, 0.15), 0 8px 10px -6px rgba(0, 0, 0, 0.1)",
                    zIndex: 50,
                  }}
                >
                  {/* <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "12px" }}>
                    <span style={{ fontWeight: 700, fontSize: "14px", color: "#0f172a" }}>
                      Set Grace Buffer Time
                    </span>
                    <button
                      type="button"
                      onClick={() => setBufferModalOpen(false)}
                      style={{ background: "none", border: "none", cursor: "pointer", fontSize: "16px", color: "#64748b", fontWeight: 700 }}
                    >
                      ×
                    </button>
                  </div> */}

                  {/* <p style={{ fontSize: "12px", color: "#64748b", margin: "0 0 12px 0", lineHeight: 1.4 }}>
                    Arrival within the buffer period after shift start will be marked <strong>On Time</strong>.
                  </p> */}

                  <div style={{ marginBottom: "12px" }}>
                    {/* <label style={{ display: "block", fontSize: "12px", fontWeight: 600, color: "#334155", marginBottom: "4px" }}>
                      Buffer Duration
                    </label> */}
                    <select
                      value={bufferSelection}
                      onChange={(e) => setBufferSelection(e.target.value)}
                      style={{
                        width: "100%",
                        padding: "8px 10px",
                        borderRadius: "6px",
                        border: "1px solid #cbd5e1",
                        fontSize: "13px",
                        color: "#0f172a",
                        background: "#f8fafc",
                        outline: "none",
                        cursor: "pointer",
                      }}
                    >
                      <option value="0">0 Minutes (Disabled)</option>
                      <option value="5">5 Minutes</option>
                      <option value="10">10 Minutes</option>
                      <option value="15">15 Minutes</option>
                      <option value="custom">Custom Time</option>
                    </select>
                  </div>

                  {bufferSelection === "custom" && (
                    <div style={{ marginBottom: "14px" }}>
                      <label style={{ display: "block", fontSize: "12px", fontWeight: 600, color: "#334155", marginBottom: "4px" }}>
                        Enter Minutes
                      </label>
                      <input
                        type="number"
                        min="1"
                        max="120"
                        placeholder="e.g. 20"
                        value={customBufferMinutes}
                        onChange={(e) => setCustomBufferMinutes(e.target.value)}
                        style={{
                          width: "100%",
                          padding: "8px 10px",
                          borderRadius: "6px",
                          border: "1px solid #cbd5e1",
                          fontSize: "13px",
                          color: "#0f172a",
                          outline: "none",
                          boxSizing: "border-box",
                        }}
                      />
                    </div>
                  )}

                  {bufferMessage && (
                    <div
                      style={{
                        padding: "6px 10px",
                        borderRadius: "6px",
                        fontSize: "12px",
                        marginBottom: "10px",
                        background: bufferMessage.type === "success" ? "#ecfdf5" : "#fef2f2",
                        color: bufferMessage.type === "success" ? "#065f46" : "#991b1b",
                        border: `1px solid ${bufferMessage.type === "success" ? "#a7f3d0" : "#fecaca"}`,
                      }}
                    >
                      {bufferMessage.text}
                    </div>
                  )}

                  <div style={{ display: "flex", gap: "8px", justifyContent: "flex-end" }}>
                    <button
                      type="button"
                      onClick={() => setBufferModalOpen(false)}
                      style={{
                        padding: "6px 12px",
                        borderRadius: "6px",
                        border: "1px solid #cbd5e1",
                        background: "#ffffff",
                        color: "#475569",
                        fontSize: "12.5px",
                        fontWeight: 600,
                        cursor: "pointer",
                      }}
                    >
                      Cancel
                    </button>
                    <button
                      type="button"
                      disabled={bufferLoading}
                      onClick={() => handleSaveBuffer()}
                      style={{
                        padding: "6px 14px",
                        borderRadius: "6px",
                        border: "none",
                        background: "#0078d4",
                        color: "#ffffff",
                        fontSize: "12.5px",
                        fontWeight: 700,
                        cursor: "pointer",
                        opacity: bufferLoading ? 0.7 : 1,
                      }}
                    >
                      {bufferLoading ? "Applying..." : "Save Buffer"}
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>

          <div className="miracle-cards-scroll-container">
            {dateAttendanceLoading ? (
              <div
                className="loading-state"
                style={{
                  background: "#ffffff",
                  padding: "30px",
                  borderRadius: "6px",
                  textAlign: "center",
                }}
              >
                Loading employee attendance records…
              </div>
            ) : sortedAttendanceEmployees.length === 0 ? (
              <div
                className="empty-state"
                style={{
                  background: "#ffffff",
                  padding: "40px 20px",
                  borderRadius: "6px",
                  textAlign: "center",
                  border: "1px solid #e2e8f0",
                }}
              >
                <div
                  style={{
                    fontSize: "28px",
                    color: "#94a3b8",
                    marginBottom: "8px",
                  }}
                >
                  ⊘
                </div>
                <div
                  style={{
                    fontWeight: "600",
                    color: "#334155",
                    marginBottom: "4px",
                  }}
                >
                  No employees match the selected criteria
                </div>
                <p style={{ color: "#64748b", fontSize: "13px", margin: 0 }}>
                  Try clearing or adjusting search keywords, department,
                  location, or status filters.
                </p>
              </div>
            ) : (
              sortedAttendanceEmployees.map((emp) => {
                const rec = getAttendance(emp.employee_id) || {};
                const initials = (emp.employee_name || "E")
                  .split(" ")
                  .filter(Boolean)
                  .map((n) => n[0])
                  .slice(0, 2)
                  .join("")
                  .toUpperCase();

                const empId = String(emp.employee_id || emp.id || emp.login_id || "");
                const avatarUrl =
                  emp.profile_pic ||
                  emp.profilePic ||
                  rec.profile_pic ||
                  rec.profilePic ||
                  profilePics[empId];
                const hasValidPic = Boolean(avatarUrl) && !imgErrors[empId];

                return (
                  <div key={emp.employee_id} className="miracle-employee-card">
                    {hasValidPic ? (
                      <img
                        src={avatarUrl}
                        alt={emp.employee_name || "Employee"}
                        className="miracle-card-avatar"
                        style={{
                          width: 48,
                          height: 48,
                          borderRadius: "50%",
                          objectFit: "cover",
                          flexShrink: 0,
                          border: "2px solid #ffffff",
                          boxShadow: "0 2px 4px rgba(0, 0, 0, 0.08)",
                        }}
                        onError={() =>
                          setImgErrors((prev) => ({ ...prev, [empId]: true }))
                        }
                      />
                    ) : (
                      <div
                        className="miracle-card-avatar"
                        style={{
                          width: 48,
                          height: 48,
                          borderRadius: "50%",
                          background: "#004b87",
                          color: "#ffffff",
                          fontSize: 16,
                          fontWeight: 700,
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "center",
                          flexShrink: 0,
                          border: "2px solid #ffffff",
                          boxShadow: "0 2px 4px rgba(0, 0, 0, 0.08)",
                          letterSpacing: "0.5px",
                        }}
                      >
                        {initials}
                      </div>
                    )}

                    <div className="miracle-card-info">
                      <div
                        className="miracle-card-name"
                        style={{
                          fontSize: "15px",
                          fontWeight: 700,
                          color: "#0f172a",
                          marginBottom: "3px",
                          letterSpacing: "-0.01em",
                        }}
                      >
                        {emp.employee_name}
                      </div>

                      <div
                        className="miracle-card-shift-row"
                        style={{
                          fontSize: "12.5px",
                          color: "#475569",
                          fontWeight: 500,
                          display: "flex",
                          alignItems: "center",
                          gap: "6px",
                          marginBottom: "6px",
                        }}
                      >
                        <span
                          className="miracle-card-shift-icon"
                          style={{
                            display: "inline-flex",
                            alignItems: "center",
                            color: "#64748b",
                          }}
                        >
                          <svg
                            width="13"
                            height="13"
                            viewBox="0 0 24 24"
                            fill="none"
                            stroke="currentColor"
                            strokeWidth="2"
                            strokeLinecap="round"
                            strokeLinejoin="round"
                          >
                            <circle cx="12" cy="12" r="10"></circle>
                            <polyline points="12 6 12 12 16 14"></polyline>
                          </svg>
                        </span>
                        <span>
                          {emp.is_flexible_shift
                            ? "Flexible Shift"
                            : `Shift: ${emp.shift_start || "09:00"} – ${emp.shift_end || "17:00"
                            }`}
                        </span>
                      </div>

                      <div
                        className="miracle-card-badges-row"
                        style={{
                          display: "flex",
                          alignItems: "center",
                          gap: "8px",
                          flexWrap: "wrap",
                        }}
                      >
                        <span
                          className="miracle-pill miracle-pill-location"
                          style={{
                            background: "#0078d4",
                            color: "#ffffff",
                            fontWeight: 700,
                            fontSize: "11px",
                            padding: "3px 8px",
                            borderRadius: "4px",
                            textTransform: "uppercase",
                            letterSpacing: "0.2px",
                          }}
                        >
                          {emp.work_location ||
                            emp.location ||
                            "MIRACLE CITY (HQ)"}
                        </span>

                        <span
                          className="miracle-pill"
                          style={{
                            background: "#eff6ff",
                            color: "#0066cc",
                            border: "1px solid #bfdbfe",
                            fontWeight: 650,
                            fontSize: "11px",
                            padding: "3px 8px",
                            borderRadius: "4px",
                          }}
                        >
                          HR: {emp.reporting_hr || rec.reporting_hr || "Unassigned"}
                        </span>
                      </div>
                    </div>

                    <div className="miracle-card-actions">
                      <button
                        type="button"
                        className="miracle-card-icon-btn btn-blue"
                        onClick={(e) => {
                          e.stopPropagation();
                          openEditShift(emp);
                        }}
                        title="Edit Shift"
                        aria-label={`Edit shift for ${emp.employee_name}`}
                      >
                        <svg
                          width="15"
                          height="15"
                          viewBox="0 0 24 24"
                          fill="none"
                          stroke="currentColor"
                          strokeWidth="2"
                          strokeLinecap="round"
                          strokeLinejoin="round"
                        >
                          <path d="M17 3a2.85 2.83 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5Z"></path>
                          <path d="m15 5 4 4"></path>
                        </svg>
                      </button>

                      <button
                        type="button"
                        className="miracle-card-icon-btn btn-blue"
                        onClick={(e) => {
                          e.stopPropagation();
                          openEmployeeHistory(emp);
                        }}
                        title="View History"
                        aria-label={`View attendance history for ${emp.employee_name}`}
                      >
                        <svg
                          width="15"
                          height="15"
                          viewBox="0 0 24 24"
                          fill="none"
                          stroke="currentColor"
                          strokeWidth="2"
                          strokeLinecap="round"
                          strokeLinejoin="round"
                        >
                          <path d="M12 8v4l3 3"></path>
                          <path d="M3.05 11a9 9 0 1 1 .5 4m-.5 5v-5h5"></path>
                        </svg>
                      </button>

                      <button
                        type="button"
                        className="miracle-card-icon-btn btn-blue"
                        onClick={(e) => {
                          e.stopPropagation();
                          openReportChooser(emp);
                        }}
                        title="Export Report"
                        aria-label={`Export report for ${emp.employee_name}`}
                      >
                        <svg
                          width="15"
                          height="15"
                          viewBox="0 0 24 24"
                          fill="none"
                          stroke="currentColor"
                          strokeWidth="2"
                          strokeLinecap="round"
                          strokeLinejoin="round"
                        >
                          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                          <polyline points="14 2 14 8 20 8"></polyline>
                          <line x1="16" y1="13" x2="8" y2="13"></line>
                          <line x1="16" y1="17" x2="8" y2="17"></line>
                          <polyline points="10 9 9 9 8 9"></polyline>
                        </svg>
                      </button>

                      <button
                        type="button"
                        className="miracle-card-icon-btn btn-delete"
                        onClick={(e) => {
                          e.stopPropagation();
                          deleteEmployee(emp);
                        }}
                        disabled={
                          deletingEmployeeId === String(emp.employee_id)
                        }
                        title="Delete"
                        aria-label={`Delete ${emp.employee_name}`}
                      >
                        <svg
                          width="15"
                          height="15"
                          viewBox="0 0 24 24"
                          fill="none"
                          stroke="currentColor"
                          strokeWidth="2"
                          strokeLinecap="round"
                          strokeLinejoin="round"
                        >
                          <polyline points="3 6 5 6 21 6"></polyline>
                          <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
                          <line x1="10" y1="11" x2="10" y2="17"></line>
                          <line x1="14" y1="11" x2="14" y2="17"></line>
                        </svg>
                      </button>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>

        {/* Right Column: Filter By Card matching Miracle Reference */}
        <div className="miracle-filter-column">
          <div className="miracle-filter-card">
            {/* Search Field */}
            <div className="miracle-filter-section">
              <label className="miracle-filter-label">EMPLOYEE SEARCH</label>
              <div className="miracle-search-input-group">
                <input
                  type="text"
                  className="miracle-filter-input"
                  placeholder="Search by Name, Email or Mobile"
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                />
                <button
                  type="button"
                  className="miracle-search-btn"
                  title="Search employees"
                >
                  <svg
                    width="15"
                    height="15"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2.5"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  >
                    <circle cx="11" cy="11" r="8"></circle>
                    <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
                  </svg>
                </button>
              </div>
            </div>

            <div className="miracle-filter-title">Filter By</div>

            {/* Attendance Date */}
            <div className="miracle-filter-section">
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  marginBottom: "6px",
                }}
              >
                <label className="miracle-filter-label" style={{ margin: 0 }}>
                  ATTENDANCE DATE
                </label>
                <button
                  type="button"
                  className="miracle-today-link"
                  onClick={() => {
                    const now = new Date();
                    const todayStr = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-${String(now.getDate()).padStart(2, "0")}`;
                    setSelectedDate(todayStr);
                    loadAttendanceByDate(todayStr);
                  }}
                >
                  Today
                </button>
              </div>
              <input
                type="date"
                className="miracle-filter-input"
                value={selectedDate}
                max={(() => {
                  const now = new Date();
                  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-${String(now.getDate()).padStart(2, "0")}`;
                })()}
                onChange={(e) => {
                  const val = e.target.value;
                  const now = new Date();
                  const todayStr = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-${String(now.getDate()).padStart(2, "0")}`;
                  if (val > todayStr) {
                    return;
                  }
                  handleAttendanceDateChange(e);
                }}
              />
            </div>

            {/* Department Filter */}
            <div className="miracle-filter-section">
              <label className="miracle-filter-label">DEPARTMENT</label>
              <select
                className="miracle-filter-select"
                value={deptFilter}
                onChange={(e) => handleDeptChange(e.target.value)}
              >
                <option value="ALL">All Departments</option>
                {allDepartments.map((d) => (
                  <option key={d} value={d}>
                    {d}
                  </option>
                ))}
              </select>
            </div>

            {/* Practice Filter */}
            <div className="miracle-filter-section">
              <label className="miracle-filter-label">PRACTICE</label>
              <select
                className="miracle-filter-select"
                value={isPracticeDisabled ? "ALL" : practiceFilter}
                disabled={isPracticeDisabled}
                onChange={(e) =>
                  setPracticeFilter && setPracticeFilter(e.target.value)
                }
                style={{
                  background: isPracticeDisabled ? "#f8fafc" : "white",
                  color: isPracticeDisabled ? "#94a3b8" : "#1e293b",
                  cursor: isPracticeDisabled ? "not-allowed" : "pointer",
                }}
              >
                <option value="ALL">All Practices</option>
                {isSoftwareServices &&
                  practiceOptions.map((p) => (
                    <option key={p} value={p}>
                      {p}
                    </option>
                  ))}
              </select>
            </div>

            {/* Dependent Team Filter */}
            <div className="miracle-filter-section">
              <label className="miracle-filter-label">TEAM</label>
              <select
                className="miracle-filter-select"
                value={isTeamDisabled ? "ALL" : teamFilter}
                disabled={isTeamDisabled}
                onChange={(e) => setTeamFilter && setTeamFilter(e.target.value)}
                style={{
                  background: isTeamDisabled ? "#f8fafc" : "white",
                  color: isTeamDisabled ? "#94a3b8" : "#1e293b",
                  cursor: isTeamDisabled ? "not-allowed" : "pointer",
                }}
              >
                <option value="ALL">All Teams</option>
                {availableTeams.map((t) => (
                  <option key={t} value={t}>
                    {t}
                  </option>
                ))}
              </select>
            </div>

            {/* Sub-Practice Filter
            <div className="miracle-filter-section">
              <label className="miracle-filter-label">SUB-PRACTICE</label>
              <select
                className="miracle-filter-select"
                value={subPracticeFilter}
                onChange={(e) =>
                  setSubPracticeFilter && setSubPracticeFilter(e.target.value)
                }
              >
                <option value="ALL">All Sub-Practices</option>
                {allSubPractices.map((sp) => (
                  <option key={sp} value={sp}>
                    {sp}
                  </option>
                ))}
              </select>
            </div> */}

            {/* Work Location Filter */}
            {/* <div className="miracle-filter-section">
              <label className="miracle-filter-label">WORK LOCATION</label>
              <select
                className="miracle-filter-select"
                value={locationFilter}
                onChange={(e) => setLocationFilter(e.target.value)}
              >
                <option value="ALL">All Work Locations</option>
                {allLocations.map((loc) => (
                  <option key={loc} value={loc}>
                    {loc}
                  </option>
                ))}
              </select>
            </div> */}


            {/* Attendance Status Filter */}
            {/* <div className="miracle-filter-section">
              <label className="miracle-filter-label">ATTENDANCE STATUS</label>
              <select
                className="miracle-filter-select"
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
              >
                <option value="ALL">All Statuses</option>
                <option value="PRESENT">Present</option>
                <option value="LATE">Late Arrival</option>
                <option value="ABSENT">Absent</option>
                <option value="HALF_DAY">Half Day</option>
                <option value="INSIDE_NOW">Inside Now</option>
              </select>
            </div> */}

            {/* Automated Attendance & HR Reporting Controls matching Image 2 */}
            <div
              style={{
                marginTop: "16px",
                padding: "14px",
                background: "#f8fafc",
                border: "1px solid #e2e8f0",
                borderRadius: "8px",
              }}
            >
              <div style={{ fontSize: "11px", fontWeight: 700, color: "#475569", letterSpacing: "0.5px", marginBottom: "8px" }}>
                AUTOMATED HR REPORTS
              </div>
              <button
                type="button"
                onClick={() => {
                  setPreviewReportType("arrival");
                  setPreviewModalOpen(true);
                }}
                style={{
                  width: "100%",
                  padding: "9px 12px",
                  marginBottom: "8px",
                  borderRadius: "6px",
                  border: "1px solid #003a70",
                  background: "#ffffff",
                  color: "#003a70",
                  fontSize: "12px",
                  fontWeight: 700,
                  cursor: "pointer",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  gap: "6px",
                  transition: "all 0.15s ease",
                }}
              >
                Shift Arrival Status
              </button>
              <button
                type="button"
                onClick={() => {
                  setPreviewReportType("eod");
                  setPreviewModalOpen(true);
                }}
                style={{
                  width: "100%",
                  padding: "9px 12px",
                  borderRadius: "6px",
                  border: "1px solid #0284c7",
                  background: "#f0f9ff",
                  color: "#0369a1",
                  fontSize: "12px",
                  fontWeight: 700,
                  cursor: "pointer",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  gap: "6px",
                  transition: "all 0.15s ease",
                }}
              >
                EOD Report
              </button>
            </div>

            {/* Actions in Filter Card */}
            <div className="miracle-filter-actions">
              <button
                type="button"
                className="miracle-export-btn"
                onClick={() => openReportChooser()}
              >
                <svg
                  width="15"
                  height="15"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  style={{ marginRight: "7px" }}
                >
                  <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                  <polyline points="7 10 12 15 17 10"></polyline>
                  <line x1="12" y1="15" x2="12" y2="3"></line>
                </svg>
                Export Attendance (.xlsx)
              </button>

              {(search ||
                deptFilter !== "ALL" ||
                practiceFilter !== "ALL" ||
                teamFilter !== "ALL" ||
                locationFilter !== "ALL" ||
                statusFilter !== "ALL") && (
                  <button
                    type="button"
                    className="miracle-reset-btn"
                    onClick={() => {
                      setSearch("");
                      if (auth?.role !== "hr") setDeptFilter("ALL");
                      if (setPracticeFilter) setPracticeFilter("ALL");
                      if (setTeamFilter) setTeamFilter("ALL");
                      if (setSubPracticeFilter) setSubPracticeFilter("ALL");
                      setLocationFilter("ALL");
                      setStatusFilter("ALL");
                    }}
                  >
                    Clear Filters
                  </button>
                )}
            </div>
          </div>
        </div>
      </div>

      {/* Automated HR Reports Dashboard Preview Modal (Requirement 7) */}
      <ReportPreviewModal
        isOpen={previewModalOpen}
        onClose={() => setPreviewModalOpen(false)}
        reportType={previewReportType}
        selectedDate={selectedDate}
        authFetch={authFetch}
        API_URL={API_URL}
      />
    </div>
  );
}
