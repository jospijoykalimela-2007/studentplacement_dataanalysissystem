# Fieldnotes · Student Placement Analytics

A Flask application for managing student skills and placement records, with cohort-level placement, department, skill-demand, and package analytics. The dashboard can run in fictional preview mode without MySQL; record management and CSV export use the configured database.

## Measures and data rules

- **Eligible denominator:** all registered students in the selected graduation-year cohort.
- **Placed:** distinct students with at least one placement record whose status is `placed`. Other applications and offers do not count as placements.
- **Duplicate applications:** the database rejects a repeated student/company/role/date tuple. Metrics count distinct student IDs so separate applications cannot inflate placement rates.
- **Package unit:** `package_lpa` stores INR lakhs per annum. Package mean, median, and histogram use the highest confirmed (`placed`) package per student in the cohort.
- **Privacy:** aggregate dashboard and CSV reports contain no roll numbers or student IDs. Identifiers are limited to staff-only record views.
- **Skills:** demand is reported as the number of cohort students listing each skill, not as a job-posting count.

## Setup

1. Create a local environment and install dependencies:

   ```powershell
   py -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```

2. Copy `.env.example` to `.env`. Set a long random `FLASK_SECRET_KEY`, a unique staff password, and your local MySQL password in `DB_PASSWORD`. `.env` is ignored by Git; do not commit it.

3. Create the tables using MySQL Workbench or the MySQL CLI:

   ```powershell
   mysql -u root -p < schema.sql
   ```

4. Start the website:

   ```powershell
   flask --app app run --debug
   ```

   Visit `http://127.0.0.1:5000`. The overview shows fictional preview data when MySQL is not reachable. Sign in with the staff credentials from `.env` to access student and placement management after setting up the database.

## MySQL configuration

Defaults are `localhost:3306`, database `student_placement`, and user `root`. Override `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, and `DB_PASSWORD` in `.env` to match your local MySQL installation. Do not place database credentials in Python files or commit them.

For deployment, set `FLASK_SECRET_KEY`, `ADMIN_USERNAME`, and `ADMIN_PASSWORD` to strong unique values; use a least-privilege database account and serve the app behind HTTPS. The built-in staff login is intended as a small local-project access gate, not a replacement for institutional SSO or a multi-user authorization system.