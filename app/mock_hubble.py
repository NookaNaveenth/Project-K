import json
import sqlite3
from pathlib import Path

from fastapi import APIRouter, HTTPException


BASE_DIR = Path(__file__).resolve().parents[1]
DATA_FILE = BASE_DIR / "data" / "mock_employees.json"
DB_FILE = BASE_DIR / "attendance.db"
router = APIRouter(prefix="/mock-hubble", tags=["Mock Hubble"])


def load_employees() -> list[dict]:
    try:
        with DATA_FILE.open("r", encoding="utf-8") as file:
            data = json.load(file)
            employees = []
            for item in data:
                if isinstance(item, dict) and "data" in item and isinstance(item["data"], dict):
                    merged = dict(item["data"])
                    employees.append(merged)
                elif isinstance(item, dict):
                    employees.append(item)
            return employees
    except FileNotFoundError as error:
        raise HTTPException(
            status_code=500, detail="mock_employees.json not found"
        ) from error
    except json.JSONDecodeError as error:
        raise HTTPException(
            status_code=500, detail="mock_employees.json contains invalid JSON"
        ) from error


def get_mock_profiles_map() -> dict[str, str]:
    """
    Builds a case-insensitive map of employee ID, loginId, and mailId to profilePic URL.
    """
    try:
        employees = load_employees()
    except Exception:
        employees = []
    
    profiles = {}
    for employee in employees:
        pic = employee.get("profilePic") or employee.get("profile_pic")
        if pic and str(pic).strip() and str(pic).strip().lower() != "none":
            pic_url = str(pic).strip()
            if employee.get("id"):
                profiles[str(employee["id"]).strip().casefold()] = pic_url
            if employee.get("loginId"):
                profiles[str(employee["loginId"]).strip().casefold()] = pic_url
            if employee.get("mailId"):
                profiles[str(employee["mailId"]).strip().casefold()] = pic_url
            if employee.get("personalEmail"):
                profiles[str(employee["personalEmail"]).strip().casefold()] = pic_url
    return profiles


def get_mock_employee_profile_pic(identifier: str | None) -> str | None:
    if not identifier:
        return None
    clean = str(identifier).strip().casefold()
    profiles = get_mock_profiles_map()
    return profiles.get(clean)


@router.get("/employees")
def list_mock_employees():
    """
    Returns full mock employee directory including profilePic links.
    """
    return load_employees()


@router.get("/profile-picture/{identifier}")
def get_employee_profile_picture(identifier: str):
    """
    Returns the profile image URL for an employee by ID, login ID, or email.
    """
    pic = get_mock_employee_profile_pic(identifier)
    return {
        "success": True,
        "identifier": identifier,
        "profilePic": pic,
        "hasProfilePic": bool(pic),
    }


