from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from db.dal import SessionLocal
from db.models import Exam

router = APIRouter(prefix="/public", tags=["public"])

def db():
    with SessionLocal() as s:
        yield s

@router.get("/exams")
def list_exams(s:Session=Depends(db)):
    rows = s.query(Exam).order_by(Exam.exam_date, Exam.slot, Exam.course_code).all()
    return [{"id":e.id,"course_code":e.course_code,"course_name":e.course_name,
             "date":e.exam_date.isoformat(),"slot":e.slot} for e in rows]
