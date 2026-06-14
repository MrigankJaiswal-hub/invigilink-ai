from fastapi import APIRouter, Depends, Response, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from sqlalchemy import text

import csv
from io import StringIO
from datetime import datetime, date, time
import re

from auth.deps import require_admin
from db.dal import SessionLocal

from db.cuj_roll import academic_year_from_roll_cuj, parse_cuj_roll

from pydantic import BaseModel

from db.models import (
    Exam,
    Room,
    Professor,
    ProfessorAvailability,
    SeatingAllocation,
    Student,
    SlotAssignment,
    Department,
    StudentEnrollment,
    ProfessorCourses,
    AcademicProgram,
)

from scheduler.duty_scheduler import schedule_invigilation  # (still available if needed)
from scheduler.duty_scheduler_one_prof import schedule_one_prof_per_slot
from notifications.mailer import send_mail
from reports.report_service import render_pdf_or_html_download

router = APIRouter(prefix="/admin", tags=["admin"])


def db():
    with SessionLocal() as s:
        yield s


# ---------------- Helpers (branch detection – legacy) ----------------
def _branch_from_course(code: str) -> str:
    """
    Legacy helper used in some paths (ECE/ECA). For full-university flows
    we prefer department_id or year-based grouping instead.
    """
    c = (code or "").upper()
    if c.startswith("BEECA"):
        return "ECA"
    if c.startswith("BEECE"):
        return "ECE"
    return "OTHER"


def _branch_from_roll(roll: str) -> str:
    r = (roll or "").upper()
    if "BEECA" in r:
        return "ECA"
    if "BEECE" in r:
        return "ECE"
    return "OTHER"


# ---------------- Helpers for academic year detection from roll ----------------
def batch_prefix_from_roll(roll: str) -> int | None:
    """
    Extract leading 2 digits from roll like '23BEECE10' -> 23.
    Returns None if not found.
    """
    if not roll:
        return None
    m = re.match(r"^(\d{2})", roll.strip())
    if not m:
        return None
    try:
        return int(m.group(1))
    except ValueError:
        return None


def academic_year_from_roll(roll: str, exam_date: date) -> int | None:
    """
    Given a roll like '23BEECE10' and an exam date (e.g. 2025-05-10),
    compute the academic year:

      exam_year_suffix = 25 (for 2025)
      batch_prefix     = 23 -> diff = 2 -> 3rd year

    year = diff + 1

    We only trust values where diff is within [0, 5]; otherwise return None.
    """
    batch = batch_prefix_from_roll(roll)
    if batch is None:
        return None

    exam_year_suffix = exam_date.year % 100
    diff = exam_year_suffix - batch
    if diff < 0 or diff > 5:
        # older than 5 years or "future" batch – treat as unknown
        return None

    return diff + 1  # 0->1st yr, 1->2nd, 2->3rd, ...


def group_key_from_roll(roll: str, exam_date: date) -> str:
    """
    Produce a "group key" for mixing on benches.

    Priority:
      1) Academic year Y1/Y2/Y3... if we can infer from roll + exam_date
      2) Otherwise "UNK" (rare roll formats without leading digits).
    """
    yr = academic_year_from_roll(roll, exam_date)
    if yr is not None:
        return f"Y{yr}"
    return "UNK"


# -------------- CUJ-specific helper: roll → program code --------------
def program_code_from_roll(roll: str) -> str | None:
    """
    CUJ-style roll parsing:

      Examples:
        24MMBA01  -> "MMBA"
        23BEECE10 -> "BEECE"

    Pattern we assume for MVP:
      ^(\d{2})([A-Z]+)(\d+)$
      - 2 digits (batch year)
      - 1+ letters (program code)
      - 1+ digits (serial)

    If full match fails, we still try a relaxed pattern:
      ^\d{2}([A-Z]+)\d+
    """
    if not roll:
        return None
    r = roll.strip().upper()

    # strict pattern
    m = re.match(r"^(\d{2})([A-Z]+)(\d+)$", r)
    if m:
        return m.group(2)

    # relaxed pattern: just "2 digits" + letters + digits
    m2 = re.match(r"^\d{2}([A-Z]+)\d+", r)
    if m2:
        return m2.group(1)

    return None


# ---------------- Helpers for designation → max_duties ----------------
# def _effective_max_duties(designation: str | None, override: int | None) -> int:
#     """
#     Priority:
#       - If override (max_duties) set and >0 → use it
#       - Otherwise compute from designation:
#           PROFESSOR            → 2
#           ASSOCIATE_PROFESSOR  → 4
#           ASSISTANT_PROFESSOR  → 6
#       - Fallback → 6
#     """
#     if override is not None:
#         try:
#             if int(override) > 0:
#                 return int(override)
#         except Exception:
#             pass

#     d = (designation or "").upper()
#     if "ASSISTANT" in d:
#         return 6
#     if "ASSOCIATE" in d:
#         return 4
#     if "PROFESSOR" in d:
#         return 2

#     # default for others / unknown
#     return 6

def _effective_max_duties(designation: str | None, override: int | None) -> int:
    """
    Determine max duties based on designation,
    unless overridden in DB.
    """
    if override is not None:
        return override

    d = (designation or "").lower()

    if d == "professor":
        return 2
    elif d == "associate":
        return 4
    else:  # Assistant / default
        return 6



class AcademicProgramIn(BaseModel):
    id: int | None = None
    code_prefix: str
    degree_type: str | None = None
    level: str | None = None
    department_name: str | None = None
    school_name: str | None = None
    department_id: int | None = None
    course_prefix: str | None = None
    roll_pattern: str | None = None


# ========================================
# Academic Programs – List
# ========================================
@router.get("/academic-programs", dependencies=[Depends(require_admin)])
def list_academic_programs(s: Session = Depends(db)):
    """
    Return all academic programs (code_prefix → dept/school mapping).
    Used by the admin UI table.
    """
    rows = (
        s.query(AcademicProgram)
        .order_by(AcademicProgram.code_prefix)
        .all()
    )
    return [
        {
            "id": p.id,
            "code_prefix": p.code_prefix,
            "degree_type": p.degree_type,
            "level": p.level,
            "department_name": p.department_name,
            "school_name": p.school_name,
            "department_id": p.department_id,
            "course_prefix": p.course_prefix,
            "roll_pattern": p.roll_pattern,
        }
        for p in rows
    ]


# ========================================
# Academic Programs – Create/Update (JSON)
# ========================================
@router.post("/academic-programs/save", dependencies=[Depends(require_admin)])
def save_academic_program(
    payload: AcademicProgramIn,
    s: Session = Depends(db),
):
    """
    Create or update an AcademicProgram.

    If payload.id is provided → update that row.
    Else → upsert by code_prefix.
    """
    if payload.id is not None:
        prog = s.query(AcademicProgram).get(payload.id)
        if not prog:
            raise HTTPException(404, detail="Program not found")

        prog.code_prefix = payload.code_prefix.strip()
        prog.degree_type = payload.degree_type or None
        prog.level = payload.level or None
        prog.department_name = payload.department_name or None
        prog.school_name = payload.school_name or None
        prog.department_id = payload.department_id
        prog.course_prefix = payload.course_prefix or None
        prog.roll_pattern = payload.roll_pattern or None

        s.commit()
        s.refresh(prog)
        return {
            "id": prog.id,
            "code_prefix": prog.code_prefix,
            "degree_type": prog.degree_type,
            "level": prog.level,
            "department_name": prog.department_name,
            "school_name": prog.school_name,
            "department_id": prog.department_id,
            "course_prefix": prog.course_prefix,
            "roll_pattern": prog.roll_pattern,
        }

    # No id: upsert by code_prefix
    code_prefix = payload.code_prefix.strip()
    prog = (
        s.query(AcademicProgram)
        .filter(AcademicProgram.code_prefix == code_prefix)
        .first()
    )

    if prog:
        prog.degree_type = payload.degree_type or None
        prog.level = payload.level or None
        prog.department_name = payload.department_name or None
        prog.school_name = payload.school_name or None
        prog.department_id = payload.department_id
        prog.course_prefix = payload.course_prefix or None
        prog.roll_pattern = payload.roll_pattern or None
    else:
        prog = AcademicProgram(
            code_prefix=code_prefix,
            degree_type=payload.degree_type or None,
            level=payload.level or None,
            department_name=payload.department_name or None,
            school_name=payload.school_name or None,
            department_id=payload.department_id,
            course_prefix=payload.course_prefix or None,
            roll_pattern=payload.roll_pattern or None,
        )
        s.add(prog)

    s.commit()
    s.refresh(prog)
    return {
        "id": prog.id,
        "code_prefix": prog.code_prefix,
        "degree_type": prog.degree_type,
        "level": prog.level,
        "department_name": prog.department_name,
        "school_name": prog.school_name,
        "department_id": prog.department_id,
        "course_prefix": prog.course_prefix,
        "roll_pattern": prog.roll_pattern,
    }


