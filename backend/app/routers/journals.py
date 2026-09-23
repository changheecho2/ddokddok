from typing import List, Optional
from datetime import date

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.database import supabase
from app.models.journal import Journal

router = APIRouter(prefix="/journals", tags=["journals"])


class JournalUpdate(BaseModel):
    hashtag: Optional[str] = None
    label: Optional[str] = None
    check_date: Optional[date] = None
    comment_check_date: Optional[date] = None


@router.get("", response_model=List[Journal])
def get_journals():
    data = supabase.table("journals").select("*").order("check_date").execute().data
    return data


@router.patch("/{journal_id}", response_model=Journal)
def update_journal(journal_id: str, body: JournalUpdate):
    payload = body.model_dump(exclude_unset=True)
    # date 객체는 supabase 전송을 위해 ISO 문자열로 변환
    for key in ("check_date", "comment_check_date"):
        if payload.get(key) is not None:
            payload[key] = payload[key].isoformat()

    if not payload:
        raise HTTPException(status_code=400, detail="변경할 값이 없습니다.")

    rows = supabase.table("journals").select("id").eq("id", journal_id).execute().data
    if not rows:
        raise HTTPException(status_code=404, detail="Journal not found")

    result = supabase.table("journals").update(payload).eq("id", journal_id).execute()
    return result.data[0]
