# backend/db/cuj_roll.py

import re
from datetime import date
from typing import Optional, Dict, Any

from sqlalchemy.orm import Session

from db.models import AcademicProgram


def extract_batch_suffix(roll: str) -> Optional[int]:
    """
    From '24MMBA01' → 24
    From '23BEECE10' → 23
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


def extract_program_code(roll: str) -> Optional[str]:
    """
    From '24MMBA01' → 'MMBA'
    From '23BEECE10' → 'BEECE'
    """
    if not roll:
        return None
    m = re.match(r"^\d{2}([A-Z]+)", roll.strip().upper())
    if not m:
        return None
    return m.group(1)


def academic_year_from_roll_cuj(roll: str, exam_date: date) -> Optional[int]:
    """
    Use CUJ-style roll: leading 2 digits = batch year suffix.
    Example:
      roll = '23BEECE01', exam_date = 2025 → diff = 25 - 23 = 2 → 3rd year.

    year = diff + 1, only if diff in [0, 5].
    """
    batch = extract_batch_suffix(roll)
    if batch is None:
        return None

    exam_suffix = exam_date.year % 100
    diff = exam_suffix - batch
    if diff < 0 or diff > 5:
        return None
    return diff + 1


def lookup_program_for_roll(roll: str, s: Session) -> Optional[AcademicProgram]:
    """
    First try CODE_PREFIX from '24MMBA01' → 'MMBA' → academic_programs.code_prefix.
    If that fails, try roll_pattern regex match (if configured).
    """
    roll_up = (roll or "").strip().upper()
    if not roll_up:
        return None

    prefix = extract_program_code(roll_up)
    prog = None

    if prefix:
        prog = (
            s.query(AcademicProgram)
            .filter(AcademicProgram.code_prefix == prefix)
            .first()
        )

    if prog:
        return prog

    # Fallback: check regex patterns
    all_programs = s.query(AcademicProgram).all()
    for p in all_programs:
        if p.roll_pattern:
            try:
                if re.match(p.roll_pattern, roll_up):
                    return p
            except re.error:
                # ignore bad patterns
                continue

    return None


def parse_cuj_roll(roll: str, exam_date: Optional[date], s: Session) -> Dict[str, Any]:
    """
    Main helper for CUJ:
    Returns a dict:
      {
        "batch_suffix": int | None,
        "batch_year": int | None,
        "academic_year": int | None,
        "program_code": str | None,
        "program": AcademicProgram | None,
        "department_id": int | None,
        "department_name": str | None,
        "school_name": str | None,
      }
    """
    roll_up = (roll or "").strip().upper()
    batch_suffix = extract_batch_suffix(roll_up)
    batch_year = 2000 + batch_suffix if batch_suffix is not None else None

    academic_year = None
    if exam_date is not None:
        academic_year = academic_year_from_roll_cuj(roll_up, exam_date)

    program = lookup_program_for_roll(roll_up, s)
    program_code = extract_program_code(roll_up)

    return {
        "batch_suffix": batch_suffix,
        "batch_year": batch_year,
        "academic_year": academic_year,
        "program_code": program_code,
        "program": program,
        "department_id": program.department_id if program else None,
        "department_name": program.department_name if program else None,
        "school_name": program.school_name if program else None,
    }
