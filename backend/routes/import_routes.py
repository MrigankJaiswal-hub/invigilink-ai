from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
import pandas as pd
import csv
from io import StringIO
from datetime import datetime, date

from auth.deps import require_admin
from db.dal import SessionLocal
from db.models import (
    School,
    Department,
    Professor,
    Room,
    Exam,
    Student,
    ProfessorAvailability,
)

router = APIRouter(prefix="/admin/import", tags=["admin-import"])

def db():
    with SessionLocal() as s:
        yield s

# ----------------------
# helpers
# ----------------------
def _get_or_create(s: Session, model, where: dict, defaults: dict = None):
    obj = s.query(model).filter_by(**where).first()
    if obj:
        return obj
    data = {**where, **(defaults or {})}
    obj = model(**data)
    s.add(obj)
    s.flush()
    return obj

def _parse_date_any(v: str) -> date:
    v = (v or "").strip()
    if not v:
        raise ValueError("empty date")
    for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(v, fmt).date()
        except ValueError:
            pass
    raise ValueError(f"Unrecognized date: {v}")

def _norm_slot(v: str) -> str:
    v = (v or "").strip().upper()
    if v in {"FN", "FORENOON", "AM", "MORNING"}:
        return "FN"
    if v in {"AN", "AFTERNOON", "PM", "EVENING"}:
        return "AN"
    return v or "FN"

def _parse_bool(v: str) -> bool:
    return str(v).strip().lower() in {"1", "true", "yes", "y"}


# ----------------------
# Professors
# ----------------------
@router.post("/professors-csv")
def import_professors_csv(
    file: UploadFile = File(...),
    _=Depends(require_admin),
    s: Session = Depends(db),
):
    df = pd.read_csv(file.file)
    req_cols = {"name", "email", "school", "department", "max_duties"}
    if not req_cols.issubset(df.columns):
        raise HTTPException(400, f"Missing columns. Required: {sorted(req_cols)}")

    for _, r in df.iterrows():
        sch = _get_or_create(s, School, {"name": str(r["school"]).strip()})
        dep = _get_or_create(
            s,
            Department,
            {"name": str(r["department"]).strip()},
            {"school_id": sch.id},
        )
        email = str(r["email"]).strip()
        prof = s.query(Professor).filter_by(email=email).first()
        maxd = int(r["max_duties"]) if pd.notna(r["max_duties"]) else 3
        if prof:
            prof.name = str(r["name"]).strip()
            prof.department_id = dep.id
            prof.max_duties = maxd
        else:
            s.add(
                Professor(
                    name=str(r["name"]).strip(),
                    email=email,
                    department_id=dep.id,
                    max_duties=maxd,
                )
            )
    s.commit()
    return {"imported": len(df)}


# ----------------------
# Rooms
# ----------------------
@router.post("/rooms-csv")
def import_rooms_csv(
    file: UploadFile = File(...),
    _=Depends(require_admin),
    s: Session = Depends(db),
):
    df = pd.read_csv(file.file)
    req_cols = {"code", "capacity"}
    if not req_cols.issubset(df.columns):
        raise HTTPException(400, f"Missing columns. Required: {sorted(req_cols)}")

    for _, r in df.iterrows():
        code = str(r["code"]).strip()
        room = s.query(Room).filter_by(code=code).first()
        cap = int(r["capacity"])
        is_block = bool(r.get("is_block", False))
        if room:
            room.capacity = cap
            room.is_block = is_block
        else:
            s.add(Room(code=code, capacity=cap, is_block=is_block))
    s.commit()
    return {"imported": len(df)}


