import datetime
import json
import requests
import re
import os

BASE_URL = "http://127.0.0.1:8000"

def test_all():
    print("=" * 60)
    print("TESTING ALL 5 NEW REQUIREMENTS")
    print("=" * 60)

    # Login to get auth token
    login_res = requests.post(f"{BASE_URL}/auth/login", json={"username": "superior", "password": "superior123"})
    assert login_res.status_code == 200, f"Login failed: {login_res.text}"
    token = login_res.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}
    print("[PASS] Superior login successful")

    # ---------------------------------------------------------
    # 1. Dynamic Employee Profile Pictures (Hubble Mock API)
    # ---------------------------------------------------------
    print("\n--- 1. Testing Hubble Mock API & Dynamic Profile Pictures ---")
    hubble_res = requests.get(f"{BASE_URL}/mock-hubble/employees")
    assert hubble_res.status_code == 200, "Hubble mock employees endpoint failed"
    hubble_data = hubble_res.json()
    assert len(hubble_data) > 0, "No mock Hubble employees found"
    print(f"[PASS] Mock Hubble employee directory loaded ({len(hubble_data)} employees)")

    # Test profile picture endpoint
    for test_id, expected_img in [
        ("9615", "nchowdari.png"),
        ("9616", "mamujuri.png"),
        ("9614", "isanapathi.png"),
        ("9608", "mbhasyam.png"),
    ]:
        pic_res = requests.get(f"{BASE_URL}/mock-hubble/profile-picture/{test_id}")
        assert pic_res.status_code == 200, f"Profile pic endpoint failed for {test_id}"
        pic_data = pic_res.json()
        assert expected_img in pic_data.get("profilePic", ""), f"Unexpected profile pic URL for {test_id}: {pic_data}"
        print(f"[PASS] Dynamic profile pic for {test_id}: {pic_data['profilePic']}")

    # Test that /employees API returns dynamic profile_pic
    emps_res = requests.get(f"{BASE_URL}/employees", headers=headers)
    assert emps_res.status_code == 200, "GET /employees failed"
    emps = emps_res.json()
    found_pics = [e for e in emps if e.get("profile_pic")]
    print(f"[PASS] GET /employees returned {len(emps)} employees, {len(found_pics)} have dynamic profile pics")
    assert len(found_pics) >= 4, "Expected at least 4 employees with profile pictures"

    # ---------------------------------------------------------
    # 2. Disable Future Dates in Attendance Calendar & Backend API
    # ---------------------------------------------------------
    print("\n--- 2. Testing Future Date Prevention ---")
    today = datetime.date.today()
    future_date = (today + datetime.timedelta(days=2)).strftime("%Y-%m-%d")
    today_str = today.strftime("%Y-%m-%d")

    # Future date API call must be rejected with 400
    fut_res = requests.get(f"{BASE_URL}/attendance/date/{future_date}", headers=headers)
    print(f"Future date {future_date} response: {fut_res.status_code} - {fut_res.json()}")
    assert fut_res.status_code == 400, "Future attendance date must return HTTP 400"
    assert "future" in fut_res.json().get("detail", "").lower(), "Error message must state future dates not allowed"
    print("[PASS] Backend API blocked future attendance query")

    # Today's date API call must succeed
    today_res = requests.get(f"{BASE_URL}/attendance/date/{today_str}", headers=headers)
    assert today_res.status_code == 200, f"Today's attendance request failed: {today_res.status_code}"
    print(f"[PASS] Today's attendance date ({today_str}) successfully queried")

    # ---------------------------------------------------------
    # 3. Attendance Dashboard – Pie Chart (Week Off)
    # ---------------------------------------------------------
    print("\n--- 3. Testing Attendance Dashboard Pie Chart (Week Off) ---")
    charts_path = os.path.join("hr-dashboard", "src", "components", "DashboardAnalyticsCharts.jsx")
    with open(charts_path, "r", encoding="utf-8") as f:
        charts_code = f.read()

    assert 'label: "Week Off"' in charts_code, "Week Off missing in donut slices"
    assert '#cbd5e1' in charts_code, "Week Off color (#cbd5e1) missing in donut slices"
    assert '<span>Week Off</span>' in charts_code, "Week Off missing in donut legend"
    assert 'weekOffToday' in charts_code, "weekOffToday count missing in donut chart calculations"
    print("[PASS] DashboardAnalyticsCharts includes 'Week Off' in pie chart slices & legend")

    # ---------------------------------------------------------
    # 4. Responsive Late-Arrival Email Template (White background)
    # ---------------------------------------------------------
    print("\n--- 4. Testing Responsive Late-Arrival Email Template ---")
    from email_service import get_late_notification_colors
    colors = get_late_notification_colors(1)
    
    with open("email_service.py", "r", encoding="utf-8") as f:
        email_code = f.read()

    assert "background-color: #ffffff" in email_code, "Outer email body background must be #ffffff"
    assert "@media only screen and (max-width: 540px)" in email_code, "Mobile responsive CSS media query missing"
    assert "header-stack" in email_code, "header-stack responsive class missing"
    assert "badge-chip" in email_code, "badge-chip responsive class missing"
    assert "details-table" in email_code, "details-table responsive class missing"
    print("[PASS] Email service template has pure white outer background (#ffffff) and mobile-responsive styles")

    # ---------------------------------------------------------
    # 5. Simplify Employee Attendance Cards
    # ---------------------------------------------------------
    print("\n--- 5. Testing Employee Attendance Cards Simplification ---")
    att_page_path = os.path.join("hr-dashboard", "src", "pages", "AttendancePage.jsx")
    with open(att_page_path, "r", encoding="utf-8") as f:
        att_code = f.read()

    # Check card elements required
    assert "miracle-card-avatar" in att_code, "Avatar element missing"
    assert "miracle-card-name" in att_code, "Employee name missing"
    assert "miracle-card-shift-row" in att_code, "Shift row missing"
    assert "miracle-pill-location" in att_code, "Location pill missing"
    assert "HR:" in att_code, "HR pill missing"
    assert "openEditShift" in att_code, "Edit shift button missing"
    assert "openEmployeeHistory" in att_code, "View history button missing"
    assert "openReportChooser" in att_code, "Export report button missing"
    assert "deleteEmployee" in att_code, "Delete button missing"

    # Check that removed items are NOT inside the card rendering
    card_section_start = att_code.find("sortedAttendanceEmployees.map((emp) =>")
    card_section_end = att_code.find("</button>\n                    </div>\n                  </div>", card_section_start)
    card_markup = att_code[card_section_start:card_section_end]

    assert "Provisional Hours" not in card_markup, "Provisional Hours must be removed from employee card"
    assert "emp.designation" not in card_markup, "Designation must be removed from employee card"
    assert "emp.department" not in card_markup, "Department must be removed from employee card"
    assert "worked_hours" not in card_markup, "Worked Hours must be removed from employee card"
    assert "miracle-pill-status" not in card_markup, "Status pill must be removed from employee card"
    print("[PASS] Employee card strictly simplified to match Image 4 layout")

    print("\n" + "=" * 60)
    print("ALL 5 REQUIREMENTS VERIFIED SUCCESSFULLY!")
    print("=" * 60)

if __name__ == "__main__":
    test_all()
