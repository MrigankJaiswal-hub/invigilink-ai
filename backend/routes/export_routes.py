from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session
import pandas as pd
from auth.deps import require_admin
from db.dal import SessionLocal

router = APIRouter(prefix="/admin/export", tags=["admin-export"])

def db():
    with SessionLocal() as s:
        yield s

@router.get("/seating-csv")
def seating_csv(exam_id:int, _=Depends(require_admin), s:Session=Depends(db)):
    rows = s.execute("""
      SELECT r.code as room, sa.seat_no as seat, st.roll_no as roll, st.name as name
      FROM seating_allocations sa
      JOIN rooms r ON r.id=sa.room_id
      JOIN students st ON st.id=sa.student_id
      WHERE sa.exam_id=:eid
      ORDER BY r.code, sa.seat_no
    """, {"eid": exam_id}).mappings().all()
    df = pd.DataFrame(rows)
    return Response(df.to_csv(index=False), media_type="text/csv")

@router.get("/duty-csv-one-per-slot")
def duty_csv_one(_=Depends(require_admin), s:Session=Depends(db)):
    rows = s.execute("""
      SELECT e.exam_date, e.slot, e.course_code, e.course_name, p.name as professor, p.email
      FROM slot_assignments sa
      JOIN exams e ON e.id = sa.exam_id
      JOIN professors p ON p.id = sa.professor_id
      ORDER BY e.exam_date, e.slot, e.course_code
    """).mappings().all()
    df = pd.DataFrame(rows)
    return Response(df.to_csv(index=False), media_type="text/csv")