# ----------------------
# Exams (normalized importer)
# ----------------------
@router.post("/exams-csv")
def import_exams_csv(
    file: UploadFile = File(...),
    _=Depends(require_admin),
    s: Session = Depends(db),
):
    df = pd.read_csv(file.file)
    req_cols = {
        "course_code",
        "course_name",
        "exam_date",
        "slot",
        "duration_minutes",
        "school",
        "department",
    }
    if not req_cols.issubset(df.columns):
        raise HTTPException(400, f"Missing columns. Required: {sorted(req_cols)}")

    for _, r in df.iterrows():
        _get_or_create(s, School, {"name": str(r["school"]).strip()})
        _get_or_create(s, Department, {"name": str(r["department"]).strip()})

        code = str(r["course_code"]).strip()
        name = str(r["course_name"]).strip()
        d = pd.to_datetime(r["exam_date"]).date()
        slot = str(r["slot"]).strip()
        mins = int(r["duration_minutes"])

        # Upsert on (exam_date, slot, course_code)
        s.execute(
            text(
                """
            INSERT INTO exams (course_code, course_name, exam_date, slot, duration_minutes, school, department)
            VALUES (:code, :name, :d, :slot, :mins, :school, :dept)
            ON CONFLICT (exam_date, slot, course_code)
            DO UPDATE SET
                course_name = EXCLUDED.course_name,
                duration_minutes = EXCLUDED.duration_minutes,
                school = EXCLUDED.school,
                department = EXCLUDED.department
            """
            ),
            {
                "code": code,
                "name": name,
                "d": d,
                "slot": slot,
                "mins": mins,
                "school": str(r["school"]).strip(),
                "dept": str(r["department"]).strip(),
            },
        )
    s.commit()
    return {"upserted": len(df)}


# ----------------------
# Students (legacy, with course_code)
# ----------------------
@router.post("/students-csv")
def import_students_csv(
    file: UploadFile = File(...),
    _=Depends(require_admin),
    s: Session = Depends(db),
):
    df = pd.read_csv(file.file)
    req_cols = {"roll_no", "name", "course_code", "school", "department", "batch"}
    if not req_cols.issubset(df.columns):
        raise HTTPException(400, f"Missing columns. Required: {sorted(req_cols)}")

    for _, r in df.iterrows():
        _get_or_create(s, School, {"name": str(r["school"]).strip()})
        _get_or_create(s, Department, {"name": str(r["department"]).strip()})

        roll = str(r["roll_no"]).strip()
        name = str(r["name"]).strip()
        course = str(r["course_code"]).strip()

        st = s.query(Student).filter_by(roll_no=roll).first()
        if st:
            st.name = name
            st.course_code = course
        else:
            s.add(Student(roll_no=roll, name=name, course_code=course))
    s.commit()
    return {"imported": len(df)}


