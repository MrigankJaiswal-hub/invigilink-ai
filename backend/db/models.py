from sqlalchemy import (
    Column, Integer, String, Boolean, Date, ForeignKey, Enum,
    UniqueConstraint, Text
)
from sqlalchemy.orm import declarative_base
import enum

Base = declarative_base()

# -----------------------------
# User Roles
# -----------------------------
class UserRole(str, enum.Enum):
    ADMIN = "ADMIN"
    FACULTY = "FACULTY"


# -----------------------------
# School & Department
# -----------------------------
class School(Base):
    __tablename__ = "schools"
    id = Column(Integer, primary_key=True)
    name = Column(String(160), unique=True, nullable=False)


class Department(Base):
    __tablename__ = "departments"
    id = Column(Integer, primary_key=True)
    name = Column(String(160), unique=True, nullable=False)
    school_id = Column(Integer, ForeignKey("schools.id"))


# -----------------------------
# Professor with designation + duty limits
# -----------------------------
class ProfessorDesignation(str, enum.Enum):
    PROFESSOR = "PROFESSOR"
    ASSOCIATE_PROFESSOR = "ASSOCIATE_PROFESSOR"
    ASSISTANT_PROFESSOR = "ASSISTANT_PROFESSOR"
    OTHER = "OTHER"


class Professor(Base):
    __tablename__ = "professors"
    id = Column(Integer, primary_key=True)
    name = Column(String(160), nullable=False)
    email = Column(String(200), unique=True, nullable=True)

    department_id = Column(Integer, ForeignKey("departments.id"), nullable=True)
    designation = Column(Enum(ProfessorDesignation), nullable=True)

    # auto-set from designation rules
    max_duties = Column(Integer, default=3)


# -----------------------------
# Rooms
# -----------------------------
class Room(Base):
    __tablename__ = "rooms"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String, unique=True, index=True)
    capacity = Column(Integer)

    # 🔥 NEW:
    building = Column(String(100), nullable=True)  # e.g. "DDE Building" or "Aryabhatta Block"
    floor = Column(String(50), nullable=True)      # e.g. "A", "B", "C", "Ground", "1st"


# -----------------------------
# Exams (with school + department)
# -----------------------------
class Exam(Base):
    __tablename__ = "exams"
    id = Column(Integer, primary_key=True)

    course_code = Column(String(60), nullable=False)
    course_name = Column(String(200), nullable=True)
    course_title = Column(String(200), nullable=True)

    school = Column(String(200), nullable=True)
    department = Column(String(200), nullable=True)

    exam_date = Column(Date, nullable=False)
    slot = Column(String(20), nullable=False)
    duration_minutes = Column(Integer, nullable=False)


# -----------------------------
# Students (lean model)
# -----------------------------
class Student(Base):
    __tablename__ = "students"
    id = Column(Integer, primary_key=True)
    roll_no = Column(String(60), unique=True, nullable=False)
    name = Column(String(200), nullable=False)


# -----------------------------
# Student Enrollments (many-to-many)
# -----------------------------
class StudentEnrollment(Base):
    __tablename__ = "student_enrollments"
    id = Column(Integer, primary_key=True)
    student_id = Column(Integer, ForeignKey("students.id", ondelete="CASCADE"))
    course_code = Column(String(60), nullable=False)

    __table_args__ = (
        UniqueConstraint("student_id", "course_code", name="uq_student_course"),
    )


# -----------------------------
# Professor Availability
# -----------------------------
class ProfessorAvailability(Base):
    __tablename__ = "professor_availability"
    id = Column(Integer, primary_key=True)
    professor_id = Column(Integer, ForeignKey("professors.id", ondelete="CASCADE"))
    exam_date = Column(Date, nullable=False)
    slot = Column(String(20), nullable=False)
    available = Column(Boolean, nullable=False)

    __table_args__ = (
        UniqueConstraint("professor_id", "exam_date", "slot",
                         name="uq_prof_available_dt_slot"),
    )


# -----------------------------
# Professor → Teaching Courses
# -----------------------------
class ProfessorCourses(Base):
    __tablename__ = "professor_courses"
    id = Column(Integer, primary_key=True)

    professor_id = Column(Integer, ForeignKey("professors.id", ondelete="CASCADE"))
    course_code = Column(String(60), nullable=False)

    __table_args__ = (
        UniqueConstraint("professor_id", "course_code", name="uq_prof_course"),
    )


# -----------------------------
# Seating Allocations
# (ONLY unique per exam per student)
# Allows 2 students per bench now
# -----------------------------
class SeatingAllocation(Base):
    __tablename__ = "seating_allocations"
    id = Column(Integer, primary_key=True)

    exam_id = Column(Integer, ForeignKey("exams.id", ondelete="CASCADE"))
    room_id = Column(Integer, ForeignKey("rooms.id", ondelete="CASCADE"))
    seat_no = Column(Integer, nullable=False)
    student_id = Column(Integer, ForeignKey("students.id", ondelete="CASCADE"))

    __table_args__ = (
        UniqueConstraint("exam_id", "student_id", name="uq_exam_student"),
    )


# -----------------------------
# Duty Assignment
# -----------------------------
class SlotAssignment(Base):
    __tablename__ = "slot_assignments"
    id = Column(Integer, primary_key=True)
    exam_id = Column(Integer, ForeignKey("exams.id", ondelete="CASCADE"), unique=True)
    professor_id = Column(Integer, ForeignKey("professors.id", ondelete="CASCADE"))


# -----------------------------
# Admin Panel Users
# -----------------------------
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)

    email = Column(String(200), unique=True, nullable=False)
    password_hash = Column(String, nullable=False)

    role = Column(Enum(UserRole), nullable=False)
    professor_id = Column(Integer, ForeignKey("professors.id"), nullable=True)


# -----------------------------
# Academic Programs (For CUJ roll-number decoding)
# -----------------------------
class AcademicProgram(Base):
    __tablename__ = "academic_programs"

    id = Column(Integer, primary_key=True)

    code_prefix = Column(String(40), nullable=False, index=True)
    degree_type = Column(String(80), nullable=True)
    level = Column(String(20), nullable=True)        # UG/PG/PhD

    school_name = Column(String(200), nullable=True)
    department_name = Column(String(200), nullable=True)
    department_id = Column(Integer, nullable=True)

    course_prefix = Column(String(40), nullable=True)
    roll_pattern = Column(Text, nullable=True)

    __table_args__ = (
        UniqueConstraint("code_prefix", name="uq_program_codeprefix"),
    )