# ========================================
# Academic Programs – CSV Upload (with department auto-resolve)
# ========================================
@router.post("/academic-programs/upload", dependencies=[Depends(require_admin)])
def upload_academic_programs(
    file: UploadFile = File(...),
    s: Session = Depends(db),
):
    """
    CSV columns (case-insensitive):

      code_prefix, degree_type, level,
      department_name, school_name, department_id,
      course_prefix, roll_pattern

    - Only 'code_prefix' is mandatory.
    - Upsert by code_prefix.
    - If department_id is blank but department_name is provided,
      we auto-resolve to departments.id via case-insensitive name match.
    """

    content = file.file.read().decode("utf-8", errors="ignore")
    reader = csv.DictReader(StringIO(content))
    cols = {(c or "").strip().lower() for c in (reader.fieldnames or [])}

    if "code_prefix" not in cols:
        raise HTTPException(
            400,
            detail="CSV must include at least 'code_prefix' column.",
        )

    created = 0
    updated = 0

    for row in reader:
        code_prefix = (row.get("code_prefix") or row.get("Code Prefix") or "").strip()
        if not code_prefix:
            continue

        degree_type = (row.get("degree_type") or row.get("Degree Type") or "").strip() or None
        level = (row.get("level") or row.get("Level") or "").strip() or None
        department_name = (row.get("department_name") or row.get("Department Name") or "").strip() or None
        school_name = (row.get("school_name") or row.get("School Name") or "").strip() or None
        course_prefix = (row.get("course_prefix") or row.get("Course Prefix") or "").strip() or None
        roll_pattern = (row.get("roll_pattern") or row.get("Roll Pattern") or "").strip() or None

        dept_id_raw = (row.get("department_id") or row.get("Department Id") or "").strip()
        department_id = None
        if dept_id_raw:
            try:
                department_id = int(dept_id_raw)
            except ValueError:
                department_id = None

        # auto-resolve department_id from department_name if still None
        if department_id is None and department_name:
            dept = (
                s.query(Department)
                 .filter(Department.name.ilike(department_name))
                 .first()
            )
            if dept:
                department_id = dept.id

        prog = (
            s.query(AcademicProgram)
            .filter(AcademicProgram.code_prefix == code_prefix)
            .first()
        )

        if prog:
            prog.degree_type = degree_type
            prog.level = level
            prog.department_name = department_name
            prog.school_name = school_name
            prog.department_id = department_id
            prog.course_prefix = course_prefix
            prog.roll_pattern = roll_pattern
            updated += 1
        else:
            s.add(AcademicProgram(
                code_prefix=code_prefix,
                degree_type=degree_type,
                level=level,
                department_name=department_name,
                school_name=school_name,
                department_id=department_id,
                course_prefix=course_prefix,
                roll_pattern=roll_pattern,
            ))
            created += 1

    s.commit()
    return {"created": created, "updated": updated}


# ---------------------------------------------------------
# Exams list (used by seating UI dropdown)
# ---------------------------------------------------------
@router.get("/exams-list", dependencies=[Depends(require_admin)])
def exams_list(s: Session = Depends(db)):
    rows = s.execute(text("""
        SELECT id,
               exam_date,
               slot,
               course_code,
               COALESCE(course_name, course_title) AS course_name,
               department,
               exam_type
        FROM exams
        ORDER BY exam_date, slot, id
    """)).mappings().all()
    return [
        {
            "id": r["id"],
            "exam_date": r["exam_date"].isoformat() if hasattr(r["exam_date"], "isoformat") else str(r["exam_date"]),
            "slot": r["slot"],
            "course_code": r["course_code"],
            "course_name": r["course_name"],
            "department": r["department"],
            "exam_type": r["exam_type"],
        }
        for r in rows
    ]



