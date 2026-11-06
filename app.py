import base64
import io
import os
import secrets
from datetime import date
from functools import wraps

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import mysql.connector
import numpy as np
import pandas as pd
from dotenv import load_dotenv
from flask import Flask, flash, redirect, render_template, request, session, url_for
from flask_wtf.csrf import CSRFProtect

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY") or secrets.token_hex(32)
CSRFProtect(app)
app.config["DATABASE_CONFIG"] = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", "3306")),
    "database": os.getenv("DB_NAME", "student_placement"),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", ""),
}

STATUSES = ("applied", "interview", "offer", "placed", "rejected")
DEMO_STUDENTS = pd.DataFrame([
    {"department": "Computer Science", "graduation_year": 2026},
    {"department": "Computer Science", "graduation_year": 2026},
    {"department": "Computer Science", "graduation_year": 2026},
    {"department": "Information Technology", "graduation_year": 2026},
    {"department": "Information Technology", "graduation_year": 2026},
    {"department": "Electronics", "graduation_year": 2026},
    {"department": "Electronics", "graduation_year": 2026},
    {"department": "Mechanical", "graduation_year": 2026},
    {"department": "Mechanical", "graduation_year": 2026},
    {"department": "Mechanical", "graduation_year": 2026},
])
DEMO_PLACEMENTS = pd.DataFrame([
    {"department": "Computer Science", "graduation_year": 2026, "student_id": 1, "company": "Northstar Labs", "role": "Software Engineer", "package_lpa": 12.5, "placement_date": date(2026, 3, 10), "status": "placed"},
    {"department": "Computer Science", "graduation_year": 2026, "student_id": 2, "company": "Meridian Systems", "role": "Data Analyst", "package_lpa": 8.0, "placement_date": date(2026, 4, 2), "status": "placed"},
    {"department": "Information Technology", "graduation_year": 2026, "student_id": 4, "company": "Northstar Labs", "role": "QA Engineer", "package_lpa": 7.5, "placement_date": date(2026, 3, 22), "status": "placed"},
    {"department": "Electronics", "graduation_year": 2026, "student_id": 6, "company": "Cirrus Devices", "role": "Embedded Engineer", "package_lpa": 9.0, "placement_date": date(2026, 4, 12), "status": "placed"},
    {"department": "Mechanical", "graduation_year": 2026, "student_id": 8, "company": "Vertex Mobility", "role": "Graduate Engineer", "package_lpa": 6.0, "placement_date": date(2026, 4, 18), "status": "placed"},
    {"department": "Mechanical", "graduation_year": 2026, "student_id": 8, "company": "Aster Manufacturing", "role": "Design Engineer", "package_lpa": 6.8, "placement_date": date(2026, 4, 24), "status": "offer"},
    {"department": "Computer Science", "graduation_year": 2026, "student_id": 3, "company": "Meridian Systems", "role": "Software Engineer", "package_lpa": 10.0, "placement_date": date(2026, 4, 20), "status": "interview"},
])
DEMO_SKILLS = pd.DataFrame([
    {"skill_name": "Python", "student_count": 6},
    {"skill_name": "SQL", "student_count": 5},
    {"skill_name": "JavaScript", "student_count": 4},
    {"skill_name": "Data analysis", "student_count": 4},
    {"skill_name": "Java", "student_count": 3},
])


def get_connection():
    return mysql.connector.connect(**app.config["DATABASE_CONFIG"], connection_timeout=2)


def database_available():
    try:
        connection = get_connection()
        connection.close()
        return True
    except mysql.connector.Error:
        return False


def db_rows(query, params=()):
    connection = get_connection()
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute(query, params)
        return cursor.fetchall()
    finally:
        connection.close()


def db_write(query, params=()):
    connection = get_connection()
    try:
        cursor = connection.cursor()
        cursor.execute(query, params)
        connection.commit()
        return cursor.lastrowid
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("authenticated"):
            return redirect(url_for("login", next=request.path))
        return view(*args, **kwargs)
    return wrapped


