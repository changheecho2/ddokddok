"""디스코드 알림 라우터"""
from datetime import date
from typing import Optional

from fastapi import APIRouter, Query
from pydantic import BaseModel

from app.services.discord_notify import (
    build_journal_warning,
    build_journal_result,
    build_comment_warning,
    build_comment_result,
    send_discord_message,
    today_kst,
)

router = APIRouter(prefix="/notify", tags=["notify"])


class NotifyResponse(BaseModel):
    message_type: str
    message: Optional[str]
    sent: bool


@router.post("/journal/warning", response_model=NotifyResponse)
def journal_warning(ref_date: Optional[str] = Query(default=None)):
    """일지 마감 3시간 전 경고."""
    d = date.fromisoformat(ref_date) if ref_date else today_kst()
    msg = build_journal_warning(d)
    if msg:
        send_discord_message(msg)
    return NotifyResponse(message_type="journal_warning", message=msg, sent=msg is not None)


@router.post("/journal/result", response_model=NotifyResponse)
def journal_result(ref_date: Optional[str] = Query(default=None)):
    """일지 마감 후 결과."""
    d = date.fromisoformat(ref_date) if ref_date else today_kst()
    msg = build_journal_result(d)
    if msg:
        send_discord_message(msg)
    return NotifyResponse(message_type="journal_result", message=msg, sent=msg is not None)


@router.post("/comment/warning", response_model=NotifyResponse)
def comment_warning(ref_date: Optional[str] = Query(default=None)):
    """댓글 마감 3시간 전 경고."""
    d = date.fromisoformat(ref_date) if ref_date else today_kst()
    msg = build_comment_warning(d)
    if msg:
        send_discord_message(msg)
    return NotifyResponse(message_type="comment_warning", message=msg, sent=msg is not None)


@router.post("/comment/result", response_model=NotifyResponse)
def comment_result(ref_date: Optional[str] = Query(default=None)):
    """댓글 마감 후 결과."""
    d = date.fromisoformat(ref_date) if ref_date else today_kst()
    msg = build_comment_result(d)
    if msg:
        send_discord_message(msg)
    return NotifyResponse(message_type="comment_result", message=msg, sent=msg is not None)


@router.post("/check", response_model=dict)
def check_and_notify():
    """오늘 날짜 기준으로 알림이 필요한지 확인하고 자동 전송.

    cron job에서 호출하는 엔드포인트.
    - 매일 21:00 KST 호출 → check_date/comment_check_date가 내일인 일지의 경고 알림
    - 매일 00:10 KST 호출 → check_date/comment_check_date가 오늘인 일지의 결과 알림
    """
    today = today_kst()
    sent = []

    # 경고: 오늘이 마감일인 일지/댓글 (21:00에 호출 시 마감 3시간 전)
    for builder, label in [
        (build_journal_warning, "journal_warning"),
        (build_comment_warning, "comment_warning"),
    ]:
        msg = builder(today)
        if msg:
            send_discord_message(msg)
            sent.append(label)

    # 결과: 어제가 마감일이었던 일지/댓글 (00:10에 호출 시 마감 후)
    from datetime import timedelta
    yesterday = today - timedelta(days=1)
    for builder, label in [
        (build_journal_result, "journal_result"),
        (build_comment_result, "comment_result"),
    ]:
        msg = builder(yesterday)
        if msg:
            send_discord_message(msg)
            sent.append(label)

    return {"date": today.isoformat(), "sent": sent}
