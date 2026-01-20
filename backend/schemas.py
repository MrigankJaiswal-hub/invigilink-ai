from pydantic import BaseModel
from typing import List

class RunScheduleRequest(BaseModel):
    exam_ids: List[int]

class RunSeatingRequest(BaseModel):
    exam_id: int