# ---------------------------------------------------------
# Import exams CSV with UPSERT (idempotent).
# Accepts EITHER normalized or raw timetable formats.
# ---------------------------------------------------------
# ---------------------------------------------------------
# Import exams CSV with UPSERT (idempotent).
# Accepts EITHER normalized or raw timetable formats.
# ---------------------------------------------------------
@router.post("/import/exams-csv")
def import_exams_csv(
    file: UploadFile = File(...),
    _=Depends(require_admin),
    s: Session = Depends(db),
):
    """
    Accepts EITHER:
      A) Normalized headers:
         course_code, course_name, department, duration_minutes, exam_date, school, slot, [exam_type]

      B) Raw timetable headers:
         Course Code, Course Title, Date of Exam, Time, Branch, [School], [Exam Type] / [Regular / Re-appear]

    - exam_date: YYYY-MM-DD or DD/MM/YYYY
    - Time: "10:00 AM to 01:00 PM" → duration + slot (FN before 13:00 else AN)
    - UPSERT on (exam_date, slot, course_code)
    """

    content = file.file.read().decode("utf-8", errors="ignore")
    reader = csv.DictReader(StringIO(content))
    raw_cols = {(c or "").strip() for c in (reader.fieldnames or [])}
    cols_lc = {(c or "").strip().lower() for c in (reader.fieldnames or [])}

    def parse_date(v: str) -> date:
        v = (v or "").strip()
        if not v:
            raise ValueError("empty date")
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
            try:
                return datetime.strptime(v, fmt).date()
            except ValueError:
                pass
        raise ValueError(f"Unrecognized date format: {v}")

    def parse_time(v: str) -> time | None:
        v = (v or "").strip()
        if not v:
            return None
        for fmt in ("%I:%M %p", "%H:%M"):
            try:
                return datetime.strptime(v, fmt).time()
            except ValueError:
                pass
        return None

    def split_timerange(sv: str):
        if not sv:
            return None
        # allow "to" / "-" etc.
        if "to" in sv:
            parts = [p.strip() for p in sv.split("to", 1)]
        elif "-" in sv:
            parts = [p.strip() for p in sv.split("-", 1)]
        else:
            return None
        if len(parts) != 2:
            return None
        st = parse_time(parts[0])
        en = parse_time(parts[1])
        if st and en:
            return (st, en)
        return None

    def slot_from_start(t: time) -> str:
        return "FN" if t.hour < 13 else "AN"

    def minutes_between(d: date, t1: time, t2: time) -> int:
        dt1 = datetime(d.year, d.month, d.day, t1.hour, t1.minute)
        dt2 = datetime(d.year, d.month, d.day, t2.hour, t2.minute)
        mins = int((dt2 - dt1).total_seconds() // 60)
        return mins if mins > 0 else 120

    def upsert_row(code, name, dept, mins, d, school, slot, exam_type) -> bool:
        res = s.execute(text("""
            INSERT INTO exams (
                course_code,
                course_name,
                department,
                duration_minutes,
                exam_date,
                school,
                slot,
                exam_type
            )
            VALUES (:code, :name, :dept, :mins, :exam_date, :school, :slot, :exam_type)
            ON CONFLICT (exam_date, slot, course_code)
            DO UPDATE SET
                course_name      = EXCLUDED.course_name,
                department       = EXCLUDED.department,
                duration_minutes = EXCLUDED.duration_minutes,
                school           = EXCLUDED.school,
                exam_type        = EXCLUDED.exam_type
            RETURNING (xmax = 0) AS inserted
        """), {
            "code": code,
            "name": name,
            "dept": dept,
            "mins": mins,
            "exam_date": d,
            "school": school,
            "slot": slot,
            "exam_type": exam_type,
        }).mappings().first()
        return bool(res and res["inserted"])

    normalized_need = {
        "course_code", "course_name", "department", "duration_minutes", "exam_date", "school", "slot"
    }
    raw_need = {"course code", "course title", "date of exam", "time", "branch"}

    is_normalized = normalized_need.issubset(cols_lc)
    is_raw = raw_need.issubset(cols_lc)

    if not (is_normalized or is_raw):
        raise HTTPException(
            400,
            detail=(
                "Missing columns. Required either normalized: "
                "['course_code','course_name','department','duration_minutes','exam_date','school','slot'] "
                "or raw timetable: ['Course Code','Course Title','Date of Exam','Time','Branch']. "
                f"Found headers: {sorted(raw_cols)}"
            ),
        )

    imported = 0
    updated = 0

    for r in reader:
        try:
            # ---------- NORMALIZED FORMAT ----------
            if is_normalized:
                code = str(r.get("course_code", "")).strip().upper()
                name = str(r.get("course_name", "")).strip()
                dept = str(r.get("department", "")).strip()
                school = str(r.get("school", "")).strip() or "CUJ"
                slot = str(r.get("slot", "")).strip().upper() or "FN"

                # skip blank / heading rows
                if not code and not name:
                    continue

                raw_date = (r.get("exam_date") or "").strip()
                if not raw_date:
                    # skip noise rows with no date
                    continue
                d = parse_date(raw_date)

                try:
                    mins = int(str(r.get("duration_minutes", "")).strip() or "0")
                except Exception:
                    mins = 0
                if mins <= 0:
                    mins = 120

                raw_exam_type = (
                    r.get("exam_type")
                    or r.get("Exam Type")
                    or r.get("examType")
                    or ""
                )
                exam_type = raw_exam_type.strip().upper() or None

            # ---------- RAW TIMETABLE FORMAT ----------
            else:
                code = str(r.get("Course Code") or r.get("course code") or "").strip().upper()
                name = str(r.get("Course Title") or r.get("course title") or "").strip()
                branch = str(r.get("Branch") or r.get("branch") or "").strip()
                dept = branch or ""
                school = str(r.get("School") or r.get("school") or "CUJ").strip() or "CUJ"

                # skip blank / heading rows
                if not code and not name and not branch:
                    continue

                raw_date = (
                    r.get("Date of Exam")
                    or r.get("date of exam")
                    or ""
                )
                if not (raw_date or "").strip():
                    # skip header / non-data lines with no date
                    continue
                d = parse_date(raw_date)

                tr = split_timerange(r.get("Time") or r.get("time") or "")
                if tr:
                    st, en = tr
                    mins = minutes_between(d, st, en)
                    slot = slot_from_start(st)
                else:
                    mins = 120
                    slot = "FN"

                raw_exam_type = (
                    r.get("Exam Type")
                    or r.get("exam_type")
                    or r.get("Regular / Re-appear")
                    or r.get("Regular / Reappear")
                    or r.get("Regular/Re-appear")
                    or ""
                )
                exam_type = raw_exam_type.strip().upper() or None

            # If still no code or no name, skip row
            if not code or not name:
                continue

            inserted = upsert_row(code, name, dept, mins, d, school, slot, exam_type)
            if inserted:
                imported += 1
            else:
                updated += 1

        except ValueError as ve:
            # Instead of killing the whole upload, you can either:
            #  - raise (strict mode), OR
            #  - just skip this row.
            raise HTTPException(
                400,
                detail=f"Row error for course_code={r.get('course_code') or r.get('Course Code')}: {ve}"
            ) from ve
        except Exception as e:
            raise HTTPException(
                400,
                detail=f"Row error for course_code={r.get('course_code') or r.get('Course Code')}: {e}"
            ) from e

    s.commit()
    return {"imported": imported, "updated": updated}



# -------------------------------------------------
# Import professor availability (calendar → CSV → DB)
# -------------------------------------------------
@router.post("/faculty-availability/upload")
def upload_prof_availability(
    file: UploadFile = File(...),
    _=Depends(require_admin),
    s: Session = Depends(db),
):
    """
    CSV headers (case-insensitive):
      employee_code, exam_date, slot, available

    Optional:
      professor_name, designation, department_id
    """

    content = file.file.read().decode("utf-8", errors="ignore")
    reader = csv.DictReader(StringIO(content))
    cols = {(c or "").strip().lower() for c in (reader.fieldnames or [])}

    required = {"employee_code", "exam_date", "slot", "available"}
    if not required.issubset(cols):
        raise HTTPException(
            400,
            detail="Required columns: employee_code, exam_date, slot, available",
        )

    def parse_date(v: str) -> date:
        v = (v or "").strip()
        for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
            try:
                return datetime.strptime(v, fmt).date()
            except ValueError:
                pass
        raise ValueError(f"Invalid date: {v}")

    def parse_bool(v: str) -> bool:
        return str(v).strip().lower() in ("1", "true", "yes", "y")

    def normalize_slot(v: str) -> str | None:
        v = (v or "").strip().lower()
        if v in ("fn", "forenoon", "morning"):
            return "FN"
        if v in ("an", "afternoon"):
            return "AN"
        if v in ("evening", "ev"):
            return "EVENING"
        return None

    saved = 0

    for row in reader:
        emp = (row.get("employee_code") or "").strip()
        if not emp:
            continue

        prof_id = s.execute(
            text("SELECT id FROM professors WHERE employee_code = :c"),
            {"c": emp},
        ).scalar()

        if not prof_id:
            continue

        # Optional name update
        prof_name = (row.get("professor_name") or "").strip()
        if prof_name:
            s.execute(
                text("UPDATE professors SET name = :n WHERE id = :pid"),
                {"n": prof_name, "pid": prof_id},
            )

        # Parse date
        try:
            exam_date = parse_date(row.get("exam_date"))
        except Exception:
            continue

        slot = normalize_slot(row.get("slot"))
        if not slot:
            continue

        available = parse_bool(row.get("available"))

        s.execute(
            text("""
                INSERT INTO professor_availability
                    (professor_id, exam_date, slot, available)
                VALUES
                    (:pid, :d, :slot, :avail)
                ON CONFLICT (professor_id, exam_date, slot)
                DO UPDATE SET available = EXCLUDED.available
            """),
            {
                "pid": prof_id,
                "d": exam_date,
                "slot": slot,
                "avail": available,
            },
        )

        saved += 1

    s.commit()
    return {"saved": saved}


# -------------------------------------------------
# Import professor teaching subjects → professor_courses
# -------------------------------------------------
@router.post("/faculty-teaching/upload")
def upload_prof_teaching(
    file: UploadFile = File(...),
    _=Depends(require_admin),
    s: Session = Depends(db),
):
    """
    CSV required (case-insensitive headers):
      employee_code, course_code

    This feeds the professor_courses table, used to AVOID
    assigning a professor as invigilator to their own subject.
    """
    content = file.file.read().decode("utf-8", errors="ignore")
    reader = csv.DictReader(StringIO(content))
    cols = {(c or "").strip().lower() for c in (reader.fieldnames or [])}
    need = {"employee_code", "course_code"}
    if not need.issubset(cols):
        raise HTTPException(
            400,
            detail="Missing columns. Required: ['employee_code','course_code']"
        )

    inserted = 0
    for row in reader:
        emp = (row.get("employee_code") or row.get("Employee Code") or "").strip()
        cc = (row.get("course_code") or row.get("Course Code") or "").strip().upper()
        if not emp or not cc:
            continue

        prof = s.execute(
            text("SELECT id FROM professors WHERE employee_code = :c"),
            {"c": emp},
        ).scalar()
        if not prof:
            continue

        # Insert ignore on conflict (professor_id, course_code)
        s.execute(text("""
            INSERT INTO professor_courses (professor_id, course_code)
            VALUES (:pid, :cc)
            ON CONFLICT (professor_id, course_code) DO NOTHING
        """), {"pid": prof, "cc": cc})
        inserted += 1

    s.commit()
    return {"inserted": inserted}


# -------------------------------------------------
# Import lean students CSV: Roll No, Name (upsert by roll_no)
# -------------------------------------------------
@router.post("/import/students-lean-csv")
def import_students_lean_csv(
    file: UploadFile = File(...),
    _=Depends(require_admin),
    s: Session = Depends(db)
):
    """
    CSV required (case-insensitive headers):
      Roll No, Name
    """
    content = file.file.read().decode("utf-8", errors="ignore")
    reader = csv.DictReader(StringIO(content))
    need = {"roll no", "name"}
    cols = {c.strip().lower() for c in (reader.fieldnames or [])}
    if not need.issubset(cols):
        raise HTTPException(400, detail="Missing columns. Required: ['Roll No','Name']")

    inserted = 0
    for row in reader:
        roll = (row.get("Roll No") or row.get("roll no") or "").strip()
        name = (row.get("Name") or row.get("name") or "").strip()
        if not roll or not name:
            continue
        existing = s.execute(text("SELECT id FROM students WHERE roll_no = :r"), {"r": roll}).scalar()
        if existing:
            s.execute(text("UPDATE students SET name=:n WHERE id=:id"), {"n": name, "id": existing})
        else:
            s.execute(text("INSERT INTO students (roll_no, name) VALUES (:r, :n)"), {"r": roll, "n": name})
            inserted += 1
    s.commit()
    return {"imported": inserted}


# -------------------------------------------------
# Auto-enroll students into exams by CUJ-style roll → program code
# -------------------------------------------------
@router.post("/auto-enroll-from-roll")
def auto_enroll_from_roll(_=Depends(require_admin), s: Session = Depends(db)):
    """
    CUJ-style auto-enrollment:

    - Student roll_no like: 24MMBA01, 23BEECE10, ...
      -> program_code_from_roll(...) => "MMBA", "BEECE", etc.

    - Exam course_code like: MMBA101, BEECE301, ...
      -> We enroll a student into all exams whose course_code starts with their program code.

    So:
      24MMBA01   -> auto-enrolled to all courses where course_code startswith "MMBA"
      23BEECE10  -> auto-enrolled to all "BEECE..." exams
    """
    exam_codes = [
        (r["course_code"] or "").strip().upper()
        for r in s.execute(text("SELECT DISTINCT course_code FROM exams")).mappings().all()
        if (r["course_code"] or "").strip()
    ]
    if not exam_codes:
        raise HTTPException(400, "No exams found to map against.")

    students = s.execute(
        text("SELECT id, roll_no FROM students ORDER BY id")
    ).mappings().all()
    if not students:
        return {"enrolled": 0, "note": "No students found."}

    inserted = 0
    for st in students:
        roll = (st["roll_no"] or "").strip()
        prog = program_code_from_roll(roll)
        if not prog:
            # can't infer program from roll, skip safely
            continue

        prefix = prog.upper()
        for code in exam_codes:
            if not code:
                continue
            if code.startswith(prefix):
                s.execute(text("""
                    INSERT INTO student_enrollments (student_id, course_code)
                    SELECT :sid, :code
                    WHERE NOT EXISTS (
                        SELECT 1
                        FROM student_enrollments
                        WHERE student_id = :sid AND course_code = :code
                    )
                """), {"sid": st["id"], "code": code})
                inserted += 1

    s.commit()
    return {"enrolled": inserted}


# -------------------------------------------------
# Enrollments per course (preview for UI)
# -------------------------------------------------
@router.get("/enrollments-summary")
def enrollments_summary(_=Depends(require_admin), s: Session = Depends(db)):
    rows = s.execute(text("""
        SELECT course_code, COUNT(*) AS students
        FROM student_enrollments
        GROUP BY course_code
        ORDER BY course_code
    """)).mappings().all()
    return {"rows": [{"course_code": r["course_code"], "students": int(r["students"])} for r in rows]}


# -------------------------------------------------
# Designation summary (for frontend display)
# -------------------------------------------------
# -------------------------------------------------
# Designation summary (for frontend display)
# -------------------------------------------------
@router.get("/professors/designation-summary", dependencies=[Depends(require_admin)])
def designation_summary(s: Session = Depends(db)):
    """
    Returns per-professor designation and effective max duties
    after applying designation rules and DB overrides.
    """

    rows = s.execute(text("""
        SELECT
            id,
            name,
            COALESCE(designation::text, 'ASSISTANT_PROFESSOR') AS designation,
            max_duties
        FROM professors
        ORDER BY name
    """)).mappings().all()

    out = []
    for r in rows:
        effective = _effective_max_duties(
            r["designation"],
            r["max_duties"]
        )

        out.append({
            "professor_id": r["id"],
            "name": r["name"],
            "designation": r["designation"],
            "configured_max_duties": r["max_duties"],
            "effective_max_duties": effective,
        })

    return {
        "count": len(out),
        "rows": out,
    }


# @router.get("/professors/designation-summary", dependencies=[Depends(require_admin)])
# def designation_summary(s: Session = Depends(db)):
#     """
#     Returns per-professor designation and effective max duties
#     after applying designation rules and DB overrides.
#     """

#     rows = s.execute(text("""
#         SELECT
#             id,
#             name,
#             COALESCE(designation, 'Assistant') AS designation,
#             max_duties
#         FROM professors
#         ORDER BY name
#     """)).mappings().all()

#     out = []
#     for r in rows:
#         effective = _effective_max_duties(
#             r["designation"],
#             r["max_duties"]
#         )

#         out.append({
#             "professor_id": r["id"],
#             "name": r["name"],
#             "designation": r["designation"],
#             "configured_max_duties": r["max_duties"],
#             "effective_max_duties": effective,
#         })

#     return {
#         "count": len(out),
#         "rows": out,
#     }
 
# -----------------
# Seating generator (single exam)
# -----------------
@router.post("/plan-seating")
def seating(exam_id: int, _=Depends(require_admin), s: Session = Depends(db)):
    e = s.get(Exam, exam_id)
    if not e:
        raise HTTPException(404, "Exam not found")

    # Prefer enrollments (many-to-many)
    students = s.execute(text("""
        SELECT st.id, st.roll_no, st.name
        FROM student_enrollments se
        JOIN students st ON st.id = se.student_id
        WHERE se.course_code = :cc
        ORDER BY st.roll_no
    """), {"cc": e.course_code}).mappings().all()

    # Fallback to legacy: students.course_code
    if not students:
        students = s.execute(text("""
            SELECT id, roll_no, name
            FROM students
            WHERE course_code = :cc
            ORDER BY roll_no
        """), {"cc": e.course_code}).mappings().all()

    rooms = s.query(Room).order_by(Room.code).all()
    if not rooms:
        return {"seats_assigned": 0, "note": "No rooms found"}

    allocs = []
    r_iter = iter(rooms)
    room = next(r_iter, None)
    cap_used = 0

    for st in students:
        if not room:
            break
        if cap_used >= room.capacity:
            room = next(r_iter, None)
            cap_used = 0
            if not room:
                break
        cap_used += 1
        allocs.append((e.id, room.id, cap_used, st["id"]))

    s.query(SeatingAllocation).filter_by(exam_id=e.id).delete(synchronize_session=False)
    for eid, rid, seat, sid in allocs:
        s.add(SeatingAllocation(exam_id=eid, room_id=rid, seat_no=seat, student_id=sid))
    s.commit()
    return {"seats_assigned": len(allocs)}


# --------------------------------------------
# One professor per exam slot (idempotent) – CUJ-aware, avoid same department
# --------------------------------------------
@router.post("/schedule-duty-one-per-slot", dependencies=[Depends(require_admin)])
def schedule_one_per_slot_endpoint(s: Session = Depends(db)):
    # Pull exams (ordered by date/slot for stability)
    exams = s.execute(text("""
        SELECT
          id,
          exam_date,
          slot,
          course_code,
          department
        FROM exams
        ORDER BY exam_date, slot, id
    """)).mappings().all()
    if not exams:
        return {"assigned_slots": 0, "note": "No exams found"}

    # Professors with max_duties + department_id
    profs = s.execute(text("""
        SELECT
          id,
          COALESCE(max_duties, 999999) AS max_duties,
          department_id
        FROM professors
        ORDER BY id
    """)).mappings().all()
    if not profs:
        return {"assigned_slots": 0, "note": "No professors found"}

    # Availability (prof, date, slot)
    av_rows = s.execute(text("""
        SELECT professor_id, exam_date, slot
        FROM professor_availability
        WHERE available = TRUE
    """)).all()
    availability = {(r[0], r[1], r[2]) for r in av_rows}

    # professor_id -> set(course_code) map (avoid own subject)
    teaches: dict[int, set[str]] = {}
    try:
        teach_rows = s.execute(text("""
            SELECT professor_id, course_code
            FROM professor_courses
        """)).mappings().all()
        for r in teach_rows:
            code = (r["course_code"] or "").upper()
            if not code:
                continue
            teaches.setdefault(r["professor_id"], set()).add(code)
    except Exception:
        teaches = {}

    # department name → id (for exams.department string)
    dept_name_to_id = {}
    for d in s.query(Department).all():
        dept_name_to_id[d.name.strip().lower()] = d.id

    # exam_id -> department_id (if we can map)
    exam_departments: dict[int, int | None] = {}
    for e in exams:
        dept_str = (e["department"] or "").strip().lower() if e["department"] else ""
        exam_departments[e["id"]] = dept_name_to_id.get(dept_str)

    # prof_id -> dept_id
    prof_departments: dict[int, int | None] = {
        p["id"]: p["department_id"] for p in profs
    }

    # Run scheduler
    res = schedule_one_prof_per_slot(
        profs=[dict(id=p["id"], max_duties=p["max_duties"]) for p in profs],
        exams=[
            dict(
                id=e["id"],
                exam_date=e["exam_date"],
                slot=e["slot"],
                course_code=e["course_code"],
            )
            for e in exams
        ],
        availability=availability,
        teaches=teaches,
        avoid_own_subject=True,
        avoid_same_department=True,
        exam_departments=exam_departments,
        prof_departments=prof_departments,
    )

    # Persist results (replace all)
    s.execute(text("DELETE FROM slot_assignments"))
    for exam_id, prof_id in res:
        s.execute(
            text("INSERT INTO slot_assignments (exam_id, professor_id) VALUES (:e, :p)"),
            {"e": exam_id, "p": prof_id},
        )
    s.commit()
    return {"assigned_slots": len(res)}


# ------------------------
# Duty roster (PDF/HTML) – CUJ format
# ------------------------
# ------------------------
# Internal helper for duty queries (tries room join, falls back if table missing)
# ------------------------

def _fetch_duty_rows(
    s: Session,
    where_clause: str = "",
    params: dict | None = None,
):
    """
    Try to fetch duties with venue/floor/room (using seat_assignments + rooms).
    If that fails (e.g. seat_assignments table doesn't exist),
    ROLLBACK the transaction and fall back to the simpler query.
    """

    if params is None:
        params = {}

    where_sql = f"WHERE {where_clause}" if where_clause else ""

    # -------------------------------------------------
    # Attempt 1: Use seat_assignments + rooms
    # -------------------------------------------------
    sql_with_room = f"""
        WITH room_info AS (
            SELECT
                sa2.exam_id,
                MIN(r.building) AS venue,
                MIN(COALESCE(r.floor::text, '')) AS floor,
                MIN(r.code) AS room_allotted
            FROM seat_assignments sa2
            JOIN rooms r ON r.id = sa2.room_id
            GROUP BY sa2.exam_id
        )
        SELECT
          e.exam_date AS date,
          e.slot,
          p.name AS professor_name,
          p.employee_code AS employee_code,
          e.course_code,
          COALESCE(e.course_title, e.course_name) AS course_title,
          ri.venue,
          NULLIF(ri.floor, '') AS floor,
          ri.room_allotted
        FROM slot_assignments sa
        JOIN exams      e ON e.id = sa.exam_id
        JOIN professors p ON p.id = sa.professor_id
        LEFT JOIN room_info ri ON ri.exam_id = e.id
        {where_sql}
        ORDER BY e.exam_date, e.slot, p.name
    """

    # -------------------------------------------------
    # Fallback: NO room dependency (always works)
    # -------------------------------------------------
    sql_no_room = f"""
        SELECT
          e.exam_date AS date,
          e.slot,
          p.name AS professor_name,
          p.employee_code AS employee_code,
          e.course_code,
          COALESCE(e.course_title, e.course_name) AS course_title,
          NULL AS venue,
          NULL AS floor,
          NULL AS room_allotted
        FROM slot_assignments sa
        JOIN exams      e ON e.id = sa.exam_id
        JOIN professors p ON p.id = sa.professor_id
        {where_sql}
        ORDER BY e.exam_date, e.slot, p.name
    """

    try:
        return s.execute(text(sql_with_room), params).mappings().all()

    except Exception as ex:
        # 🔴 IMPORTANT: reset failed transaction
        s.rollback()

        # Safe fallback (never fails)
        return s.execute(text(sql_no_room), params).mappings().all()

    
# ------------------------
# Duty roster (PDF/HTML) – CUJ format
# ------------------------
@router.get("/duty-pdf-one-per-slot")
def duty_pdf_one_per_slot(_=Depends(require_admin)):
    with SessionLocal() as s:
        rows = _fetch_duty_rows(s)

    content, fname, media_type = render_pdf_or_html_download(
        "duty_one_per_slot.html", {"rows": rows}
    )
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{fname}"'}
    )


