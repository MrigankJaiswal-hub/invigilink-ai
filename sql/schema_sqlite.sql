PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS schools (id INTEGER PRIMARY KEY, name TEXT UNIQUE NOT NULL);
CREATE TABLE IF NOT EXISTS departments (id INTEGER PRIMARY KEY, name TEXT UNIQUE NOT NULL, school_id INTEGER, FOREIGN KEY (school_id) REFERENCES schools(id));

CREATE TABLE IF NOT EXISTS professors (
  id INTEGER PRIMARY KEY,
  name TEXT NOT NULL,
  email TEXT UNIQUE NOT NULL,
  department_id INTEGER,
  max_duties INTEGER DEFAULT 3,
  FOREIGN KEY (department_id) REFERENCES departments(id)
);

CREATE TABLE IF NOT EXISTS rooms (
  id INTEGER PRIMARY KEY,
  code TEXT UNIQUE NOT NULL,
  capacity INTEGER NOT NULL,
  is_block INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS exams (
  id INTEGER PRIMARY KEY,
  course_code TEXT NOT NULL,
  course_name TEXT NOT NULL,
  exam_date TEXT NOT NULL,
  slot TEXT NOT NULL,
  duration_minutes INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS students (
  id INTEGER PRIMARY KEY,
  roll_no TEXT UNIQUE NOT NULL,
  name TEXT NOT NULL,
  course_code TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS professor_availability (
  id INTEGER PRIMARY KEY,
  professor_id INTEGER NOT NULL,
  exam_date TEXT NOT NULL,
  slot TEXT NOT NULL,
  available INTEGER NOT NULL,
  FOREIGN KEY (professor_id) REFERENCES professors(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS invigilation_assignments (
  id INTEGER PRIMARY KEY,
  exam_id INTEGER NOT NULL,
  room_id INTEGER NOT NULL,
  professor_id INTEGER NOT NULL,
  UNIQUE (exam_id, room_id, professor_id),
  FOREIGN KEY (exam_id) REFERENCES exams(id) ON DELETE CASCADE,
  FOREIGN KEY (room_id) REFERENCES rooms(id) ON DELETE CASCADE,
  FOREIGN KEY (professor_id) REFERENCES professors(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS seating_allocations (
  id INTEGER PRIMARY KEY,
  exam_id INTEGER NOT NULL,
  room_id INTEGER NOT NULL,
  seat_no INTEGER NOT NULL,
  student_id INTEGER NOT NULL,
  UNIQUE (exam_id, room_id, seat_no),
  UNIQUE (exam_id, student_id),
  FOREIGN KEY (exam_id) REFERENCES exams(id) ON DELETE CASCADE,
  FOREIGN KEY (room_id) REFERENCES rooms(id) ON DELETE CASCADE,
  FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS users (
  id INTEGER PRIMARY KEY,
  email TEXT UNIQUE NOT NULL,
  password_hash TEXT NOT NULL,
  role TEXT NOT NULL CHECK (role IN ('ADMIN','FACULTY')),
  professor_id INTEGER,
  FOREIGN KEY (professor_id) REFERENCES professors(id)
);

CREATE TABLE IF NOT EXISTS slot_assignments (
  id INTEGER PRIMARY KEY,
  exam_id INTEGER UNIQUE REFERENCES exams(id) ON DELETE CASCADE,
  professor_id INTEGER REFERENCES professors(id) ON DELETE CASCADE
);
