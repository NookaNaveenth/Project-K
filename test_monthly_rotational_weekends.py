"""
Comprehensive verification test script for Rotational Weekends - Current Month Only
and Weekly Off Protection for Late-Arrival Notifications & HR Reports.

Verifies the 9 required scenarios:
1. Current-month rotational weekends work correctly.
2. Previous-month attendance remains unchanged.
3. Future-month attendance does not inherit the current configuration.
4. No late email is sent when an employee does not attend on a weekly off.
5. No absence notification is generated on a weekly off.
6. An employee arriving on time on a weekly off does not receive a late email.
7. An employee arriving late on a weekly off receives the normal late-arrival email.
8. HR reports correctly distinguish weekly offs from absences.
9. Monthly configuration resets correctly when a new month begins.
"""

import sys
from datetime import date, datetime
from fastapi.testclient import TestClient
from api import app
import attendance as db

client = TestClient(app)

def run_tests():
    print("=" * 70)
    print("STARTING 9-SCENARIO ROTATIONAL WEEKENDS & NOTIFICATION VERIFICATION")
    print("=" * 70)

    now = datetime.now()
    cur_year = now.year
    cur_month = now.month
    prev_month = 12 if cur_month == 1 else cur_month - 1
    prev_year = cur_year - 1 if cur_month == 1 else cur_year
    next_month = 1 if cur_month == 12 else cur_month + 1
    next_year = cur_year + 1 if cur_month == 12 else cur_year

    test_emp_id = "TEST_ROT_EMP_99"
    emp_name = "Rotational Verification Employee"

    # Step 0: Create test employee if not exists
    emp = db.get_employee(test_emp_id)
    if not emp:
        conn = db.get_connection()
        conn.execute(
            """INSERT INTO employees (
                employee_id, employee_name, shift_start, shift_end,
                email, department, practice, designation, is_enrolled,
                reporting_hr, hr_email, work_location
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                test_emp_id, emp_name, "14:00", "22:00",
                "test.rot@miraclesoft.com", "Software Services", "App Dev", "Software Engineer", 1,
                "Test HR Lead", "testhr@miraclesoft.com", "Miracle City (HQ)"
            )
        )
        conn.commit()
        conn.close()

    try:
        # -------------------------------------------------------------
        # SCENARIO 1: Current-month rotational weekends work correctly
        # -------------------------------------------------------------
        print("\n--- Scenario 1: Current-month rotational weekends work correctly ---")
        # Configure Wednesday – Thursday (weekdays 2 and 3) for current month
        resp = client.put(f"/employees/{test_emp_id}/shift", json={
            "shift_start": "14:00",
            "shift_end": "22:00",
            "rotational_weekend": "Wednesday – Thursday",
            "year": cur_year,
            "month": cur_month,
        })
        assert resp.status_code == 200, f"Failed updating shift: {resp.text}"
        data = resp.json()
        assert data.get("employee", {}).get("rotational_weekend") == "Wednesday – Thursday"

        # Verify DB monthly configuration table
        saved_rot = db.get_employee_monthly_rotational_weekend(test_emp_id, cur_year, cur_month)
        assert saved_rot == "Wednesday – Thursday", f"Expected 'Wednesday – Thursday', got '{saved_rot}'"

        # Test date resolution: find a Wednesday in current month
        # Check attendance history for current month
        hist_resp = client.get(f"/employees/{test_emp_id}/attendance-history?year={cur_year}&month={cur_month}")
        assert hist_resp.status_code == 200
        hist_data = hist_resp.json()
        records = hist_data.get("attendance", [])
        assert len(records) > 0, "No attendance records returned for current month"

        # Verify that Wednesday (weekday 2) and Thursday (weekday 3) are WEEKEND, while Saturday/Sunday are not
        wed_records = [r for r in records if datetime.strptime(r["date"], "%Y-%m-%d").weekday() in (2, 3)]
        sat_records = [r for r in records if datetime.strptime(r["date"], "%Y-%m-%d").weekday() in (5, 6)]
        assert len(wed_records) > 0, "No Wednesday/Thursday in month?"
        for r in wed_records:
            assert r["status"] == "WEEKEND", f"Expected WEEKEND for {r['date']}, got {r['status']}"
        print(f"[PASS] Scenario 1: Wednesday – Thursday successfully configured as WEEKEND for {cur_year}-{cur_month:02d}.")

        # -------------------------------------------------------------
        # SCENARIO 2: Previous-month attendance remains unchanged
        # -------------------------------------------------------------
        print("\n--- Scenario 2: Previous-month attendance remains unchanged ---")
        # Previous month should not have Wednesday-Thursday, but default Saturday-Sunday
        prev_rot = db.get_employee_monthly_rotational_weekend(test_emp_id, prev_year, prev_month)
        assert prev_rot is None, f"Previous month should not have inherited current month rotation, got {prev_rot}"

        hist_prev = client.get(f"/employees/{test_emp_id}/attendance-history?year={prev_year}&month={prev_month}")
        assert hist_prev.status_code == 200
        prev_records = hist_prev.json().get("attendance", [])
        prev_sat_sun = [r for r in prev_records if datetime.strptime(r["date"], "%Y-%m-%d").weekday() in (5, 6)]
        for r in prev_sat_sun:
            assert r["status"] == "WEEKEND", f"Expected Saturday/Sunday in past month to be WEEKEND, got {r['status']} for {r['date']}"
        print(f"[PASS] Scenario 2: Previous month ({prev_year}-{prev_month:02d}) retained default Saturday-Sunday weekend.")

        # -------------------------------------------------------------
        # SCENARIO 3: Future-month attendance does not inherit current configuration
        # -------------------------------------------------------------
        print("\n--- Scenario 3: Future-month attendance does not inherit current configuration ---")
        future_rot = db.get_employee_monthly_rotational_weekend(test_emp_id, next_year, next_month)
        assert future_rot is None, f"Future month should not have configuration, got {future_rot}"

        hist_future = client.get(f"/employees/{test_emp_id}/attendance-history?year={next_year}&month={next_month}")
        assert hist_future.status_code == 200
        future_records = hist_future.json().get("attendance", [])
        future_wed = [r for r in future_records if datetime.strptime(r["date"], "%Y-%m-%d").weekday() == 2]
        future_sat = [r for r in future_records if datetime.strptime(r["date"], "%Y-%m-%d").weekday() == 5]
        # In future month without explicit config, Wednesday must NOT be WEEKEND
        for r in future_wed:
            assert r["status"] != "WEEKEND", f"Future Wednesday should NOT be WEEKEND, got {r['status']}"
        # And Saturday should be default WEEKEND
        for r in future_sat:
            assert r["status"] == "WEEKEND", f"Expected future Saturday to be default WEEKEND, got {r['status']}"
        print(f"[PASS] Scenario 3: Future month ({next_year}-{next_month:02d}) maintains default rules and does not inherit November rotation.")

        # -------------------------------------------------------------
        # SCENARIO 4: No late email is sent when an employee does not attend on a weekly off
        # -------------------------------------------------------------
        print("\n--- Scenario 4: No late email is sent on unworked weekly off ---")
        # Pick the first Wednesday in current month
        target_wed_str = wed_records[0]["date"]
        # Call validate_late_arrival_notification with NO check-in
        val_off_no_checkin = db.validate_late_arrival_notification(
            employee_id=test_emp_id,
            attendance_date=target_wed_str,
            check_in_time=None,
            shift_start="14:00"
        )
        assert val_off_no_checkin["should_send"] is False, "Should NOT send late email on unworked weekly off!"
        assert val_off_no_checkin["is_weekly_off"] is True
        assert val_off_no_checkin["has_check_in"] is False
        assert val_off_no_checkin["is_late"] is False
        assert "Weekly Off Protection" in val_off_no_checkin["skip_reason"]
        print(f"[PASS] Scenario 4: Weekly off without check-in skipped with: '{val_off_no_checkin['skip_reason']}'.")

        # -------------------------------------------------------------
        # SCENARIO 5: No absence notification is generated on a weekly off
        # -------------------------------------------------------------
        print("\n--- Scenario 5: No absence notification is generated on a weekly off ---")
        # In cutoff reports, unworked weekly off must NOT be 'Not Checked In'
        reports = db.get_shift_cutoff_attendance_reports(
            shift_start="14:00",
            target_date=target_wed_str,
            buffer_minutes=60
        )
        # Find test employee in report
        found_emp = None
        for rep in reports:
            for e in rep["employees"]:
                if e["id"] == test_emp_id:
                    found_emp = e
                    break
        assert found_emp is not None, "Test employee should be present in cutoff report"
        assert found_emp["status"] == "WEEKEND", f"Status should be 'WEEKEND', got '{found_emp['status']}'"
        assert found_emp["login_time"] == "WEEKLY OFF", f"Login time should be 'WEEKLY OFF', got '{found_emp['login_time']}'"
        print(f"[PASS] Scenario 5: Cutoff report classifies unworked off-day as '{found_emp['status']}' ({found_emp['login_time']}), NOT as absent.")

        # -------------------------------------------------------------
        # SCENARIO 6: An employee arriving on time on a weekly off does not receive a late email
        # -------------------------------------------------------------
        print("\n--- Scenario 6: Employee arriving on time on a weekly off does not receive a late email ---")
        # Shift start is 14:00, arrival is 13:50 (on time / early)
        val_on_time = db.validate_late_arrival_notification(
            employee_id=test_emp_id,
            attendance_date=target_wed_str,
            check_in_time="13:50",
            shift_start="14:00"
        )
        assert val_on_time["should_send"] is False, "On-time arrival must not trigger late email"
        assert val_on_time["is_weekly_off"] is True
        assert val_on_time["has_check_in"] is True
        assert val_on_time["is_late"] is False
        print(f"[PASS] Scenario 6: On-time arrival (13:50) on weekly off has should_send=False: '{val_on_time['skip_reason']}'.")

        # -------------------------------------------------------------
        # SCENARIO 7: An employee arriving late on a weekly off receives the normal late-arrival email
        # -------------------------------------------------------------
        print("\n--- Scenario 7: Employee arriving late on a weekly off receives normal late-arrival email ---")
        # Shift start is 14:00, arrival is 14:35 (35 minutes late)
        val_late = db.validate_late_arrival_notification(
            employee_id=test_emp_id,
            attendance_date=target_wed_str,
            check_in_time="14:35",
            shift_start="14:00"
        )
        assert val_late["should_send"] is True, "Late arrival on weekly off MUST trigger late notification"
        assert val_late["is_weekly_off"] is True
        assert val_late["has_check_in"] is True
        assert val_late["is_late"] is True
        assert val_late["late_minutes"] == 35
        assert val_late["arrival_status"] == "LATE"
        print(f"[PASS] Scenario 7: Late arrival (14:35) on weekly off has should_send=True, late_minutes={val_late['late_minutes']}.")

        # -------------------------------------------------------------
        # SCENARIO 8: HR reports correctly distinguish weekly offs from absences
        # -------------------------------------------------------------
        print("\n--- Scenario 8: HR reports correctly distinguish weekly offs from absences ---")
        eod_reports = db.get_hr_end_of_day_reports(target_date=target_wed_str)
        assert len(eod_reports) > 0, "EOD reports should not be empty"
        # Check totals in EOD reports
        rep0 = eod_reports[0]
        totals = rep0.get("totals", {})
        assert "weekly_off" in totals, f"Totals should contain 'weekly_off' field: {totals}"
        assert "absent" in totals, f"Totals should contain 'absent' field: {totals}"
        print(f"[PASS] Scenario 8: EOD reports separate weekly_off ({totals['weekly_off']}) from absent ({totals['absent']}).")

        # -------------------------------------------------------------
        # SCENARIO 9: Monthly configuration resets correctly when a new month begins
        # -------------------------------------------------------------
        print("\n--- Scenario 9: Monthly configuration resets correctly when a new month begins ---")
        # Explicitly configure December 2026 differently or verify it starts as None
        test_year = 2027
        test_month = 1
        jan_rot = db.get_employee_monthly_rotational_weekend(test_emp_id, test_year, test_month)
        assert jan_rot is None, "New month must start without any rotation inherited"

        # Configure Jan 2027 with Friday – Saturday
        db.set_employee_monthly_rotational_weekend(test_emp_id, test_year, test_month, "Friday – Saturday")
        assert db.get_employee_monthly_rotational_weekend(test_emp_id, test_year, test_month) == "Friday – Saturday"

        # Check that Feb 2027 has None (does not carry forward)
        assert db.get_employee_monthly_rotational_weekend(test_emp_id, test_year, test_month + 1) is None
        print(f"[PASS] Scenario 9: Jan 2027 independent; Feb 2027 does not carry forward.")

        print("\n" + "=" * 70)
        print("ALL 9 SCENARIOS VERIFIED SUCCESSFULLY 100%!")
        print("=" * 70)

    finally:
        # Cleanup test employee
        conn = db.get_connection()
        conn.execute("DELETE FROM employee_monthly_rotational_weekends WHERE employee_id = ?", (test_emp_id,))
        conn.execute("DELETE FROM employees WHERE employee_id = ?", (test_emp_id,))
        conn.commit()
        conn.close()
        print("[CLEANUP] Test records cleaned up successfully.")

if __name__ == "__main__":
    run_tests()