@router.get("/duty-preview-one-per-slot")
def duty_preview_one_per_slot(_=Depends(require_admin)):
    with SessionLocal() as s:
        rows = _fetch_duty_rows(s)
    return {"rows": list(rows)}


# ------------------------
# Duty roster filtered by SCHOOL
# ------------------------
@router.get("/duty-pdf-by-school")
def duty_pdf_by_school(school: str, _=Depends(require_admin)):
    with SessionLocal() as s:
        rows = _fetch_duty_rows(
            s,
            where_clause="e.school = :school",
            params={"school": school},
        )

    if not rows:
        raise HTTPException(404, detail=f"No duties found for school '{school}'.")

    safe_school = school.replace(" ", "_")
    content, fname, media_type = render_pdf_or_html_download(
        "duty_one_per_slot.html",
        {
            "rows": rows,
            "filter_label": f"School: {school}",
        },
    )
    disposition = f'attachment; filename="duty_{safe_school}.pdf"'
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": disposition}
    )


# ------------------------
# Duty roster filtered by DEPARTMENT
# ------------------------
@router.get("/duty-pdf-by-department")
def duty_pdf_by_department(department: str, _=Depends(require_admin)):
    with SessionLocal() as s:
        rows = _fetch_duty_rows(
            s,
            where_clause="e.department = :dept",
            params={"dept": department},
        )

    if not rows:
        raise HTTPException(404, detail=f"No duties found for department '{department}'.")

    safe_dept = department.replace(" ", "_")
    content, fname, media_type = render_pdf_or_html_download(
        "duty_one_per_slot.html",
        {
            "rows": rows,
            "filter_label": f"Department: {department}",
        },
    )
    disposition = f'attachment; filename="duty_{safe_dept}.pdf"'
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": disposition}
    )


