"""
Demo seed for Invigilink-AI.
Run using:
    python db/seed_demo.py
"""

import datetime
from passlib.hash import bcrypt

from db.dal import SessionLocal, init_db
from db.models import (
    School, Department, Professor, ProfessorDesignation,
    Room, Exam, Student, StudentEnrollment,
    ProfessorAvailability,
    AcademicProgram,
    User, UserRole
)


def run():
    init_db()

    with SessionLocal() as s:

        # -----------------------------
        # Schools + Departments
        # -----------------------------
        eng = School(name="School of Engineering")
        bus = School(name="School of Business Studies")
        s.add_all([eng, bus])
        s.flush()

        ece = Department(name="Electronics & Communication", school_id=eng.id)
        cse = Department(name="Computer Science & Engineering", school_id=eng.id)
        mba = Department(name="MBA", school_id=bus.id)
        s.add_all([ece, cse, mba])
        s.flush()

        # -----------------------------
        # Academic Programs (CUJ examples)
        # -----------------------------
        s.add_all([
            AcademicProgram(
                code_prefix="BEECE",
                degree_type="B.Tech",
                level="UG",
                school_name="School of Engineering",
                department_name="Electronics & Communication",
                department_id=ece.id,
                roll_pattern=r"^2[0-9]BEECE[0-9]{2}$"
            ),
            AcademicProgram(
                code_prefix="BECSE",
                degree_type="B.Tech",
                level="UG",
                school_name="School of Engineering",
                department_name="Computer Science & Engineering",
                department_id=cse.id,
                roll_pattern=r"^2[0-9]BECSE[0-9]{2}$"
            ),
            AcademicProgram(
                code_prefix="MMBA",
                degree_type="MBA",
                level="PG",
                school_name="School of Business Studies",
                department_name="MBA",
                department_id=mba.id,
                roll_pattern=r"^2[0-9]MMBA[0-9]{2}$"
            )
        ])

        # -----------------------------
        # Professors
        # -----------------------------
        p1 = Professor(
            name="Dr. Amit Sharma",
            email="amit.sharma@cuj.edu",
            department_id=ece.id,
            designation=ProfessorDesignation.PROFESSOR,
            max_duties=2
        )
        p2 = Professor(
            name="Dr. Rina Mehta",
            email="rina.mehta@cuj.edu",
            department_id=cse.id,
            designation=ProfessorDesignation.ASSISTANT_PROFESSOR,
            max_duties=6
        )
        s.add_all([p1, p2])
        s.flush()

        # -----------------------------
        # Admin + Faculty Accounts
        # -----------------------------
        admin = User(
            email="admin@invigilink.ai",
            password_hash=bcrypt.hash("Admin@123"),
            role=UserRole.ADMIN
        )
        fac1 = User(
            email=p1.email,
            password_hash=bcrypt.hash("Faculty@123"),
            role=UserRole.FACULTY,
            professor_id=p1.id
        )

        s.add_all([admin, fac1])

        # -----------------------------
        # Rooms
        # -----------------------------
        r1 = Room(code="A3-301", capacity=60)
        r2 = Room(code="A3-302", capacity=60)
        s.add_all([r1, r2])

        # -----------------------------
        # Exams
        # -----------------------------
        e1 = Exam(
            course_code="EC201",
            course_name="Signals & Systems",
            exam_date=datetime.date(2025, 11, 28),
            slot="FN",
            duration_minutes=180,
            school="School of Engineering",
            department="ECE"
        )
        e2 = Exam(
            course_code="CS105",
            course_name="Data Structures",
            exam_date=datetime.date(2025, 11, 28),
            slot="AN",
            duration_minutes=180,
            school="School of Engineering",
            department="CSE"
        )
        s.add_all([e1, e2])
        s.flush()

        # -----------------------------
        # Students
        # -----------------------------
        s1 = Student(roll_no="23BEECE01", name="Riya Singh")
        s2 = Student(roll_no="23BEECE02", name="Arjun Verma")
        s3 = Student(roll_no="24MMBA01", name="Sara Ali")
        s.add_all([s1, s2, s3])
        s.flush()

        # Enrollments
        s.add_all([
            StudentEnrollment(student_id=s1.id, course_code="EC201"),
            StudentEnrollment(student_id=s2.id, course_code="EC201"),
            StudentEnrollment(student_id=s3.id, course_code="CS105"),
        ])

        # -----------------------------
        # Professor Availability
        # -----------------------------
        s.add_all([
            ProfessorAvailability(professor_id=p1.id, exam_date=e1.exam_date, slot="FN", available=True),
            ProfessorAvailability(professor_id=p1.id, exam_date=e2.exam_date, slot="AN", available=False),

            ProfessorAvailability(professor_id=p2.id, exam_date=e1.exam_date, slot="FN", available=False),
            ProfessorAvailability(professor_id=p2.id, exam_date=e2.exam_date, slot="AN", available=True),
        ])

        s.commit()
        print("✅ Demo database seeded successfully.")


if __name__ == "__main__":
    run()