def load_analytics(cohort):
    if not database_available():
        students = DEMO_STUDENTS[DEMO_STUDENTS.graduation_year == cohort].copy()
        placements = DEMO_PLACEMENTS[DEMO_PLACEMENTS.graduation_year == cohort].copy()
        skills = DEMO_SKILLS.copy()
        return students, placements, skills, False

    students = pd.DataFrame(db_rows(
        "SELECT student_id, department, graduation_year FROM students WHERE graduation_year = %s",
        (cohort,),
    ), columns=["student_id", "department", "graduation_year"])
    placements = pd.DataFrame(db_rows(
        "SELECT p.student_id, s.department, s.graduation_year, p.company, p.role, "
        "p.package_lpa, p.placement_date, p.status FROM placements p "
        "JOIN students s ON s.student_id = p.student_id WHERE s.graduation_year = %s",
        (cohort,),
    ), columns=["student_id", "department", "graduation_year", "company", "role", "package_lpa", "placement_date", "status"])
    skills = pd.DataFrame(db_rows(
        "SELECT sk.skill_name, COUNT(DISTINCT ss.student_id) AS student_count "
        "FROM skills sk JOIN student_skills ss ON ss.skill_id = sk.skill_id "
        "JOIN students st ON st.student_id = ss.student_id "
        "WHERE st.graduation_year = %s GROUP BY sk.skill_id, sk.skill_name "
        "ORDER BY student_count DESC, sk.skill_name LIMIT 8",
        (cohort,),
    ), columns=["skill_name", "student_count"])
    return students, placements, skills, True


def chart_image(fig):
    output = io.BytesIO()
    fig.savefig(output, format="png", dpi=150, bbox_inches="tight", transparent=True)
    plt.close(fig)
    return base64.b64encode(output.getvalue()).decode("ascii")


def build_charts(students, placements, skills):
    placed = placements[placements.status == "placed"] if not placements.empty else placements
    departments = students.groupby("department").size().rename("eligible").to_frame()
    if not placed.empty:
        departments["placed"] = placed.groupby("department").student_id.nunique()
    else:
        departments["placed"] = 0
    departments = departments.fillna(0).sort_values("eligible", ascending=True)

    fig, axis = plt.subplots(figsize=(7.1, 3.2))
    axis.barh(departments.index, departments.eligible, color="#dce6e2", height=0.56, label="Eligible")
    axis.barh(departments.index, departments.placed, color="#167b68", height=0.56, label="Placed")
    axis.set_xlabel("Students", color="#66756e", fontsize=9)
    axis.tick_params(axis="both", labelsize=9, colors="#53635c", length=0)
    axis.spines[:].set_visible(False)
    axis.grid(axis="x", color="#e7ece9", linewidth=0.8)
    axis.set_axisbelow(True)
    axis.legend(frameon=False, loc="lower right", fontsize=8, ncol=2)
    fig.patch.set_alpha(0)
    department_chart = chart_image(fig)

    packages = placed.groupby("student_id").package_lpa.max().dropna().to_numpy(dtype=float) if not placed.empty else np.array([])
    fig, axis = plt.subplots(figsize=(5.4, 3.2))
    if packages.size:
        axis.hist(packages, bins=min(8, max(3, packages.size)), color="#167b68", edgecolor="#ffffff", linewidth=1.5)
    else:
        axis.text(0.5, 0.5, "No confirmed packages yet", ha="center", va="center", color="#66756e", transform=axis.transAxes)
    axis.set_xlabel("Package (INR LPA)", color="#66756e", fontsize=9)
    axis.set_ylabel("Students", color="#66756e", fontsize=9)
    axis.tick_params(axis="both", labelsize=9, colors="#53635c", length=0)
    axis.spines[:].set_visible(False)
    axis.grid(axis="y", color="#e7ece9", linewidth=0.8)
    axis.set_axisbelow(True)
    fig.patch.set_alpha(0)
    package_chart = chart_image(fig)

    fig, axis = plt.subplots(figsize=(5.4, 3.2))
    if not skills.empty:
        ordered_skills = skills.sort_values("student_count", ascending=True)
        axis.barh(ordered_skills.skill_name, ordered_skills.student_count, color="#bc7043", height=0.58)
    axis.set_xlabel("Students with skill", color="#66756e", fontsize=9)
    axis.tick_params(axis="both", labelsize=9, colors="#53635c", length=0)
    axis.spines[:].set_visible(False)
    axis.grid(axis="x", color="#e7ece9", linewidth=0.8)
    axis.set_axisbelow(True)
    fig.patch.set_alpha(0)
    skill_chart = chart_image(fig)
    return department_chart, package_chart, skill_chart


@app.context_processor
def inject_navigation_state():
    return {"is_authenticated": session.get("authenticated", False)}


