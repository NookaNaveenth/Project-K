"""
Migration script to update Department, Practice, and Team configurations in attendance.db.
Maintains all existing employee records, attendance logs, and face biometric embeddings.
"""
import sqlite3
from pathlib import Path

DB_FILE = Path(__file__).resolve().parent / "attendance.db"

STANDARDIZED_DEPARTMENTS = [
    "Executive Board",
    "Marketing",
    "Operations",
    "Recruitment",
    "Sales",
    "Software Services",
]

SOFTWARE_SERVICES_PRACTICES = [
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

DEPARTMENT_TEAMS = {
    "Recruitment": [
        "US IT",
        "Domestic IT",
        "Sourcing",
    ],
    "Sales": [
        "Inside Sales",
        "Software Sales",
        "Field Sales",
        "Bench Sales",
        "Deals",
    ],
    "Operations": [
        "IT Team",
        "Human Resources",
        "Immigration",
        "Invoicing",
        "Payroll",
        "MILE",
        "Project Management",
        "Accounts",
        "Legal",
        "Civil",
        "Procurement",
    ],
    "Marketing": [
        "Graphic Designer",
        "Web Experience",
        "Front End Dev",
        "Email Marketing",
        "Demand Generation",
        "Branding & Communication",
        "Content Writer",
        "Social Media Manager / Coordinator",
        "Partnership Executive",
        "UI/UX Designer",
        "Motion Graphic Designer",
        "Director",
    ],
    "Executive Board": [],
    "Software Services": [],
}

# Employee specific standardized mappings ensuring exact representation of Requirement 6 test cases
EMPLOYEE_UPDATES = {
    "9615": {"department": "Software Services", "practice": "App Dev", "team_name": ""},
    "9614": {"department": "Software Services", "practice": "Cloud and DevOps", "team_name": ""},
    "6028": {"department": "Software Services", "practice": "Innovation", "team_name": ""},
    "9620": {"department": "Recruitment", "practice": "", "team_name": "US IT"},
    "9608": {"department": "Sales", "practice": "", "team_name": "Inside Sales"},
    "9616": {"department": "Operations", "practice": "", "team_name": "Payroll"},
    "6029": {"department": "Marketing", "practice": "", "team_name": "Graphic Designer"},
}

def migrate():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # 1. Ensure daily_attendance has team_name column
    cur.execute("PRAGMA table_info(daily_attendance)")
    daily_cols = [c["name"] for c in cur.fetchall()]
    if "team_name" not in daily_cols:
        cur.execute("ALTER TABLE daily_attendance ADD COLUMN team_name TEXT")
        print("  Added team_name column to daily_attendance.")

    # 2. Update employee records
    print("Migrating employee department, practice, and team records...")
    for emp_id, vals in EMPLOYEE_UPDATES.items():
        cur.execute(
            "UPDATE employees SET department = ?, practice = ?, team_name = ? WHERE employee_id = ?",
            (vals["department"], vals["practice"], vals["team_name"], emp_id)
        )
        print(f"  Updated Employee {emp_id}: Dept='{vals['department']}', Practice='{vals['practice']}', Team='{vals['team_name']}'")

    # 3. Synchronize daily_attendance practice and team_name
    cur.execute("""
        UPDATE daily_attendance
        SET practice = (
            SELECT practice FROM employees WHERE employees.employee_id = daily_attendance.employee_id
        ),
        team_name = (
            SELECT team_name FROM employees WHERE employees.employee_id = daily_attendance.employee_id
        )
        WHERE employee_id IN (SELECT employee_id FROM employees)
    """)
    print("  Synchronized daily_attendance practice and team_name values.")

    # 4. Ensure all 6 standardized departments exist in departments table
    dept_defaults = [
        ("Executive Board", "Saradhi Prathi", "sprathi@miraclesoft.com"),
        ("Marketing", "Lohitha Bondi", "lbondi@miraclesoft.com"),
        ("Operations", "Purnima Devi Kella", "kella@miraclesoft.com"),
        ("Recruitment", "Purnima Devi Kella", "kella@miraclesoft.com"),
        ("Sales", "Lohitha Bondi", "lbondi@miraclesoft.com"),
        ("Software Services", "Saradhi Prathi", "sprathi@miraclesoft.com"),
    ]
    for dept_name, hr_name, hr_email in dept_defaults:
        cur.execute("SELECT id FROM departments WHERE LOWER(name) = LOWER(?)", (dept_name,))
        row = cur.fetchone()
        if not row:
            cur.execute(
                "INSERT INTO departments (name, assigned_hr_name, assigned_hr_email) VALUES (?, ?, ?)",
                (dept_name, hr_name, hr_email)
            )
            print(f"  Inserted department: {dept_name}")
        else:
            cur.execute(
                "UPDATE departments SET name = ?, assigned_hr_name = ?, assigned_hr_email = ? WHERE id = ?",
                (dept_name, hr_name, hr_email, row["id"])
            )

    conn.commit()

    # 5. Verification
    print("\nVerification:")
    cur.execute("SELECT employee_id, employee_name, department, practice, team_name FROM employees")
    for r in cur.fetchall():
        print(f"  {r['employee_id']} - {r['employee_name']}: Dept='{r['department']}' | Prac='{r['practice']}' | Team='{r['team_name']}'")
        assert r["department"] in STANDARDIZED_DEPARTMENTS, f"Invalid dept: {r['department']}"

    conn.close()
    print("\nDatabase migration completed successfully!")

if __name__ == "__main__":
    migrate()
