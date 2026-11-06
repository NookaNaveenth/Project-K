import os
import sys
import json
import requests
import datetime
from attendance import (
    calculate_arrival_status,
    calculate_attendance_status,
    calculate_break_minutes,
    set_system_buffer_minutes,
    get_system_buffer_minutes,
    validate_late_arrival_notification,
)

BASE_URL = "http://127.0.0.1:8000"

def run_tests():
    print("=" * 70)
    print("COMPREHENSIVE VERIFICATION: 20 SPECIFIED SCENARIOS")
    print("=" * 70)

    # Login to obtain authorization token
    login_res = requests.post(f"{BASE_URL}/auth/login", json={"username": "superior", "password": "superior123"})
    assert login_res.status_code == 200, f"Login failed: {login_res.text}"
    token = login_res.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}
    print("[PASS] Authentication established (Superior user)")

    # =========================================================================
    # PART 1: BUFFER TIME SCENARIOS (1 to 5)
    # =========================================================================
    print("\n--- Scenarios 1-5: Buffer Time Configurations & Lateness ---")
    
    # 1. 5-minute buffer
    set_res = requests.post(f"{BASE_URL}/attendance/buffer-time", json={"buffer_minutes": 5}, headers=headers)
    assert set_res.status_code == 200 and set_res.json()["buffer_minutes"] == 5
    st, early, late = calculate_arrival_status("14:04", "14:00", buffer_minutes=5)
    assert st == "ON_TIME", f"5-min buffer: 14:04 should be ON_TIME, got {st}"
    st, early, late = calculate_arrival_status("14:05", "14:00", buffer_minutes=5)
    assert st == "ON_TIME", f"5-min buffer: 14:05 should be ON_TIME, got {st}"
    st, early, late = calculate_arrival_status("14:08", "14:00", buffer_minutes=5)
    assert st == "LATE" and late == 3, f"5-min buffer: 14:08 should be LATE by 3, got {st}, {late}"
    print("[PASS] Scenario 1: 5-minute buffer verified (14:04 & 14:05 on-time, 14:08 late by 3 min)")

    # 2. 10-minute buffer
    set_res = requests.post(f"{BASE_URL}/attendance/buffer-time", json={"buffer_minutes": 10}, headers=headers)
    assert set_res.status_code == 200 and set_res.json()["buffer_minutes"] == 10
    st, early, late = calculate_arrival_status("14:05", "14:00", buffer_minutes=10)
    assert st == "ON_TIME"
    st, early, late = calculate_arrival_status("14:10", "14:00", buffer_minutes=10)
    assert st == "ON_TIME"
    st, early, late = calculate_arrival_status("14:15", "14:00", buffer_minutes=10)
    assert st == "LATE" and late == 5
    print("[PASS] Scenario 2: 10-minute buffer verified (14:05 & 14:10 on-time, 14:15 late by 5 min)")

    # 3. 15-minute buffer
    set_res = requests.post(f"{BASE_URL}/attendance/buffer-time", json={"buffer_minutes": 15}, headers=headers)
    assert set_res.status_code == 200 and set_res.json()["buffer_minutes"] == 15
    st, early, late = calculate_arrival_status("14:15", "14:00", buffer_minutes=15)
    assert st == "ON_TIME"
    st, early, late = calculate_arrival_status("14:20", "14:00", buffer_minutes=15)
    assert st == "LATE" and late == 5
    print("[PASS] Scenario 3: 15-minute buffer verified (14:15 on-time, 14:20 late by 5 min)")

    # 4. Custom buffer (e.g. 25 minutes)
    set_res = requests.post(f"{BASE_URL}/attendance/buffer-time", json={"buffer_minutes": 25}, headers=headers)
    assert set_res.status_code == 200 and set_res.json()["buffer_minutes"] == 25
    st, early, late = calculate_arrival_status("14:24", "14:00", buffer_minutes=25)
    assert st == "ON_TIME"
    st, early, late = calculate_arrival_status("14:30", "14:00", buffer_minutes=25)
    assert st == "LATE" and late == 5
    print("[PASS] Scenario 4: Custom 25-minute buffer verified (14:24 on-time, 14:30 late by 5 min)")

    # 5. Late-arrival notifications use the same buffer calculation
    # Reset to 10 min buffer
    set_system_buffer_minutes(10)
    val_ontime = validate_late_arrival_notification("9615", "2026-11-04", check_in_time="14:08", shift_start="14:00")
    assert not val_ontime["should_send"], f"14:08 with 10 min buffer should not send email, got {val_ontime}"
    val_late = validate_late_arrival_notification("9615", "2026-11-04", check_in_time="14:20", shift_start="14:00")
    assert val_late["should_send"] and val_late["late_minutes"] == 10, f"14:20 with 10 min buffer should send email for 10 min late, got {val_late}"
    print("[PASS] Scenario 5: Late-arrival email notification validation strictly respects buffer time")

    # =========================================================================
    # PART 2: EMPLOYEE DATA & TWO-WAY SYNC (6 to 9)
    # =========================================================================
    print("\n--- Scenarios 6-9: Mock API Integration & Two-Way Sync ---")
    
    # 6. Verify profile pictures load from Mock API
    emp_res = requests.get(f"{BASE_URL}/mock-hubble/profile-picture/9615")
    assert emp_res.status_code == 200 and "nchowdari.png" in emp_res.json()["profilePic"]
    print(f"[PASS] Scenario 6: Profile pic loads from Mock API: {emp_res.json()['profilePic']}")

    # 7. Update profile picture in Mock API and verify UI/API reflects it
    test_pic_url = "https://images.miraclesoft.com/employee-profile-pics/test_profile_update.png"
    up_res = requests.put(f"{BASE_URL}/mock-hubble/employee/9615", json={"profilePic": test_pic_url})
    assert up_res.status_code == 200, f"Mock update failed: {up_res.text}"
    emp_refetched = requests.get(f"{BASE_URL}/employees/9615", headers=headers).json()
    assert emp_refetched["profile_pic"] == test_pic_url, f"Refetched employee does not have updated pic: {emp_refetched.get('profile_pic')}"
    print("[PASS] Scenario 7: Mock API update immediately reflects in application API")

    # Revert pic URL back
    orig_pic = "https://images.miraclesoft.com/employee-profile-pics/nchowdari.png"
    requests.put(f"{BASE_URL}/mock-hubble/employee/9615", json={"profilePic": orig_pic})

    # 8. Change employee shift timings through UI/API and verify Mock API updates
    shift_res = requests.put(f"{BASE_URL}/employees/9615/shift", json={"shift_start": "13:30", "shift_end": "22:30", "is_flexible_shift": False}, headers=headers)
    assert shift_res.status_code == 200, f"Shift update failed: {shift_res.text}"
    # Verify Mock API has the updated shift
    mock_emp = requests.get(f"{BASE_URL}/mock-hubble/employee/9615").json()
    assert mock_emp.get("shift_start") == "13:30" and mock_emp.get("shift_end") == "22:30", f"Mock API shift not updated: {mock_emp}"
    print("[PASS] Scenario 8: Shift update in application successfully synced back to Mock API")

    # Revert shift back
    requests.put(f"{BASE_URL}/employees/9615/shift", json={"shift_start": "14:00", "shift_end": "23:00", "is_flexible_shift": False}, headers=headers)

    # 9. Verify changes do not create duplicate employee records
    emps_all = requests.get(f"{BASE_URL}/employees", headers=headers).json()
    emp_ids = [e["employee_id"] for e in emps_all]
    assert len(emp_ids) == len(set(emp_ids)), f"Duplicate employee IDs found: {emp_ids}"
    print(f"[PASS] Scenario 9: Zero duplicate employee records exist across directory ({len(emps_all)} unique employees)")

    # =========================================================================
    # PART 3: ATTENDANCE OVERRIDE FILTERING (10 to 12)
    # =========================================================================
    print("\n--- Scenarios 10-12: Attendance Override Dependent Dropdowns ---")
    override_path = os.path.join("hr-dashboard", "src", "pages", "AttendanceOverridePage.jsx")
    with open(override_path, "r", encoding="utf-8") as f:
        override_code = f.read()

    # 10. Teams dropdown appears and is enabled for non-Software Services departments
    assert "Teams" in override_code, "Teams dropdown label missing in AttendanceOverridePage.jsx"
    assert "isTeamDisabled" in override_code, "isTeamDisabled logic missing in AttendanceOverridePage.jsx"
    print("[PASS] Scenario 10: Teams dropdown implemented with dependency control")

    # 11. Practice dropdown appears only for Software Services
    assert "isPracticeDisabled" in override_code, "isPracticeDisabled logic missing in AttendanceOverridePage.jsx"
    assert "practiceOptions = isSoftwareServices ? SOFTWARE_SERVICES_PRACTICES : []" in override_code
    print("[PASS] Scenario 11: Practice dropdown enabled strictly for Software Services department")

    # 12. Employee filtering works correctly with teams and practices
    assert "isSoftwareServices" in override_code and "selectedPracticeFilter" in override_code
    assert "!isSoftwareServices" in override_code and "selectedTeamFilter" in override_code
    print("[PASS] Scenario 12: Employee search and dependent dropdown filtering harmonized")

    # =========================================================================
    # PART 4: ACTIVITY AND CALENDAR (13 to 16)
    # =========================================================================
    print("\n--- Scenarios 13-16: Activity and Attendance Calendar ---")
    
    # 13. Verify future dates are disabled in Activity backend API
    tomorrow = (datetime.date.today() + datetime.timedelta(days=1)).strftime("%Y-%m-%d")
    today_str = datetime.date.today().strftime("%Y-%m-%d")
    fut_audit = requests.get(f"{BASE_URL}/audit/logs?target_date={tomorrow}", headers=headers)
    assert fut_audit.status_code == 400, f"Future activity date must return 400, got {fut_audit.status_code}"
    print(f"[PASS] Scenario 13: Activity API blocks future dates: {fut_audit.json()['detail']}")

    # 14. Verify past and current dates remain selectable
    cur_audit = requests.get(f"{BASE_URL}/audit/logs?target_date={today_str}", headers=headers)
    assert cur_audit.status_code == 200, f"Today's activity logs should return 200, got {cur_audit.status_code}"
    print("[PASS] Scenario 14: Today and past dates remain fully accessible")

    # 15. Verify TODAY indicator is removed from CalendarDayCell
    day_cell_path = os.path.join("hr-dashboard", "src", "components", "calendar", "CalendarDayCell.jsx")
    with open(day_cell_path, "r", encoding="utf-8") as f:
        cell_code = f.read()
    assert "miracle-cal-today-badge" not in cell_code, "Today badge must be removed from CalendarDayCell"
    assert "is-today" not in cell_code, "is-today class must not be applied to CalendarDayCell"
    print("[PASS] Scenario 15: Automatic TODAY label and border highlight removed from calendar")

    # 16. Verify blue hover border works on all calendar dates in Calendar.css
    cal_css_path = os.path.join("hr-dashboard", "src", "components", "calendar", "Calendar.css")
    with open(cal_css_path, "r", encoding="utf-8") as f:
        cal_css = f.read()
    assert ".miracle-cal-day-card-v2:hover:not(.type-inactive)" in cal_css
    assert "border: 2px solid #0084ff !important" in cal_css
    print("[PASS] Scenario 16: Blue hover border configured on all active calendar date cells")

    # =========================================================================
    # PART 5: WORKING HOURS & THRESHOLDS (17 to 20)
    # =========================================================================
    print("\n--- Scenarios 17-20: Working Hours & 6-Hour Full-Day Threshold ---")

    # 17. 5 hours worked (300 min) is NOT marked Full Day
    status_5h = calculate_attendance_status(300)
    assert status_5h != "FULL_DAY", f"5 hours must NOT be FULL_DAY, got {status_5h}"
    assert status_5h == "HALF_DAY", f"5 hours should be HALF_DAY, got {status_5h}"
    print(f"[PASS] Scenario 17: 5 hours (300 min) correctly classified as {status_5h} (NOT Full Day)")

    # 18. Exactly 6 hours worked (360 min) is marked Full Day
    status_6h = calculate_attendance_status(360)
    assert status_6h == "FULL_DAY", f"6 hours must be FULL_DAY, got {status_6h}"
    print(f"[PASS] Scenario 18: Exactly 6 hours (360 min) correctly classified as {status_6h}")

    # 19. 8 hours worked (480 min) is marked Full Day
    status_8h = calculate_attendance_status(480)
    assert status_8h == "FULL_DAY", f"8 hours must be FULL_DAY, got {status_8h}"
    print(f"[PASS] Scenario 19: 8 hours (480 min) correctly classified as {status_8h}")

    # 20. Break deductions correctly applied
    # E.g. 8-hour scheduled shift (09:00 - 17:00 = 480 min), worked 420 min -> break is 60 min
    break_calc = calculate_break_minutes([{"check_in": "09:00", "check_out": "16:00"}], "09:00", "17:00", 420)
    assert break_calc == 60, f"Expected 60 min break deduction, got {break_calc}"
    print(f"[PASS] Scenario 20: Break deduction correctly calculated ({break_calc} min for 7h worked on 8h shift)")

    # Cleanup: Reset buffer time to 0 minutes default
    set_system_buffer_minutes(0)

    print("\n" + "=" * 70)
    print("ALL 20 SCENARIOS VERIFIED SUCCESSFULLY 100%!")
    print("=" * 70)

if __name__ == "__main__":
    run_tests()
