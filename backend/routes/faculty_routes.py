from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from auth.deps import require_faculty
from db.dal import SessionLocal

router = APIRouter(prefix="/faculty", tags=["faculty"])

def db():
    with SessionLocal() as s:
        yield s

@router.get("/my-duties")
def my_duties(user=Depends(require_faculty), s:Session=Depends(db)):
    email = user["sub"]
    rows = s.execute("""
      SELECT e.exam_date, e.slot, e.course_code, e.course_name
      FROM users u
      JOIN slot_assignments sa ON sa.professor_id = u.professor_id
      JOIN exams e ON e.id = sa.exam_id
      WHERE u.email = :email
      ORDER BY e.exam_date, e.slot, e.course_code
    """, {"email": email}).mappings().all()
    return [{"date": str(r["exam_date"]),
             "slot": r["slot"],
             "course_code": r["course_code"],
             "course_name": r["course_name"]} for r in rows]