# ------------------------
# Email single-exam roster
# ------------------------
@router.post("/email-roster")
async def email_roster(exam_id: int, _=Depends(require_admin), s: Session = Depends(db)):
    exam = s.execute(text("""
        SELECT
          id,
          exam_date AS date,
          slot,
          course_code AS subject_code,
          COALESCE(course_title, course_name) AS subject_name
        FROM exams
        WHERE id = :eid
    """), {"eid": exam_id}).mappings().first()

    if not exam:
        raise HTTPException(404, "Exam not found")

    roster = s.execute(text("""
        SELECT
          p.name AS professor_name,
          p.email,
          p.employee_code AS employee_code
        FROM slot_assignments sa
        JOIN professors p ON p.id = sa.professor_id
        WHERE sa.exam_id = :eid
        ORDER BY p.name
    """), {"eid": exam_id}).mappings().all()

    if not roster:
        raise HTTPException(404, "No slot assignment found for this exam.")

    # Build rows compatible with duty_one_per_slot.html CUJ format
    rows = [{
        "date": exam["date"],
        "slot": exam["slot"],
        "professor_name": r["professor_name"],
        "employee_code": r["employee_code"],
        "course_code": exam["subject_code"],
        "course_title": exam["subject_name"],
        "venue": None,
        "floor": None,
        "room_allotted": None,
    } for r in roster]

    attachment_bytes, attach_name, attach_mime = render_pdf_or_html_download(
        "duty_one_per_slot.html", {"rows": rows}
    )

    subj = f"Invigilation Duty – {exam['subject_code']} ({exam['date']} {exam['slot']})"
    html = f"""
      <p>Dear Colleague,</p>
      <p>You are assigned invigilation duty for <b>{exam['subject_code']}: {exam['subject_name']}</b>
      on <b>{exam['date']} ({exam['slot']})</b>.</p>
      <p>Duty details are attached.</p>
      <p>Regards,<br/>Exam Cell</p>
    """

    for r in roster:
        await send_mail(
            r["email"],
            subj,
            html,
            attachments=[(attach_name, attachment_bytes, attach_mime)],
        )

    return {"emailed_to": [r["email"] for r in roster]}