@router.get("/employee/{login_id}")
def get_mock_employee(login_id: str):
    clean = login_id.strip().casefold()
    if not clean:
        raise HTTPException(status_code=400, detail="login_id is required")

    # 1. Search mock employees file
    try:
        employees = load_employees()
    except Exception:
        employees = []

    # First try exact match on loginId, id, or mailId
    for employee in employees:
        emp_login = str(employee.get("loginId", "")).strip().casefold()
        emp_id = str(employee.get("id", "")).strip().casefold()
        emp_mail = str(employee.get("mailId", "")).strip().casefold()
        emp_pmail = str(employee.get("personalEmail", "")).strip().casefold()
        if clean in (emp_login, emp_id, emp_mail, emp_pmail):
            return employee

    # Second try partial / prefix match on loginId, name, or email
    for employee in employees:
        emp_login = str(employee.get("loginId", "")).strip().casefold()
        emp_name = str(employee.get("name", "")).strip().casefold()
        emp_mail = str(employee.get("mailId", "")).strip().casefold()
        if (clean in emp_login) or (clean in emp_name) or (clean in emp_mail):
            return employee

    # 2. Check database for existing employee details
    if DB_FILE.exists():
        try:
            conn = sqlite3.connect(DB_FILE)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM employees
                WHERE LOWER(TRIM(login_id)) = ? OR LOWER(TRIM(employee_id)) = ? OR LOWER(TRIM(email)) = ?
            """, (clean, clean, clean))
            row = cursor.fetchone()
            conn.close()
            if row:
                d = dict(row)
                return {
                    "id": int(d["employee_id"]) if str(d["employee_id"]).isdigit() else d["employee_id"],
                    "name": d.get("employee_name") or "",
                    "mailId": d.get("email") or "",
                    "loginId": d.get("login_id") or login_id,
                    "department": d.get("department") or "",
                    "designation": d.get("designation") or "",
                    "teamName": d.get("team_name") or "",
                    "reportsTo": d.get("reports_to") or "",
                    "reportsToMailId": d.get("reports_to_mail_id") or "",
                    "hrContact": d.get("hr_contact") or d.get("reporting_hr") or "",
                    "hrEmail": d.get("hr_email") or "",
                    "work_location": d.get("work_location") or "Miracle City (HQ)",
                    "shift_start": d.get("shift_start") or "14:00",
                    "shift_end": d.get("shift_end") or "22:00",
                    "is_enrolled": bool(d.get("is_enrolled")),
                }
        except Exception:
            pass

    raise HTTPException(status_code=404, detail="Employee not found in mock Hubble data")


def update_mock_employee(identifier: str, updates: dict) -> dict:
    """
    Updates or inserts employee details in data/mock_employees.json and syncs to SQLite employees table.
    """
    clean_id = str(identifier).strip()
    clean_cf = clean_id.casefold()

    try:
        with DATA_FILE.open("r", encoding="utf-8") as file:
            employees = json.load(file)
    except Exception:
        employees = []

    matched_idx = -1
    for idx, emp in enumerate(employees):
        e_id = str(emp.get("id", "")).strip().casefold()
        e_login = str(emp.get("loginId", "")).strip().casefold()
        e_mail = str(emp.get("mailId", "")).strip().casefold()
        if clean_cf in (e_id, e_login, e_mail):
            matched_idx = idx
            break

    # Map possible key names
    field_mapping = {
        "name": ["name", "employee_name"],
        "profilePic": ["profilePic", "profile_pic"],
        "department": ["department"],
        "practiceName": ["practiceName", "practice"],
        "teamName": ["teamName", "team_name", "team", "sub_practice"],
        "shift_start": ["shift_start"],
        "shift_end": ["shift_end"],
        "hrContact": ["hrContact", "hr_contact", "reporting_hr"],
        "hrEmail": ["hrEmail", "hr_email"],
        "work_location": ["work_location", "location"],
        "mailId": ["mailId", "email"],
        "loginId": ["loginId", "login_id", "username"],
        "designation": ["designation"],
    }

    if matched_idx >= 0:
        target = employees[matched_idx]
    else:
        target = {
            "id": int(clean_id) if clean_id.isdigit() else clean_id,
            "loginId": clean_id,
            "name": clean_id,
            "department": "Software Services",
            "practiceName": "App Dev",
            "teamName": "N/A",
            "shift_start": "09:00",
            "shift_end": "17:00",
            "work_location": "Miracle City (HQ)",
            "profilePic": "",
        }
        employees.append(target)

    for target_key, candidate_keys in field_mapping.items():
        for ck in candidate_keys:
            if ck in updates and updates[ck] is not None:
                target[target_key] = updates[ck]
                break

    # Write back to mock_employees.json
    try:
        with DATA_FILE.open("w", encoding="utf-8") as file:
            json.dump(employees, file, indent=2)
    except Exception as err:
        raise HTTPException(status_code=500, detail=f"Failed to persist mock employee: {err}")

    # Synchronize to SQLite database if employee exists
    if DB_FILE.exists():
        try:
            conn = sqlite3.connect(DB_FILE)
            cursor = conn.cursor()
            db_id = target.get("id") or clean_id
            cursor.execute("SELECT id FROM employees WHERE employee_id = ? OR login_id = ?", (str(db_id), str(target.get("loginId") or clean_id)))
            row = cursor.fetchone()
            if row:
                cursor.execute("""
                    UPDATE employees
                    SET employee_name = COALESCE(?, employee_name),
                        department = COALESCE(?, department),
                        practice = COALESCE(?, practice),
                        team_name = COALESCE(?, team_name),
                        shift_start = COALESCE(?, shift_start),
                        shift_end = COALESCE(?, shift_end),
                        reporting_hr = COALESCE(?, reporting_hr),
                        work_location = COALESCE(?, work_location),
                        profile_pic = COALESCE(?, profile_pic)
                    WHERE employee_id = ? OR login_id = ?
                """, (
                    target.get("name"),
                    target.get("department"),
                    target.get("practiceName"),
                    target.get("teamName"),
                    target.get("shift_start"),
                    target.get("shift_end"),
                    target.get("hrContact"),
                    target.get("work_location"),
                    target.get("profilePic"),
                    str(db_id),
                    str(target.get("loginId") or clean_id),
                ))
                conn.commit()
            conn.close()
        except Exception:
            pass

    return target


@router.put("/employee/{identifier}")
@router.patch("/employee/{identifier}")
def update_mock_employee_endpoint(identifier: str, updates: dict):
    """
    Updates employee record in mock Hubble directory and syncs to database.
    """
    updated = update_mock_employee(identifier, updates)
    return {
        "success": True,
        "message": f"Mock employee {identifier} updated successfully",
        "employee": updated,
    }