@app.get("/")
def dashboard():
    available_years = [2026]
    if database_available():
        rows = db_rows("SELECT DISTINCT graduation_year FROM students ORDER BY graduation_year DESC")
        if rows:
            available_years = [int(row["graduation_year"]) for row in rows]
    try:
        cohort = int(request.args.get("year", available_years[0]))
    except ValueError:
        cohort = available_years[0]
    if cohort not in available_years:
        cohort = available_years[0]

    students, placements, skills, connected = load_analytics(cohort)
    placed = placements[placements.status == "placed"] if not placements.empty else placements
    eligible_count = int(students.student_id.nunique()) if "student_id" in students.columns else len(students)
    placed_count = int(placed.student_id.nunique()) if not placed.empty else 0
    placement_rate = (placed_count / eligible_count * 100) if eligible_count else 0
    packages = placed.groupby("student_id").package_lpa.max().dropna().to_numpy(dtype=float) if not placed.empty else np.array([])
    departments = students.groupby("department").size().rename("eligible").to_frame()
    if not placed.empty:
        departments["placed"] = placed.groupby("department").student_id.nunique()
    else:
        departments["placed"] = 0
    departments = departments.fillna(0)
    departments["rate"] = np.where(departments.eligible > 0, departments.placed / departments.eligible * 100, 0)
    department_rows = departments.sort_values("rate", ascending=False).reset_index().to_dict("records")
    average_package = float(np.mean(packages)) if packages.size else None
    median_package = float(np.median(packages)) if packages.size else None
    top_company = "—"
    if not placed.empty:
        company_counts = placed.groupby("company").student_id.nunique().sort_values(ascending=False)
        top_company = str(company_counts.index[0])
    department_chart, package_chart, skill_chart = build_charts(students, placements, skills)
    return render_template(
        "dashboard.html", cohort=cohort, years=available_years, connected=connected,
        eligible_count=eligible_count, placed_count=placed_count, placement_rate=placement_rate,
        average_package=average_package, median_package=median_package, top_company=top_company,
        department_rows=department_rows, skills=skills.to_dict("records"),
        department_chart=department_chart, package_chart=package_chart, skill_chart=skill_chart,
    )


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = os.getenv("ADMIN_USERNAME", "")
        password = os.getenv("ADMIN_PASSWORD", "")
        if username and password and secrets.compare_digest(request.form.get("username", ""), username) and secrets.compare_digest(
            request.form.get("password", ""), password
        ):
            session.clear()
            session["authenticated"] = True
            next_url = request.args.get("next", "")
            if next_url.startswith("/") and not next_url.startswith("//"):
                return redirect(next_url)
            return redirect(url_for("students"))
        flash("Set ADMIN_USERNAME and ADMIN_PASSWORD in .env, then enter those credentials.", "error")
    return render_template("login.html")


@app.post("/logout")
def logout():
    session.clear()
    return redirect(url_for("dashboard"))


@app.route("/students", methods=["GET", "POST"])
@login_required
def students():
    if request.method == "POST":
        roll_no = request.form.get("roll_no", "").strip()
        department = request.form.get("department", "").strip()
        try:
            graduation_year = int(request.form.get("graduation_year", ""))
            if not roll_no or not department or not 2000 <= graduation_year <= 2100:
                raise ValueError
            student_id = db_write(
                "INSERT INTO students (roll_no, department, graduation_year) VALUES (%s, %s, %s)",
                (roll_no, department, graduation_year),
            )
            raw_skills = request.form.get("skills", "")
            for name in sorted({item.strip() for item in raw_skills.split(",") if item.strip()}):
                skill_id = db_write("INSERT INTO skills (skill_name) VALUES (%s) ON DUPLICATE KEY UPDATE skill_id=LAST_INSERT_ID(skill_id)", (name,))
                db_write("INSERT IGNORE INTO student_skills (student_id, skill_id) VALUES (%s, %s)", (student_id, skill_id))
            flash("Student record added.", "success")
            return redirect(url_for("students"))
        except ValueError:
            flash("Enter a roll number, department, and valid graduation year.", "error")
        except mysql.connector.IntegrityError:
            flash("That roll number is already in the register.", "error")
        except mysql.connector.Error:
            flash("Could not save the student. Check the database connection and schema.", "error")
    connected = database_available()
    rows = db_rows(
        "SELECT s.student_id, s.roll_no, s.department, s.graduation_year, "
        "GROUP_CONCAT(sk.skill_name ORDER BY sk.skill_name SEPARATOR ', ') AS skills "
        "FROM students s LEFT JOIN student_skills ss ON ss.student_id=s.student_id "
        "LEFT JOIN skills sk ON sk.skill_id=ss.skill_id "
        "GROUP BY s.student_id ORDER BY s.graduation_year DESC, s.department, s.roll_no LIMIT 300"
    ) if connected else []
    return render_template("students.html", students=rows, connected=connected, current_year=date.today().year)