# ------------------------
# Seating plan (PDF/HTML) — single exam (CUJ format)
# ------------------------
@router.get("/seating-pdf")
def seating_pdf(exam_id: int, _=Depends(require_admin)):
    with SessionLocal() as s:
        rows = s.execute(text("""
            SELECT
              r.code        AS room_code,
              r.capacity    AS capacity,
              sa.seat_no    AS seat_no,
              st.roll_no    AS roll_no,
              st.name       AS student_name,
              COALESCE(e.course_title, e.course_name) AS subject_name,
              e.course_code AS subject_code,
              e.exam_date   AS date,
              e.slot        AS slot,
              r.building    AS venue,
              r.floor       AS floor
            FROM seating_allocations sa
            JOIN rooms    r ON r.id = sa.room_id
            JOIN students st ON st.id = sa.student_id
            JOIN exams    e ON e.id = sa.exam_id
            WHERE sa.exam_id = :exam_id
            ORDER BY e.exam_date, e.slot, r.code, sa.seat_no
        """), {"exam_id": exam_id}).mappings().all()

    if not rows:
        raise HTTPException(404, "No seating found for this exam")

    building_name = rows[0]["venue"] or "Exam Halls"

    content, fname, media_type = render_pdf_or_html_download(
        "seating_plan.html", {"rows": rows, "building_name": building_name}
    )
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{fname}"'}
    )



# ============================
# Generate seating for ALL exams
# ============================
@router.post("/plan-seating-all", dependencies=[Depends(require_admin)])
def plan_seating_all(s: Session = Depends(db)):
    exams = s.execute(text("""
        SELECT id, course_code
        FROM exams
        ORDER BY exam_date, slot, id
    """)).mappings().all()
    if not exams:
        return {"seats_assigned_total": 0, "per_exam": []}

    rooms = s.query(Room).order_by(Room.code).all()
    if not rooms:
        return {"seats_assigned_total": 0, "per_exam": [], "note": "No rooms found"}

    total = 0
    per_exam = []

    for e in exams:
        students = s.execute(text("""
            SELECT st.id, st.roll_no, st.name
            FROM student_enrollments se
            JOIN students st ON st.id = se.student_id
            WHERE se.course_code = :cc
            ORDER BY st.roll_no
        """), {"cc": e["course_code"]}).mappings().all()

        if not students:
            students = s.execute(text("""
                SELECT id, roll_no, name
                FROM students
                WHERE course_code = :cc
                ORDER BY roll_no
            """), {"cc": e["course_code"]}).mappings().all()

        if not students:
            per_exam.append({"exam_id": e["id"], "seats_assigned": 0})
            continue

        allocs = []
        r_iter = iter(rooms)
        room = next(r_iter, None)
        cap_used = 0

        for st in students:
            if not room:
                break
            if cap_used >= room.capacity:
                room = next(r_iter, None)
                cap_used = 0
                if not room:
                    break
            cap_used += 1
            allocs.append((e["id"], room.id, cap_used, st["id"]))

        s.query(SeatingAllocation).filter_by(exam_id=e["id"]).delete(synchronize_session=False)
        for eid, rid, seat, sid in allocs:
            s.add(SeatingAllocation(exam_id=eid, room_id=rid, seat_no=seat, student_id=sid))

        cnt = len(allocs)
        total += cnt
        per_exam.append({"exam_id": e["id"], "seats_assigned": cnt})

    s.commit()
    return {"seats_assigned_total": total, "per_exam": per_exam}


# ============================
# One PDF for ALL exams (CUJ seating format)
# ============================
@router.get("/seating-pdf-all", dependencies=[Depends(require_admin)])
def seating_pdf_all():
    with SessionLocal() as s:
        rows = s.execute(text("""
            SELECT
              r.code        AS room_code,
              r.capacity    AS capacity,
              sa.seat_no    AS seat_no,
              st.roll_no    AS roll_no,
              st.name       AS student_name,
              COALESCE(e.course_title, e.course_name) AS subject_name,
              e.course_code AS subject_code,
              e.exam_date   AS date,
              e.slot        AS slot,
              r.building    AS venue,
              r.floor       AS floor
            FROM seating_allocations sa
            JOIN rooms    r ON r.id = sa.room_id
            JOIN students st ON st.id = sa.student_id
            JOIN exams    e ON e.id = sa.exam_id
            ORDER BY e.exam_date, e.slot, r.code, sa.seat_no
        """)).mappings().all()

    building_name = rows[0]["venue"] if rows else "Exam Halls"

    content, fname, media_type = render_pdf_or_html_download(
        "seating_plan.html", {"rows": rows, "building_name": building_name}
    )
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": 'attachment; filename="seating_all_exams.pdf"'}
    )



