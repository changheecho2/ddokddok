from typing import List, Optional
from datetime import date

from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel

from app.database import supabase
from app.models.meeting import Meeting, AttendanceIn, BulkAttendanceIn, AttendanceOut

router = APIRouter(prefix="/meetings", tags=["meetings"])


class MeetingUpdate(BaseModel):
    meeting_date: Optional[date] = None
    sequence: Optional[int] = None


@router.get("", response_model=List[Meeting])
def get_meetings():
    data = supabase.table("meetings").select("*").order("sequence").execute().data
    return data


@router.patch("/{meeting_id}", response_model=Meeting)
def update_meeting(meeting_id: str, body: MeetingUpdate):
    payload = body.model_dump(exclude_unset=True)
    if payload.get("meeting_date") is not None:
        payload["meeting_date"] = payload["meeting_date"].isoformat()

    if not payload:
        raise HTTPException(status_code=400, detail="변경할 값이 없습니다.")

    rows = supabase.table("meetings").select("id").eq("id", meeting_id).execute().data
    if not rows:
        raise HTTPException(status_code=404, detail="Meeting not found")

    result = supabase.table("meetings").update(payload).eq("id", meeting_id).execute()
    return result.data[0]


@router.post("/{meeting_id}/attendance", response_model=AttendanceOut, status_code=200)
def upsert_attendance(meeting_id: str, body: AttendanceIn):
    # meeting 존재 확인
    meeting_rows = supabase.table("meetings").select("id").eq("id", meeting_id).execute().data
    if not meeting_rows:
        raise HTTPException(status_code=404, detail="Meeting not found")

    result = supabase.table("meeting_attendance").upsert(
        {
            "member_id": str(body.member_id),
            "meeting_id": meeting_id,
            "is_attended": body.is_attended,
        },
        on_conflict="member_id,meeting_id",
    ).execute()

    return result.data[0]


@router.post("/{meeting_id}/attendance/bulk", status_code=200)
def upsert_attendance_bulk(meeting_id: str, body: BulkAttendanceIn):
    # meeting 존재 확인
    meeting_rows = supabase.table("meetings").select("id").eq("id", meeting_id).execute().data
    if not meeting_rows:
        raise HTTPException(status_code=404, detail="Meeting not found")

    rows = [
        {
            "member_id": str(a.member_id),
            "meeting_id": meeting_id,
            "is_attended": a.is_attended,
        }
        for a in body.attendances
    ]

    result = supabase.table("meeting_attendance").upsert(
        rows, on_conflict="member_id,meeting_id"
    ).execute()

    return {"upserted": len(result.data)}


@router.delete("/{meeting_id}/attendance/{member_id}", status_code=204)
def delete_attendance(meeting_id: str, member_id: str):
    supabase.table("meeting_attendance").delete()\
        .eq("meeting_id", meeting_id)\
        .eq("member_id", member_id)\
        .execute()
    return Response(status_code=204)