@app.post("/students/<int:student_id>/skills")
@login_required
def update_student_skills(student_id):
    skill_names = sorted({item.strip() for item in request.form.get("skills", "").split(",") if item.strip()})
    connection = get_connection()
    try:
        cursor = connection.cursor()
        cursor.execute("SELECT student_id FROM students WHERE student_id = %s", (student_id,))
        if cursor.fetchone() is None:
            flash("Student record not found.", "error")
            return redirect(url_for("students"))
        cursor.execute("DELETE FROM student_skills WHERE student_id = %s", (student_id,))
        for name in skill_names:
            cursor.execute(
                "INSERT INTO skills (skill_name) VALUES (%s) "
                "ON DUPLICATE KEY UPDATE skill_id=LAST_INSERT_ID(skill_id)",
                (name,),
            )
            cursor.execute("INSERT IGNORE INTO student_skills (student_id, skill_id) VALUES (%s, %s)",
                           (student_id, cursor.lastrowid))
        connection.commit()
        flash("Student skills updated.", "success")
    except mysql.connector.Error:
        connection.rollback()
        flash("Could not update skills. Check the database connection.", "error")
    finally:
        connection.close()
    return redirect(url_for("students"))


@app.route("/placements", methods=["GET", "POST"])
@login_required
def placements():
    connected = database_available()
    if request.method == "POST":
        try:
            student_id = int(request.form.get("student_id", ""))
            package_lpa = float(request.form.get("package_lpa", ""))
            status = request.form.get("status", "")
            placement_date = date.fromisoformat(request.form.get("placement_date", ""))
            company = request.form.get("company", "").strip()
            role = request.form.get("role", "").strip()
            if package_lpa < 0 or status not in STATUSES or not company or not role:
                raise ValueError
            db_write(
                "INSERT INTO placements (student_id, company, role, package_lpa, placement_date, status) "
                "VALUES (%s, %s, %s, %s, %s, %s)",
                (student_id, company, role, package_lpa, placement_date, status),
            )
            flash("Placement record added.", "success")
            return redirect(url_for("placements"))
        except ValueError:
            flash("Check the student, package, status, date, company, and role fields.", "error")
        except mysql.connector.IntegrityError:
            flash("This student, company, role, and date combination already exists.", "error")
        except mysql.connector.Error:
            flash("Could not save the placement. Check the database connection and schema.", "error")
    student_rows = db_rows("SELECT student_id, roll_no, department, graduation_year FROM students ORDER BY graduation_year DESC, roll_no") if connected else []
    rows = db_rows(
        "SELECT p.placement_id, s.roll_no, s.department, s.graduation_year, p.company, p.role, "
        "p.package_lpa, p.placement_date, p.status FROM placements p "
        "JOIN students s ON s.student_id=p.student_id ORDER BY p.placement_date DESC LIMIT 300"
    ) if connected else []
    return render_template("placements.html", placements=rows, students=student_rows, connected=connected, statuses=STATUSES)


@app.post("/placements/<int:placement_id>/status")
@login_required
def update_placement_status(placement_id):
    status = request.form.get("status", "")
    if status not in STATUSES:
        flash("Choose a valid placement status.", "error")
        return redirect(url_for("placements"))
    try:
        connection = get_connection()
        try:
            cursor = connection.cursor()
            cursor.execute("UPDATE placements SET status = %s WHERE placement_id = %s", (status, placement_id))
            if cursor.rowcount == 0:
                flash("Placement record not found.", "error")
            else:
                connection.commit()
                flash("Placement status updated.", "success")
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()
    except mysql.connector.Error:
        flash("Could not update status. Check the database connection.", "error")
    return redirect(url_for("placements"))


@app.get("/reports.csv")
def reports_csv():
    try:
        cohort = int(request.args.get("year", "2026"))
    except ValueError:
        cohort = 2026
    students, placements, skills, connected = load_analytics(cohort)
    if not connected:
        flash("Connect MySQL to export live report data.", "error")
        return redirect(url_for("dashboard", year=cohort))
    department = students.groupby("department").size().rename("eligible students").to_frame()
    placed = placements[placements.status == "placed"]
    if not placed.empty:
        department["placed students"] = placed.groupby("department").student_id.nunique()
    department["placed students"] = department.get("placed students", 0)
    department["placement rate (%)"] = np.where(department["eligible students"] > 0,
        department["placed students"] / department["eligible students"] * 100, 0).round(1)
    department.index.name = "department"
    return app.response_class(department.reset_index().to_csv(index=False), mimetype="text/csv",
                              headers={"Content-Disposition": f"attachment; filename=placement-report-{cohort}.csv"})


if __name__ == "__main__":
    app.run(debug=os.getenv("FLASK_DEBUG", "false").lower() == "true")