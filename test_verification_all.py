import requests
import json
from datetime import datetime, date, timedelta

BASE_URL = "http://127.0.0.1:8000"

def run_tests():
    print("==================================================")
    print("RUNNING COMPREHENSIVE REQUIREMENTS VERIFICATION")
    print("==================================================")

    # 1. Test Login for Superior, Admin, and HR
    print("\n--- 1. Authentication & RBAC Login Tests ---")
    sup_login = requests.post(f"{BASE_URL}/auth/login", json={"username": "superior", "password": "superior123"})
    assert sup_login.status_code == 200, f"Superior login failed: {sup_login.text}"
    sup_token = sup_login.json()["token"]
    print("[PASS] Superior login successful")

    admin_login = requests.post(f"{BASE_URL}/auth/login", json={"username": "admin", "password": "admin123"})
    assert admin_login.status_code == 200, f"Admin login failed: {admin_login.text}"
    admin_token = admin_login.json()["token"]
    print("[PASS] Admin login successful")

    hr_login = requests.post(f"{BASE_URL}/auth/login", json={"username": "sprathi", "password": "hr123"})
    assert hr_login.status_code == 200, f"HR sprathi login failed: {hr_login.text}"
    hr_token = hr_login.json()["token"]
    print("[PASS] HR sprathi login successful")

    # 2. Test Data Isolation & RBAC
    print("\n--- 2. User Data Isolation & Access Scope ---")
    # Superior employees count
    sup_emps = requests.get(f"{BASE_URL}/employees", headers={"Authorization": f"Bearer {sup_token}"}).json()
    print(f"Superior sees {len(sup_emps)} total employees")
    assert len(sup_emps) > 3, "Superior should see all employees"

    # HR employees count (sprathi assigned employees only)
    hr_emps = requests.get(f"{BASE_URL}/employees", headers={"Authorization": f"Bearer {hr_token}"}).json()
    print(f"HR sprathi sees {len(hr_emps)} assigned employees: {[e['employee_id'] for e in hr_emps]}")
    assert len(hr_emps) <= len(sup_emps), "HR must see only assigned subset"
    # Unauthenticated / empty token request
    anon_emps = requests.get(f"{BASE_URL}/employees").json()
    print(f"Unauthenticated request sees {len(anon_emps)} employees (expected 0)")
    assert len(anon_emps) == 0, "Unauthenticated request must not leak employees"

    # Practices RBAC
    sup_prac = requests.get(f"{BASE_URL}/practices", headers={"Authorization": f"Bearer {sup_token}"}).json()
    hr_prac = requests.get(f"{BASE_URL}/practices", headers={"Authorization": f"Bearer {hr_token}"}).json()
    print(f"Superior practices: {len(sup_prac)} | HR practices: {len(hr_prac)}")

    # 3. Test Department and Team Dependent Dropdown APIs
    print("\n--- 3. Department & Team Dependent APIs ---")
    depts = requests.get(f"{BASE_URL}/departments").json()
    print(f"Departments: {depts}")
    expected_depts = ["Executive Board", "Marketing", "Operations", "Recruitment", "Sales", "Software Services"]
    for ed in expected_depts:
        assert ed in depts, f"Missing department {ed}"

    teams_sales = requests.get(f"{BASE_URL}/teams?department=Sales").json()
    print(f"Sales Teams: {teams_sales}")
    assert "Inside Sales" in teams_sales
    assert "Software Sales" in teams_sales

    teams_recruitment = requests.get(f"{BASE_URL}/teams?department=Recruitment").json()
    print(f"Recruitment Teams: {teams_recruitment}")
    assert "US IT" in teams_recruitment

    teams_operations = requests.get(f"{BASE_URL}/teams?department=Operations").json()
    print(f"Operations Teams: {teams_operations}")
    assert "Payroll" in teams_operations

    teams_soft = requests.get(f"{BASE_URL}/teams?department=Software%20Services").json()
    print(f"Software Services Teams: {teams_soft}")
    assert len(teams_soft) == 0, "Software Services should have no teams (practices instead)"

    teams_exec = requests.get(f"{BASE_URL}/teams?department=Executive%20Board").json()
    print(f"Executive Board Teams: {teams_exec}")
    assert len(teams_exec) == 0, "Executive Board should have no teams"

    # 4. Test Filtering by Department and Team
    print("\n--- 4. Filtering by Department & Team ---")
    filtered_sales = requests.get(f"{BASE_URL}/employees?department=Sales", headers={"Authorization": f"Bearer {sup_token}"}).json()
    print(f"Sales Employees count: {len(filtered_sales)}")
    for e in filtered_sales:
        assert e.get("department") == "Sales"

    filtered_inside_sales = requests.get(f"{BASE_URL}/employees?department=Sales&team=Inside%20Sales", headers={"Authorization": f"Bearer {sup_token}"}).json()
    print(f"Inside Sales Employees count: {len(filtered_inside_sales)}")

    filtered_soft_appdev = requests.get(f"{BASE_URL}/employees?department=Software%20Services&practice=App%20Dev", headers={"Authorization": f"Bearer {sup_token}"}).json()
    print(f"Software Services App Dev Employees count: {len(filtered_soft_appdev)}")

    # 5. Test Attendance Override Future Date Restriction
    print("\n--- 5. Attendance Override Future Date Restrictions ---")
    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    future_date_payload = {
        "employee_id": sup_emps[0]["employee_id"],
        "attendance_date": tomorrow,
        "status": "FULL_DAY",
        "first_in": "09:00:00",
        "last_out": "17:30:00",
        "reason": "Testing future date override rejection"
    }
    fut_res = requests.post(f"{BASE_URL}/attendance/manual-correction", json=future_date_payload, headers={"Authorization": f"Bearer {sup_token}"})
    print(f"Future date correction response code: {fut_res.status_code}")
    print(f"Future date correction response detail: {fut_res.json()}")
    assert fut_res.status_code == 400, "Backend must reject future date corrections with 400"
    assert "future dates" in fut_res.json()["detail"].lower()

    # 6. Test Attendance Override Current Date Time Restrictions
    print("\n--- 6. Attendance Override Current Date Time Restrictions ---")
    today = date.today().isoformat()
    future_time_payload = {
        "employee_id": sup_emps[0]["employee_id"],
        "attendance_date": today,
        "status": "FULL_DAY",
        "first_in": "09:00:00",
        "last_out": "23:59:00",  # future time
        "reason": "Testing future time rejection"
    }
    fut_time_res = requests.post(f"{BASE_URL}/attendance/manual-correction", json=future_time_payload, headers={"Authorization": f"Bearer {sup_token}"})
    print(f"Future time response code: {fut_time_res.status_code}")
    print(f"Future time response detail: {fut_time_res.json()}")
    assert fut_time_res.status_code == 400, "Backend must reject future time corrections for today"

    # Current date in-progress shift (no checkout / incomplete period)
    in_progress_payload = {
        "employee_id": sup_emps[0]["employee_id"],
        "attendance_date": today,
        "status": "FULL_DAY",
        "first_in": "08:00:00",
        "last_out": None,
        "reason": "Testing in progress shift rejection"
    }
    in_prog_res = requests.post(f"{BASE_URL}/attendance/manual-correction", json=in_progress_payload, headers={"Authorization": f"Bearer {sup_token}"})
    print(f"In-progress shift response code: {in_prog_res.status_code}")
    print(f"In-progress shift response detail: {in_prog_res.json()}")
    assert in_prog_res.status_code == 400, "Backend must reject incomplete in-progress shift marking for today"

    # 7. Test Attendance Override Past Date Valid Correction
    print("\n--- 7. Attendance Override Past Date Valid Correction ---")
    past_date = (date.today() - timedelta(days=3)).isoformat()
    valid_past_payload = {
        "employee_id": sup_emps[0]["employee_id"],
        "attendance_date": past_date,
        "status": "FULL_DAY",
        "first_in": "09:00:00",
        "last_out": "17:30:00",
        "reason": "Valid past attendance override verification"
    }
    past_res = requests.post(f"{BASE_URL}/attendance/manual-correction", json=valid_past_payload, headers={"Authorization": f"Bearer {sup_token}"})
    print(f"Past date valid correction response code: {past_res.status_code}")
    assert past_res.status_code == 200, f"Past date valid correction failed: {past_res.text}"
    print(f"Past date correction response: {past_res.json().get('message') or past_res.json()}")

    # 8. Test Employee Lookup (Add Employee details fetching)
    print("\n--- 8. Add Employee Lookup & Details Fetching ---")
    lookup_res = requests.get(f"{BASE_URL}/employees/lookup/{sup_emps[0]['employee_id']}", headers={"Authorization": f"Bearer {sup_token}"})
    print(f"Lookup status code: {lookup_res.status_code}")
    assert lookup_res.status_code == 200, f"Lookup failed: {lookup_res.text}"
    lookup_data = lookup_res.json()
    print(f"Retrieved employee: {lookup_data.get('employee_name')} | Dept: {lookup_data.get('department')} | Team: {lookup_data.get('team_name') or lookup_data.get('teamName')}")

    # Non-existent employee lookup
    not_found_res = requests.get(f"{BASE_URL}/employees/lookup/NONEXISTENT9999", headers={"Authorization": f"Bearer {sup_token}"})
    print(f"Nonexistent lookup status: {not_found_res.status_code}")
    assert not_found_res.status_code == 404, "Nonexistent employee lookup must return 404"

    # 9. Test Audit Logs Accessibility (Superior Only)
    print("\n--- 9. Audit Logs RBAC ---")
    sup_audit = requests.get(f"{BASE_URL}/audit/logs", headers={"Authorization": f"Bearer {sup_token}"})
    assert sup_audit.status_code == 200, "Superior must have access to audit logs"
    hr_audit = requests.get(f"{BASE_URL}/audit/logs", headers={"Authorization": f"Bearer {hr_token}"})
    assert hr_audit.status_code == 403, "HR must be blocked from audit logs (HTTP 403)"
    print("[PASS] Superior allowed, HR blocked with 403 from audit logs")

    print("\n==================================================")
    print("ALL VERIFICATION TESTS COMPLETED SUCCESSFULLY!")
    print("==================================================")

if __name__ == "__main__":
    run_tests()
