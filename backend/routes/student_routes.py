from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from db.dal import SessionLocal

router = APIRouter(prefix="/student", tags=["student"])

def db():
    with SessionLocal() as s:
        yield s

@router.get("/find-seat")
def find_seat(roll_no: str, exam_id: int, s:Session=Depends(db)):
    q = s.execute("""
      SELECT e.exam_date, e.slot, e.course_code, e.course_name,
             r.code AS room_code, sa.seat_no
      FROM seating_allocations sa
      JOIN students st ON st.id = sa.student_id
      JOIN exams e ON e.id = sa.exam_id
      JOIN rooms r ON r.id = sa.room_id
      WHERE st.roll_no = :roll AND sa.exam_id = :eid
    """, {"roll": roll_no.strip(), "eid": exam_id}).mappings().first()
    if not q:
        raise HTTPException(404, "No seat found for this roll number & exam.")
    return {"date": str(q["exam_date"]), "slot": q["slot"],
            "course_code": q["course_code"], "course_name": q["course_name"],
            "room": q["room_code"], "seat_no": q["seat_no"]}
