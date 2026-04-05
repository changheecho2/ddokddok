from pydantic import BaseModel
from typing import List, Optional
from uuid import UUID
from datetime import datetime


class JournalCheck(BaseModel):
    journal_id: UUID
    is_written: bool


class CommentCheck(BaseModel):
    journal_id: UUID
    is_satisfied: bool


class MeetingAttendance(BaseModel):
    meeting_id: UUID
    is_attended: bool


class DepositHistoryItem(BaseModel):
    id: UUID
    reason: str
    amount: int
    applied_at: datetime
    memo: Optional[str] = None


class DepositAdjustIn(BaseModel):
    reason: str
    amount: int  # 음수: 차감, 양수: 환급
    memo: Optional[str] = None


class DepositAdjustOut(BaseModel):
    deposit_balance: int
    history: DepositHistoryItem


class SmallGroupUpdateIn(BaseModel):
    satisfied: Optional[bool]  # True / False / None(초기화)


class MemberDetail(BaseModel):
    id: UUID
    name: str
    deposit_balance: int
    small_group_satisfied: Optional[bool]
    meeting_attendances: List[MeetingAttendance]
    journal_checks: List[JournalCheck]
    comment_checks: List[CommentCheck]
    deposit_history: List[DepositHistoryItem]
