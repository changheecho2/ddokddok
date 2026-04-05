from pydantic import BaseModel
from typing import Optional
from uuid import UUID
from datetime import date


class SmallGroupAttendanceIn(BaseModel):
    member_id: UUID
    attended_date: date
    note: Optional[str] = None


class SmallGroupAttendanceOut(BaseModel):
    id: UUID
    member_id: UUID
    attended_date: date
    note: Optional[str] = None
