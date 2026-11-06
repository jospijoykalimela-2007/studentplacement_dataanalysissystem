CREATE DATABASE IF NOT EXISTS student_placement
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE student_placement;

CREATE TABLE IF NOT EXISTS students (
  student_id INT UNSIGNED NOT NULL AUTO_INCREMENT,
  roll_no VARCHAR(40) NOT NULL,
  department VARCHAR(100) NOT NULL,
  graduation_year YEAR NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (student_id),
  UNIQUE KEY uq_students_roll_no (roll_no),
  KEY idx_students_cohort_department (graduation_year, department)
);

CREATE TABLE IF NOT EXISTS skills (
  skill_id INT UNSIGNED NOT NULL AUTO_INCREMENT,
  skill_name VARCHAR(80) NOT NULL,
  PRIMARY KEY (skill_id),
  UNIQUE KEY uq_skills_name (skill_name)
);

CREATE TABLE IF NOT EXISTS student_skills (
  student_id INT UNSIGNED NOT NULL,
  skill_id INT UNSIGNED NOT NULL,
  PRIMARY KEY (student_id, skill_id),
  CONSTRAINT fk_student_skills_student FOREIGN KEY (student_id)
    REFERENCES students (student_id) ON DELETE CASCADE,
  CONSTRAINT fk_student_skills_skill FOREIGN KEY (skill_id)
    REFERENCES skills (skill_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS placements (
  placement_id INT UNSIGNED NOT NULL AUTO_INCREMENT,
  student_id INT UNSIGNED NOT NULL,
  company VARCHAR(120) NOT NULL,
  role VARCHAR(120) NOT NULL,
  package_lpa DECIMAL(10, 2) NOT NULL,
  placement_date DATE NOT NULL,
  status ENUM('applied', 'interview', 'offer', 'placed', 'rejected') NOT NULL DEFAULT 'applied',
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (placement_id),
  UNIQUE KEY uq_placement_application (student_id, company, role, placement_date),
  KEY idx_placements_student_status (student_id, status),
  KEY idx_placements_date (placement_date),
  CONSTRAINT fk_placements_student FOREIGN KEY (student_id)
    REFERENCES students (student_id) ON DELETE CASCADE,
  CONSTRAINT chk_placements_package_lpa CHECK (package_lpa >= 0)
);