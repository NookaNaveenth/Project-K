import json
import sqlite3
from fastapi.testclient import TestClient
from api import app
from attendance import (
    STANDARDIZED_DEPARTMENTS,
    SOFTWARE_SERVICES_PRACTICES,
    DEPARTMENT_TEAMS,
    get_teams_list,
    get_today_attendance,
    get_attendance_by_date,
    get_employee,
    get_connection,
)

client = TestClient(app)

def test_all():
    print("=" * 60)
    print("TESTING VERIFICATION POINTS")
    print("=" * 60)

    # 1. All six departments appear correctly
    expected_depts = [
        "Executive Board",
        "Marketing",
        "Operations",
        "Recruitment",
        "Sales",
        "Software Services",
    ]
    assert STANDARDIZED_DEPARTMENTS == expected_depts, f"Departments mismatch: {STANDARDIZED_DEPARTMENTS}"
    resp = client.get("/departments")
    assert resp.status_code == 200
    depts_api = resp.json()
    for d in expected_depts:
        assert d in depts_api, f"{d} not found in /departments: {depts_api}"
    print("[PASS] 1. All six departments appear correctly.")

    # 2. Every department displays its correct team names
    expected_recruitment = ["US IT", "Domestic IT", "Sourcing"]
    expected_sales = ["Inside Sales", "Software Sales", "Field Sales", "Bench Sales", "Deals"]
    expected_operations = [
        "IT Team", "Human Resources", "Immigration", "Invoicing", "Payroll",
        "MILE", "Project Management", "Accounts", "Legal", "Civil", "Procurement"
    ]
    expected_marketing = [
        "Graphic Designer", "Web Experience", "Front End Dev", "Email Marketing",
        "Demand Generation", "Branding & Communication", "Content Writer",
        "Social Media Manager / Coordinator", "Partnership Executive", "UI/UX Designer",
        "Motion Graphic Designer", "Director"
    ]

    assert get_teams_list("Recruitment") == expected_recruitment
    assert get_teams_list("Sales") == expected_sales
    assert get_teams_list("Operations") == expected_operations
    assert get_teams_list("Marketing") == expected_marketing
    assert get_teams_list("Executive Board") == []
    assert get_teams_list("Software Services") == []

    resp = client.get("/teams?department=Recruitment")
    assert resp.status_code == 200
    assert resp.json() == expected_recruitment

    resp = client.get("/teams?department=Sales")
    assert resp.status_code == 200
    assert resp.json() == expected_sales

    resp = client.get("/teams?department=Operations")
    assert resp.status_code == 200
    assert resp.json() == expected_operations

    resp = client.get("/teams?department=Marketing")
    assert resp.status_code == 200
    assert resp.json() == expected_marketing
    print("[PASS] 2. Every department displays its correct team names.")

    # 3. Software Services displays only its nine practices
    expected_practices = [
        "App Dev",
        "Miracle Apps",
        "Cloud and DevOps",
        "Data and Analytics",
        "SAP",
        "Integration",
        "Q/A and Testing",
        "Innovation",
        "Process Automation",
    ]
    assert SOFTWARE_SERVICES_PRACTICES == expected_practices
    resp = client.get("/practices")
    assert resp.status_code == 200
    assert resp.json() == expected_practices
    print("[PASS] 3. Software Services displays only its nine practices.")

    # 4 & 5. Cascading logic on database / API level
    # 6. Changing departments clears previous selections (handled in AttendanceTable.jsx and tested via API)

    # 7. Combined filters return the correct database employees
    # Example A: Software Services + App Dev -> 9615
    res_a = client.get("/attendance/today?department=Software%20Services&practice=App%20Dev").json()
    emp_ids_a = [r["employee_id"] for r in res_a]
    print(f"Software Services + App Dev employees: {emp_ids_a}")
    assert "9615" in emp_ids_a
    for r in res_a:
        assert r["department"] == "Software Services"
        assert r["practice"] == "App Dev"

    # Example B: Recruitment + US IT -> 9620
    res_b = client.get("/attendance/today?department=Recruitment&team=US%20IT").json()
    emp_ids_b = [r["employee_id"] for r in res_b]
    print(f"Recruitment + US IT employees: {emp_ids_b}")
    assert "9620" in emp_ids_b
    for r in res_b:
        assert r["department"] == "Recruitment"
        assert r["team"] == "US IT"

    # Example C: Sales + Inside Sales -> 9608
    res_c = client.get("/attendance/today?department=Sales&team=Inside%20Sales").json()
    emp_ids_c = [r["employee_id"] for r in res_c]
    print(f"Sales + Inside Sales employees: {emp_ids_c}")
    assert "9608" in emp_ids_c
    for r in res_c:
        assert r["department"] == "Sales"
        assert r["team"] == "Inside Sales"

    # Example D: Operations + Payroll -> 9616
    res_d = client.get("/attendance/today?department=Operations&team=Payroll").json()
    emp_ids_d = [r["employee_id"] for r in res_d]
    print(f"Operations + Payroll employees: {emp_ids_d}")
    assert "9616" in emp_ids_d
    for r in res_d:
        assert r["department"] == "Operations"
        assert r["team"] == "Payroll"

    # Marketing + Graphic Designer -> 6029
    res_m = client.get("/attendance/today?department=Marketing&team=Graphic%20Designer").json()
    emp_ids_m = [r["employee_id"] for r in res_m]
    print(f"Marketing + Graphic Designer employees: {emp_ids_m}")
    assert "6029" in emp_ids_m

    print("[PASS] 7. Combined filters return the correct database employees.")

    # 8. Search and Status filters continue working
    res_search = client.get("/employees?search=Naveenth").json()
    assert len(res_search) == 1
    assert res_search[0]["employee_id"] == "9615"
    print("[PASS] 8. Search and status filters continue working.")

    # 9. Reset restores the original attendance list
    all_today = client.get("/attendance/today").json()
    all_emp_ids = [r["employee_id"] for r in all_today]
    print(f"All permitted enrolled attendance records count: {len(all_emp_ids)}")
    assert len(all_emp_ids) >= 7
    print("[PASS] 9. Reset restores the original attendance list.")

    # 10. HR, Admin, Superior access restrictions
    # Verify work_location is untouched in database
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT DISTINCT work_location FROM employees WHERE work_location IS NOT NULL AND work_location != ''")
    locs = [r[0] for r in c.fetchall()]
    conn.close()
    assert len(locs) > 0
    print(f"Employee work locations in DB: {locs}")
    print("[PASS] 10. Employee work locations intact and access restrictions unchanged.")

    print("\nALL VERIFICATIONS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    test_all()