# ----------------------
# Students (lean: Roll No, Name)  **FIXED PATH**
# ----------------------
@router.post("/students-lean-csv")
def import_students_lean_csv(
    file: UploadFile = File(...),
    _=Depends(require_admin),
    s: Session = Depends(db),
):
    """
    CSV required headers (case-insensitive): Roll No, Name
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

        existing = s.execute(
            text("SELECT id FROM students WHERE roll_no = :r"), {"r": roll}
        ).scalar()
        if existing:
            s.execute(
                text("UPDATE students SET name=:n WHERE id=:id"),
                {"n": name, "id": existing},
            )
        else:
            s.execute(
                text("INSERT INTO students (roll_no, name) VALUES (:r, :n)"),
                {"r": roll, "n": name},
            )
            inserted += 1

    s.commit()
    return {"imported": inserted}


# ----------------------
# Availability (email OR name)
# ----------------------
@router.post("/availability-csv")
def import_availability_csv(
    file: UploadFile = File(...),
    _=Depends(require_admin),
    s: Session = Depends(db),
):
    """
    CSV headers (case-insensitive). One of these must be present:
      professor_email OR professor_name
    Plus:
      exam_date, slot, available

    Examples:
      professor_email,professor_name,exam_date,slot,available
      ,Dr S K Gupta,2025-10-13,FN,true
      23beece01.ece@cujammu.ac.in,,2025-10-13,AN,true
    """
    content = file.file.read().decode("utf-8", errors="ignore")
    rdr = csv.DictReader(StringIO(content))
    if not rdr.fieldnames:
        raise HTTPException(400, detail="Empty CSV")

    cols = {c.strip().lower() for c in rdr.fieldnames}
    if not {"exam_date", "slot", "available"}.issubset(cols) or not (
        "professor_email" in cols or "professor_name" in cols
    ):
        raise HTTPException(
            400,
            detail=(
                "Missing columns. Required: exam_date, slot, available and either "
                "professor_email or professor_name"
            ),
        )

    # build lookups
    prof_by_email = {
        r["email"]: r["id"]
        for r in s.execute(
            text("SELECT id, COALESCE(email,'') AS email FROM professors")
        ).mappings()
        if r["email"]
    }
    prof_by_name = {
        r["name"].strip().lower(): r["id"]
        for r in s.execute(text("SELECT id, name FROM professors")).mappings()
        if r["name"]
    }

    inserted = 0
    updated = 0
    skipped = 0

    for row in rdr:
        email = (row.get("professor_email") or "").strip()
        name = (row.get("professor_name") or "").strip()

        prof_id = None
        if email:
            prof_id = prof_by_email.get(email)
        if prof_id is None and name:
            prof_id = prof_by_name.get(name.strip().lower())
        if prof_id is None:
            skipped += 1
            continue

        d = _parse_date_any(row.get("exam_date") or "")
        slot = _norm_slot(row.get("slot") or "")
        avail = _parse_bool(row.get("available") or "")

        # upsert by delete+insert (works even without a unique constraint)
        s.execute(
            text(
                "DELETE FROM professor_availability "
                "WHERE professor_id=:p AND exam_date=:d AND slot=:slot"
            ),
            {"p": prof_id, "d": d, "slot": slot},
        )
        res = s.execute(
            text(
                "INSERT INTO professor_availability "
                "(professor_id, exam_date, slot, available) "
                "VALUES (:p, :d, :slot, :a) "
                "RETURNING 1"
            ),
            {"p": prof_id, "d": d, "slot": slot, "a": avail},
        ).scalar()

        if res:
            # since we deleted first, count as inserted (or updated if it replaced)
            # we can decide to count as inserted for simplicity
            inserted += 1

    s.commit()
    return {"inserted": inserted, "updated": updated, "skipped_unmatched": skipped}


# ----------------------
# Professor ↔ Course mapping (email OR name)
# ----------------------
@router.post("/professor-courses-csv")
def import_professor_courses_csv(
    file: UploadFile = File(...),
    _=Depends(require_admin),
    s: Session = Depends(db),
):
    """
    CSV headers (case-insensitive). Required: course_code and either
    professor_email or professor_name.

    Example rows:
      professor_email,professor_name,course_code
      ,Dr S K Gupta,BEECE3C001
      23beece01.ece@cujammu.ac.in,,BEECE3C002
    """
    content = file.file.read().decode("utf-8", errors="ignore")
    rdr = csv.DictReader(StringIO(content))
    if not rdr.fieldnames:
        raise HTTPException(400, detail="Empty CSV")

    cols = {c.strip().lower() for c in rdr.fieldnames}
    if "course_code" not in cols or not (
        "professor_email" in cols or "professor_name" in cols
    ):
        raise HTTPException(
            400,
            detail="Missing columns. Required: course_code and either professor_email or professor_name",
        )

    prof_by_email = {
        r["email"]: r["id"]
        for r in s.execute(
            text("SELECT id, COALESCE(email,'') AS email FROM professors")
        ).mappings()
        if r["email"]
    }
    prof_by_name = {
        r["name"].strip().lower(): r["id"]
        for r in s.execute(text("SELECT id, name FROM professors")).mappings()
        if r["name"]
    }

    inserted = 0
    skipped = 0

    for row in rdr:
        email = (row.get("professor_email") or "").strip()
        name = (row.get("professor_name") or "").strip()
        code = (row.get("course_code") or "").strip().upper()
        if not code:
            continue

        prof_id = None
        if email:
            prof_id = prof_by_email.get(email)
        if prof_id is None and name:
            prof_id = prof_by_name.get(name.strip().lower())
        if prof_id is None:
            skipped += 1
            continue

        # insert if missing (works with or without a unique constraint)
        exists = s.execute(
            text(
                "SELECT 1 FROM professor_courses WHERE professor_id=:p AND course_code=:c LIMIT 1"
            ),
            {"p": prof_id, "c": code},
        ).scalar()
        if not exists:
            s.execute(
                text(
                    "INSERT INTO professor_courses (professor_id, course_code) VALUES (:p, :c)"
                ),
                {"p": prof_id, "c": code},
            )
            inserted += 1

    s.commit()
    return {"inserted": inserted, "skipped_unmatched": skipped}