# ============================
# Mixed generator – TWO DIFFERENT YEARS PER BENCH (CUJ-aware)
# ============================
@router.post("/plan-seating-all-mixed", dependencies=[Depends(require_admin)])
def plan_seating_all_mixed(order: str = "Y1_FIRST", s: Session = Depends(db)):
    """
    Build seating across ALL exams, grouped by (exam_date, slot).

    Goal:
      - Preserve "paired" ordering so that two different academic years
        tend to sit next to each other.
      - seat_no remains UNIQUE per (exam_id, room_id) to satisfy DB constraint.
        (Conceptually, two consecutive seat_nos form a bench.)
    """

    exams = s.execute(text("""
        SELECT
          id,
          exam_date,
          slot,
          course_code,
          COALESCE(course_title, course_name) AS course_name
        FROM exams
        ORDER BY exam_date, slot, id
    """)).mappings().all()
    if not exams:
        return {"seats_assigned_total": 0, "note": "No exams found"}

    rooms = s.execute(text("""
        SELECT id, code, capacity
        FROM rooms
        ORDER BY code
    """)).mappings().all()
    if not rooms:
        return {"seats_assigned_total": 0, "note": "No rooms found"}

    # Group exams by (date, slot)
    by_ds: dict[tuple, list[dict]] = {}
    for e in exams:
        by_ds.setdefault((e["exam_date"], e["slot"]), []).append(e)

    # Clear existing seating (fresh plan)
    s.execute(text("DELETE FROM seating_allocations"))

    total_assigned = 0
    per_bucket = []

    for (d, slot), exs in by_ds.items():
        # ---- Build groups: Y1, Y2, Y3, UNK ----
        by_group: dict[str, list[tuple]] = {}
        total_students_for_bucket = 0

        def group_from_roll(roll: str) -> str:
            """
            Y1/Y2/... using CUJ logic; UNK if we can't figure out.
            """
            yr = academic_year_from_roll_cuj(roll, d)
            if yr is not None:
                return f"Y{yr}"
            return "UNK"

        for e in exs:
            st_rows = s.execute(text("""
                SELECT st.id AS student_id, st.roll_no, st.name
                FROM student_enrollments se
                JOIN students st ON st.id = se.student_id
                WHERE se.course_code = :cc
                ORDER BY st.roll_no
            """), {"cc": e["course_code"]}).mappings().all()

            # Legacy fallback if no enrollments table used
            if not st_rows:
                st_rows = s.execute(text("""
                    SELECT id AS student_id, roll_no, name
                    FROM students
                    WHERE course_code = :cc
                    ORDER BY roll_no
                """), {"cc": e["course_code"]}).mappings().all()

            for st in st_rows:
                roll = st["roll_no"] or ""
                grp = group_from_roll(roll)
                rec = (
                    e["id"],           # exam_id
                    st["student_id"],  # student_id
                    roll,
                    st["name"],
                )
                by_group.setdefault(grp, []).append(rec)
                total_students_for_bucket += 1

        if total_students_for_bucket == 0:
            per_bucket.append({
                "date": d.isoformat() if hasattr(d, "isoformat") else str(d),
                "slot": slot,
                "students": 0,
                "benches_used": 0,
            })
            continue

        # ---- Greedy pairing: prefer cross-group (different years) ----
        groups = list(by_group.keys())
        paired: list[list[tuple]] = []

        # 1) Cross-group pairing
        while True:
            non_empty = [g for g in groups if by_group.get(g)]
            if len(non_empty) < 2:
                break
            g1, g2 = non_empty[0], non_empty[1]
            s1 = by_group[g1].pop(0)
            s2 = by_group[g2].pop(0)
            paired.append([s1, s2])

        # 2) Within-group pairing for leftovers
        for g in groups:
            lst = by_group.get(g, [])
            for i in range(0, len(lst), 2):
                pair = [lst[i]]
                if i + 1 < len(lst):
                    pair.append(lst[i + 1])
                paired.append(pair)

        # ---- Assign seats to rooms (keep pair adjacency, no duplicate seat_no) ----
        r_iter = iter(rooms)
        room = next(r_iter, None)
        seat_in_room = 0
        seats_assigned_bucket = 0

        for pair in paired:
            for rec in pair:
                if not room:
                    break
                if seat_in_room >= room["capacity"]:
                    room = next(r_iter, None)
                    seat_in_room = 0
                    if not room:
                        break

                seat_in_room += 1
                exam_id, student_id, _roll, _name = rec
                s.add(SeatingAllocation(
                    exam_id=exam_id,
                    room_id=room["id"],
                    seat_no=seat_in_room,
                    student_id=student_id,
                ))
                total_assigned += 1
                seats_assigned_bucket += 1

        benches_used = (seats_assigned_bucket + 1) // 2  # approx: 2 seats per bench

        per_bucket.append({
            "date": d.isoformat() if hasattr(d, "isoformat") else str(d),
            "slot": slot,
            "students": total_students_for_bucket,
            "benches_used": benches_used,
        })

    s.commit()
    return {
        "seats_assigned_total": total_assigned,
        "buckets": per_bucket,
    }


# ============================
# CUJ Roll Debug API
# ============================
@router.get("/roll-debug", dependencies=[Depends(require_admin)])
def roll_debug(
    roll: str,
    exam_date: date | None = None,
    s: Session = Depends(db),
):
    """
    Debug helper for CUJ roll numbers.

    Query:
      ?roll=24MMBA01&exam_date=2025-05-10

    Uses db.cuj_roll.parse_cuj_roll to return:
      - batch_suffix (e.g. 24)
      - batch_year   (e.g. 2024)
      - academic_year (1/2/3/4...)
      - program_code (e.g. MMBA)
      - derived department/school (from academic_programs, if present)
    """

    info = parse_cuj_roll(roll, exam_date, s)
    prog = info.get("program")

    # Don't return ORM objects directly
    if "program" in info:
        info = {k: v for k, v in info.items() if k != "program"}

    program_payload = None
    if prog is not None:
        program_payload = {
            "id": prog.id,
            "code_prefix": prog.code_prefix,
            "degree_type": prog.degree_type,
            "level": prog.level,
            "department_id": prog.department_id,
            "department_name": prog.department_name,
            "school_name": prog.school_name,
        }

    return {
        "roll": roll,
        "exam_date": exam_date.isoformat() if exam_date else None,
        **info,
        "program": program_payload,
    }


# ------------------------
# Seating plan (one layout – list all courses per student)
# Includes ALL allocations on the same date/slot.
# ------------------------
@router.get("/seating-pdf-by-student", dependencies=[Depends(require_admin)])
def seating_pdf_by_student(exam_id: int, department: str | None = None):
    """
    One row per student (for ALL exams on the same date/slot as exam_id).
    If 'department' is provided, restrict to exams.department = department.

    Also:
      - derives building_name from rooms.building
      - shows all registered courses per student
    """
    with SessionLocal() as s:
        ref = s.execute(text("""
            SELECT exam_date, slot
            FROM exams
            WHERE id = :eid
        """), {"eid": exam_id}).mappings().first()
        if not ref:
            raise HTTPException(404, "Reference exam not found")

        params = {"d": ref["exam_date"], "slot": ref["slot"]}
        dept_filter = ""
        if department:
            dept_filter = " AND e.department = :dept "
            params["dept"] = department

        base = s.execute(text(f"""
            SELECT
              r.code      AS room_code,
              r.capacity  AS capacity,
              r.building  AS venue,
              r.floor     AS floor,
              sa.seat_no  AS seat_no,
              st.id       AS student_id,
              st.roll_no  AS roll_no,
              st.name     AS student_name,
              e.exam_date AS date,
              e.slot      AS slot
            FROM seating_allocations sa
            JOIN rooms    r  ON r.id = sa.room_id
            JOIN students st ON st.id = sa.student_id
            JOIN exams    e  ON e.id = sa.exam_id
            WHERE e.exam_date = :d
              AND e.slot      = :slot
              {dept_filter}
            ORDER BY r.code, sa.seat_no, st.roll_no
        """), params).mappings().all()

        if not base:
            raise HTTPException(
                404,
                "No seating found for this date/slot (and department, if filtered)",
            )

        # Build course list per student across all subjects
        courses = s.execute(text("""
            SELECT t.student_id,
                   STRING_AGG(t.course, E'\n' ORDER BY t.course) AS courses
            FROM (
              SELECT DISTINCT se.student_id,
                     ex.course_code || ' — ' ||
                     COALESCE(ex.course_title, ex.course_name) AS course
              FROM student_enrollments se
              JOIN exams ex ON ex.course_code = se.course_code
            ) t
            GROUP BY t.student_id
        """)).mappings().all()
        course_map = {c["student_id"]: c["courses"] for c in courses}

        # Determine building name (first non-empty room.building)
        building_name = None
        for r in base:
            if r["venue"]:
                building_name = r["venue"]
                break
        if not building_name:
            building_name = "Exam Halls"

        rows = []
        for r in base:
            rows.append({
                "room_code": r["room_code"],
                "capacity": r["capacity"],
                "seat_no": r["seat_no"],
                "roll_no": r["roll_no"],
                "student_name": r["student_name"],
                "courses": course_map.get(r["student_id"], ""),
                "date": r["date"],
                "slot": r["slot"],
                "floor": r["floor"],
                "venue": r["venue"],
            })

    content, fname, media_type = render_pdf_or_html_download(
        "seating_by_student.html",
        {
            "rows": rows,
            "filter_label": department or None,
            "building_name": building_name,
        },
    )
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename=\"{fname}\"'}
    )




