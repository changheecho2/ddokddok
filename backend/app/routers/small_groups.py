from fastapi import APIRouter, HTTPException, Response

from app.database import supabase
from app.models.small_group import SmallGroupAttendanceIn, SmallGroupAttendanceOut

router = APIRouter(prefix="/small-groups", tags=["small-groups"])


@router.post("/attendance", response_model=SmallGroupAttendanceOut, status_code=201)
def add_small_group_attendance(body: SmallGroupAttendanceIn):
    # member 존재 확인
    member_rows = supabase.table("members").select("id").eq("id", str(body.member_id)).execute().data
    if not member_rows:
        raise HTTPException(status_code=404, detail="Member not found")

    result = supabase.table("small_group_attendance").insert(
        {
            "member_id": str(body.member_id),
            "attended_date": body.attended_date.isoformat(),
            "note": body.note,
        }
    ).execute()

    return result.data[0]


@router.delete("/attendance/{attendance_id}", status_code=204)
def delete_small_group_attendance(attendance_id: str):
    rows = supabase.table("small_group_attendance").select("id").eq("id", attendance_id).execute().data
    if not rows:
        raise HTTPException(status_code=404, detail="Attendance record not found")

    supabase.table("small_group_attendance").delete().eq("id", attendance_id).execute()
    return Response(status_code=204)
