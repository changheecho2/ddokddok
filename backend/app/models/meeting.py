from pydantic import BaseModel
from typing import List
from uuid import UUID
from datetime import date


class Meeting(BaseModel):
    id: UUID
    meeting_date: date
    sequence: int


class AttendanceIn(BaseModel):
    member_id: UUID
    is_attended: bool


class BulkAttendanceIn(BaseModel):
    attendances: List[AttendanceIn]


class AttendanceOut(BaseModel):
    id: UUID
    member_id: UUID
    meeting_id: UUID
    is_attended: bool