# -------------------------------------------------
# Import rooms CSV  (code + capacity + optional building/floor)
# -------------------------------------------------
@router.post("/import/rooms-csv")
def import_rooms_csv(
    file: UploadFile = File(...),
    _=Depends(require_admin),
    s: Session = Depends(db),
):
    """
    CSV required (case-insensitive headers):
      code, capacity

    Optional extra columns:
      building, floor

    Examples:

      code,capacity,building,floor
      B-02,60,Aryabhatta Block,B
      C-19,28,Aryabhatta Block,C
      ANA-1,52,Aryabhatta Block,A

    Behaviour:
      - UPSERT by rooms.code
      - capacity is always updated
      - building/floor are updated if provided (non-empty),
        otherwise the old values are kept.
    """
    content = file.file.read().decode("utf-8", errors="ignore")
    reader = csv.DictReader(StringIO(content))

    if not reader.fieldnames:
        raise HTTPException(400, detail="Empty CSV or missing header row.")

    cols = {(c or "").strip().lower() for c in reader.fieldnames}
    need = {"code", "capacity"}

    if not need.issubset(cols):
        raise HTTPException(
            400,
            detail="Missing columns. Required: ['code','capacity'] Optional: ['building','floor']",
        )

    inserted = 0
    updated = 0

    for row in reader:
        code = (row.get("code") or row.get("Code") or "").strip()
        if not code:
            continue

        cap_raw = (row.get("capacity") or row.get("Capacity") or "").strip()
        if not cap_raw:
            # skip rooms with no capacity
            continue

        try:
            capacity = int(cap_raw)
        except ValueError:
            # bad capacity value – skip this row safely
            continue

        building = (row.get("building") or row.get("Building") or "").strip() or None
        floor = (row.get("floor") or row.get("Floor") or "").strip() or None

        # If your rooms table does NOT yet have building/floor columns,
        # run:
        #   ALTER TABLE rooms ADD COLUMN IF NOT EXISTS building TEXT;
        #   ALTER TABLE rooms ADD COLUMN IF NOT EXISTS floor TEXT;
        res = s.execute(text("""
            INSERT INTO rooms (code, capacity, building, floor)
            VALUES (:code, :capacity, :building, :floor)
            ON CONFLICT (code)
            DO UPDATE SET
              capacity = EXCLUDED.capacity,
              building = COALESCE(EXCLUDED.building, rooms.building),
              floor    = COALESCE(EXCLUDED.floor, rooms.floor)
            RETURNING (xmax = 0) AS inserted
        """), {
            "code": code,
            "capacity": capacity,
            "building": building,
            "floor": floor,
        }).mappings().first()

        if res and res["inserted"]:
            inserted += 1
        else:
            updated += 1

    s.commit()
    return {"inserted": inserted, "updated": updated}



# ---------------------------------------------------------
# Distinct departments from exams (for UI dropdown)
# ---------------------------------------------------------
# @router.get("/departments-list", dependencies=[Depends(require_admin)])
# def departments_list(s: Session = Depends(db)):
#     rows = s.execute(text("""
#         SELECT DISTINCT department
#         FROM exams
#         WHERE department IS NOT NULL AND department <> ''
#         ORDER BY department
#     """)).mappings().all()
#     return [r["department"] for r in rows]

@router.get("/departments-list", dependencies=[Depends(require_admin)])
def departments_list(s: Session = Depends(db)):
    """
    Department dropdown source.

    Uses DISTINCT exams.department so that the UI values
    always match the actual text stored on each exam.
    """
    rows = s.execute(text("""
        SELECT DISTINCT department
        FROM exams
        WHERE department IS NOT NULL AND department <> ''
        ORDER BY department
    """)).mappings().all()

    out = []
    for idx, r in enumerate(rows, start=1):
        name = (r["department"] or "").strip()
        if not name:
            continue
        out.append({"id": idx, "name": name})
    return out



@router.get("/seating-pdf-all-by-department", dependencies=[Depends(require_admin)])
def seating_pdf_all_by_department(department: str):
    dept_pattern = f"%{department}%"
    with SessionLocal() as s:
        rows = s.execute(text("""
            SELECT
              r.code AS room_code,
              r.capacity,
              sa.seat_no,
              st.roll_no AS roll_no,
              st.name AS student_name,
              COALESCE(e.course_title, e.course_name) AS subject_name,
              e.course_code  AS subject_code,
              e.exam_date    AS date,
              e.slot         AS slot,
              NULL AS venue,
              NULL AS floor
            FROM seating_allocations sa
            JOIN rooms    r ON r.id = sa.room_id
            JOIN students st ON st.id = sa.student_id
            JOIN exams    e ON e.id = sa.exam_id
            WHERE e.department ILIKE :dept_pattern
            ORDER BY e.exam_date, e.slot, r.code, sa.seat_no
        """), {"dept_pattern": dept_pattern}).mappings().all()

    if not rows:
        raise HTTPException(404, detail=f"No seating found for department '{department}'")

    content, fname, media_type = render_pdf_or_html_download(
        "seating_plan.html",
        {
            "rows": rows,
            "building_name": f"Aryabhatta Block – {department}",
        },
    )
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": 'attachment; filename="seating_department.pdf"'}
    )



# ============================
# Department-wise seating plan PDF
# ============================
@router.get("/seating-pdf-by-department", dependencies=[Depends(require_admin)])
def seating_pdf_by_department(department: str):
    """
    Department-wise seating plan (ALL exams for that department).

    - Uses existing seating_allocations.
    - Filters by exams.department ILIKE %department%.
    - Renders with seating_plan.html in a single layout.
    """
    dept_pattern = f"%{department}%"

    with SessionLocal() as s:
        rows = s.execute(text("""
            SELECT
              r.code AS room_code,
              r.capacity,
              sa.seat_no,
              st.roll_no AS roll_no,
              st.name AS student_name,
              COALESCE(e.course_title, e.course_name) AS subject_name,
              e.course_code  AS subject_code,
              e.exam_date    AS date,
              e.slot         AS slot,
              r.floor        AS floor,
              NULL           AS venue
            FROM seating_allocations sa
            JOIN rooms    r  ON r.id = sa.room_id
            JOIN students st ON st.id = sa.student_id
            JOIN exams    e  ON e.id = sa.exam_id
            WHERE e.department ILIKE :dept_pattern
            ORDER BY e.exam_date, e.slot, r.code, sa.seat_no
        """), {"dept_pattern": dept_pattern}).mappings().all()

    if not rows:
        raise HTTPException(
            404,
            detail=f"No seating found for department '{department}'. "
                   f"Run seating generation first for exams of this department."
        )

    safe_dept = department.replace(" ", "_")
    building_name = f"Aryabhatta Block – {department}"

    content, fname, media_type = render_pdf_or_html_download(
        "seating_plan.html",
        {
            "rows": rows,
            "building_name": building_name,
        },
    )
    return Response(
        content=content,
        media_type=media_type,
        headers={
            "Content-Disposition": f'attachment; filename="seating_{safe_dept}.pdf"'
        },
    )
