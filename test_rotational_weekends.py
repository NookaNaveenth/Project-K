import sys
import sqlite3
import datetime
from fastapi.testclient import TestClient
from api import app
from attendance import (
    ROTATIONAL_WEEKEND_OPTIONS,
    get_weekend_days_for_rotation,
    normalize_rotational_weekend,
    create_session,
    get_employee,
    get_employee_attendance_history,
    calculate_attendance_status,
)
import report_service

client = TestClient(app)

def run_tests():
    print("=" * 60)
    print("RUNNING ROTATIONAL WEEKENDS COMPREHENSIVE VERIFICATION")
    print("=" * 60)

    # 1. Verify ROTATIONAL_WEEKEND_OPTIONS
    expected_options = [
        "Monday – Tuesday",
        "Tuesday – Wednesday",
        "Wednesday – Thursday",
        "Thursday – Friday",
        "Friday – Saturday",
        "Saturday – Sunday",
        "Sunday – Monday",
    ]
    assert len(ROTATIONAL_WEEKEND_OPTIONS) == 7, f"Expected 7 options, got {len(ROTATIONAL_WEEKEND_OPTIONS)}"
    assert ROTATIONAL_WEEKEND_OPTIONS == expected_options, f"Options mismatch: {ROTATIONAL_WEEKEND_OPTIONS}"
    print("[PASS] 1. All 7 rotational weekend options defined correctly.")

    # 2. Verify weekday mapping for all 7 options
    # In Python date.weekday(): 0=Mon, 1=Tue, 2=Wed, 3=Thu, 4=Fri, 5=Sat, 6=Sun
    expected_mappings = {
        "Monday – Tuesday": {0, 1},
        "Tuesday – Wednesday": {1, 2},
        "Wednesday – Thursday": {2, 3},
        "Thursday – Friday": {3, 4},
        "Friday – Saturday": {4, 5},
        "Saturday – Sunday": {5, 6},
        "Sunday – Monday": {6, 0},
        "": {5, 6},
        None: {5, 6},
    }
    for opt, expected_days in expected_mappings.items():
        mapped = get_weekend_days_for_rotation(opt)
        assert mapped == expected_days, f"Mapping failed for {opt}: expected {expected_days}, got {mapped}"
    print("[PASS] 2. Weekday mapping for all 7 combinations + defaults validated.")

    # Create admin auth headers
    token = create_session("admin", "admin", "ALL")
    headers = {"Authorization": f"Bearer {token}"}

    # Pick an existing test employee, e.g. 9615
    test_emp_id = "9615"
    orig_emp = get_employee(test_emp_id)
    assert orig_emp is not None, f"Employee {test_emp_id} not found in DB."
    orig_rotational = orig_emp.get("rotational_weekend")

    try:
        # 3. Test saving, retrieving, updating, and removing each of the 7 combinations
        for idx, option in enumerate(ROTATIONAL_WEEKEND_OPTIONS, 1):
            print(f"\n--- Testing Combination {idx}/7: '{option}' ---")
            
            # A. Save via PUT /employees/{id}/shift
            payload = {
                "shift_start": "09:00",
                "shift_end": "18:00",
                "is_flexible_shift": False,
                "rotational_weekend": option,
            }
            res = client.put(f"/employees/{test_emp_id}/shift", json=payload, headers=headers)
            assert res.status_code == 200, f"Save failed for {option}: {res.text}"
            res_data = res.json()
            assert res_data["employee"]["rotational_weekend"] == option, f"Returned mismatch: {res_data}"
            print(f"  [PASS] Saved '{option}' successfully.")

            # B. Retrieve via GET /employees/{id} and verify persistence in DB
            emp_db = get_employee(test_emp_id)
            assert emp_db["rotational_weekend"] == option, f"DB mismatch: {emp_db['rotational_weekend']}"

            # C. Retrieve via GET /employees list
            res_list = client.get("/employees", headers=headers)
            assert res_list.status_code == 200
            all_emps = res_list.json()
            found_emp = next((e for e in all_emps if str(e["employee_id"]) == test_emp_id), None)
            assert found_emp is not None
            assert found_emp["rotational_weekend"] == option, f"List API mismatch: {found_emp['rotational_weekend']}"
            print(f"  [PASS] Retrieved and verified persistence in DB and GET /employees.")

            # D. Test attendance calendar display and status logic for this rotation
            weekend_weekdays = get_weekend_days_for_rotation(option)
            year = 2026
            month = 11  # Nov 2026
            history_result = get_employee_attendance_history(test_emp_id, year, month)
            assert history_result is not None
            assert history_result["employee"]["rotational_weekend"] == option
            history_records = history_result["attendance"]
            assert len(history_records) >= 30, f"History records missing for {year}-{month}"

            for rec in history_records:
                d = datetime.date.fromisoformat(rec["date"])
                if d.weekday() in weekend_weekdays:
                    # If this date is on the employee's rotational weekend and no actual check-in occurred:
                    if not rec.get("first_in") and not rec.get("worked_minutes"):
                        assert rec["status"] == "WEEKEND", (
                            f"Expected WEEKEND for {rec['date']} (weekday {d.weekday()}) with rotation '{option}', got {rec['status']}"
                        )
            print(f"  [PASS] Attendance history correctly marked rotational off-days as 'WEEKEND'.")

        # 4. Test Updating the configuration
        print("\n--- Testing Updating Configuration ---")
        update_payload = {
            "shift_start": "10:00",
            "shift_end": "19:00",
            "is_flexible_shift": True,
            "rotational_weekend": "Wednesday – Thursday",
        }
        res_upd = client.put(f"/employees/{test_emp_id}/shift", json=update_payload, headers=headers)
        assert res_upd.status_code == 200
        assert res_upd.json()["employee"]["rotational_weekend"] == "Wednesday – Thursday"
        assert res_upd.json()["employee"]["is_flexible_shift"] is True
        print("[PASS] Configuration updated successfully across different shift schedules (flexible shift).")

        # 5. Test Removing the configuration (setting to empty string or None)
        print("\n--- Testing Removing Configuration ---")
        remove_payload = {
            "shift_start": "09:00",
            "shift_end": "18:00",
            "is_flexible_shift": False,
            "rotational_weekend": "",
        }
        res_rem = client.put(f"/employees/{test_emp_id}/shift", json=remove_payload, headers=headers)
        assert res_rem.status_code == 200
        assert res_rem.json()["employee"]["rotational_weekend"] is None
        emp_cleared = get_employee(test_emp_id)
        assert emp_cleared["rotational_weekend"] is None
        print("[PASS] Configuration removed successfully, reverting to standard Saturday-Sunday.")

        # 6. Test Validation: Invalid rotation combinations must be rejected
        print("\n--- Testing Input Validation ---")
        invalid_payload = {
            "shift_start": "09:00",
            "shift_end": "18:00",
            "rotational_weekend": "Monday – Wednesday",  # Non-consecutive / invalid
        }
        res_inv = client.put(f"/employees/{test_emp_id}/shift", json=invalid_payload, headers=headers)
        assert res_inv.status_code == 400, f"Expected 400 Bad Request, got {res_inv.status_code}"
        assert "Invalid rotational weekend" in res_inv.json()["detail"]
        print("[PASS] Invalid combinations correctly rejected with 400 Bad Request.")

        # 7. Test Attendance Precedence & Edge Cases
        print("\n--- Testing Attendance Priority & Precedence ---")
        # Configure Wednesday – Thursday as rotational weekend
        client.put(f"/employees/{test_emp_id}/shift", json={
            "shift_start": "09:00",
            "shift_end": "18:00",
            "is_flexible_shift": False,
            "rotational_weekend": "Wednesday – Thursday",
        }, headers=headers)

        # A. Actual check-in on a weekly off day MUST be preserved!
        # When worked_minutes > 450 on a weekend -> FULL_DAY / PRESENT
        status_worked_weekend = calculate_attendance_status(worked_minutes=480, is_leave=False, is_weekend=True)
        assert status_worked_weekend == "FULL_DAY", f"Expected FULL_DAY for worked weekend, got {status_worked_weekend}"

        # When worked_minutes >= 240 on a weekend -> HALF_DAY
        status_half_weekend = calculate_attendance_status(worked_minutes=300, is_leave=False, is_weekend=True)
        assert status_half_weekend == "HALF_DAY", f"Expected HALF_DAY for worked weekend, got {status_half_weekend}"

        # When worked_minutes == 0 or None on weekend -> WEEKEND
        status_no_work_weekend = calculate_attendance_status(worked_minutes=0, is_leave=False, is_weekend=True)
        assert status_no_work_weekend == "WEEKEND", f"Expected WEEKEND for unworked weekend, got {status_no_work_weekend}"

        print("[PASS] Actual attendance check-in on weekly off days is preserved (FULL_DAY / HALF_DAY).")

        # B. Exclusion from absent count:
        # Verify unworked weekend days are never marked as ABSENT
        assert status_no_work_weekend != "ABSENT"
        print("[PASS] Weekly off days are excluded from absent calculations.")

        # 8. Test Excel Report Generation
        print("\n--- Testing Excel Report Export for Rotational Weekends ---")
        # Generate monthly report for employee with Tuesday – Wednesday rotation
        client.put(f"/employees/{test_emp_id}/shift", json={
            "shift_start": "09:00",
            "shift_end": "18:00",
            "is_flexible_shift": False,
            "rotational_weekend": "Tuesday – Wednesday",
        }, headers=headers)

        import io
        from openpyxl import load_workbook

        excel_bytes, filename = report_service.create_employee_report(test_emp_id, period="month", selected_date="2026-11-01")
        assert len(excel_bytes) > 0, "Excel output is empty"
        assert filename.endswith(".xlsx"), f"Unexpected filename: {filename}"
        wb = load_workbook(io.BytesIO(excel_bytes))
        ws_monthly = wb.worksheets[0]
        assert ws_monthly is not None

        # Check cells corresponding to days of month
        # In Nov 2026:
        # Nov 1 = Sun, Nov 2 = Mon, Nov 3 = Tue, Nov 4 = Wed
        # For Tuesday – Wednesday rotation:
        # Nov 3 (Tue) and Nov 4 (Wed) should be off-days ('W' with style STYLE_WEEK_OFF)
        # Nov 1 (Sun) and Nov 2 (Mon) are working days!
        cell_nov_3 = ws_monthly.cell(row=3, column=9 + 3)  # columns 10..40 correspond to days 1..31
        cell_nov_4 = ws_monthly.cell(row=3, column=9 + 4)
        print(f"  Nov 3 (Tue) cell value: '{cell_nov_3.value}', Nov 4 (Wed) cell value: '{cell_nov_4.value}'")
        assert cell_nov_3.value == "W", f"Expected 'W' for Tuesday off-day, got {cell_nov_3.value}"
        assert cell_nov_4.value == "W", f"Expected 'W' for Wednesday off-day, got {cell_nov_4.value}"

        # Verify summary columns (Columns 41 to 47):
        # Col 41 (AO): Present
        # Col 42 (AP): Half Day
        # Col 43 (AQ): Actual Working Days (22 for Nov 2026 with 8 weekend days)
        # Col 44 (AR): Tot. Leaves
        # Col 45 (AS): Holidays
        # Col 46 (AT): Week ends (8 for Nov 2026 with Tue-Wed rotation)
        # Col 47 (AU): Total Days in Month (30)
        col_actual_working = ws_monthly.cell(row=3, column=43).value
        col_weekends = ws_monthly.cell(row=3, column=46).value
        col_total_days = ws_monthly.cell(row=3, column=47).value
        print(f"  Summary - Actual Working Days: {col_actual_working}, Weekends: {col_weekends}, Total Month Days: {col_total_days}")
        assert col_weekends == 8, f"Expected 8 weekends in Nov 2026, got {col_weekends}"
        assert col_actual_working == 22, f"Expected 22 actual working days in Nov 2026, got {col_actual_working}"
        assert col_actual_working + col_weekends == 30, "Working days + weekends must equal 30"
        print("[PASS] Excel report reflects correct weekly off ('W') and monthly totals for rotational weekend.")

    finally:
        # Restore original state of employee
        client.put(f"/employees/{test_emp_id}/shift", json={
            "shift_start": orig_emp.get("shift_start") or "14:00",
            "shift_end": orig_emp.get("shift_end") or "22:00",
            "is_flexible_shift": bool(orig_emp.get("is_flexible_shift")),
            "rotational_weekend": orig_rotational or "",
        }, headers=headers)
        print(f"\n[CLEANUP] Restored employee {test_emp_id} to original state (rotational_weekend={orig_rotational}).")

    print("\n" + "=" * 60)
    print("ALL ROTATIONAL WEEKEND TESTS PASSED SUCCESSFULLY!")
    print("=" * 60)

if __name__ == "__main__":
    run_tests()
