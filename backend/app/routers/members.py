from collections import defaultdict
from typing import List

from fastapi import APIRouter, HTTPException

from app.database import supabase
from app.models.member import (
    MemberDetail, JournalCheck, CommentCheck, MeetingAttendance,
    DepositHistoryItem, DepositAdjustIn, DepositAdjustOut,
    SmallGroupUpdateIn,
)

router = APIRouter(prefix="/members", tags=["members"])


def _build_member_detail(member: dict, meeting_attendances: list,
                         journal_checks: list, comment_checks: list,
                         deposit_history: list) -> MemberDetail:
    return MemberDetail(
        id=member["id"],
        name=member["name"],
        deposit_balance=member["deposit_balance"],
        small_group_satisfied=member.get("small_group_satisfied"),
        meeting_attendances=[
            MeetingAttendance(meeting_id=a["meeting_id"], is_attended=a["is_attended"])
            for a in meeting_attendances
        ],
        journal_checks=[
            JournalCheck(journal_id=jc["journal_id"], is_written=jc["is_written"])
            for jc in journal_checks
        ],
        comment_checks=[
            CommentCheck(journal_id=cc["journal_id"], is_satisfied=cc["is_satisfied"])
            for cc in comment_checks
        ],
        deposit_history=[
            DepositHistoryItem(
                id=dh["id"],
                reason=dh["reason"],
                amount=dh["amount"],
                applied_at=dh["applied_at"],
                memo=dh.get("memo"),
            )
            for dh in deposit_history
        ],
    )


@router.get("", response_model=List[MemberDetail])
def get_members():
    members = supabase.table("members").select("id, name, deposit_balance, small_group_satisfied").order("name").execute().data

    # 배치 쿼리 — N+1 방지
    attendances = supabase.table("meeting_attendance").select("member_id, meeting_id, is_attended").execute().data
    journal_checks = supabase.table("journal_checks").select("member_id, journal_id, is_written").execute().data
    comment_checks = supabase.table("comment_checks").select("member_id, journal_id, is_satisfied").execute().data
    deposit_history = supabase.table("deposit_history").select("id, member_id, reason, amount, applied_at, memo").order("applied_at").execute().data

    # member_id 기준으로 그룹핑
    att_map: dict = defaultdict(list)
    for a in attendances:
        att_map[a["member_id"]].append(a)

    jc_map: dict = defaultdict(list)
    for jc in journal_checks:
        jc_map[jc["member_id"]].append(jc)

    cc_map: dict = defaultdict(list)
    for cc in comment_checks:
        cc_map[cc["member_id"]].append(cc)

    dh_map: dict = defaultdict(list)
    for dh in deposit_history:
        dh_map[dh["member_id"]].append(dh)

    return [
        _build_member_detail(
            m,
            att_map[m["id"]],
            jc_map[m["id"]],
            cc_map[m["id"]],
            dh_map[m["id"]],
        )
        for m in members
    ]


@router.get("/{member_id}", response_model=MemberDetail)
def get_member(member_id: str):
    result = supabase.table("members").select("id, name, deposit_balance, small_group_satisfied").eq("id", member_id).execute()
    rows = result.data if result is not None else []
    if not rows:
        raise HTTPException(status_code=404, detail="Member not found")
    member = rows[0]

    attendances = supabase.table("meeting_attendance").select("meeting_id, is_attended").eq("member_id", member_id).execute().data
    journal_checks = supabase.table("journal_checks").select("journal_id, is_written").eq("member_id", member_id).execute().data
    comment_checks = supabase.table("comment_checks").select("journal_id, is_satisfied").eq("member_id", member_id).execute().data
    deposit_history = supabase.table("deposit_history").select("id, reason, amount, applied_at, memo").eq("member_id", member_id).order("applied_at").execute().data

    return _build_member_detail(member, attendances, journal_checks, comment_checks, deposit_history)


@router.patch("/{member_id}/small-group", response_model=MemberDetail)
def update_small_group(member_id: str, body: SmallGroupUpdateIn):
    result = supabase.table("members").select("id").eq("id", member_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Member not found")

    supabase.table("members").update({"small_group_satisfied": body.satisfied}).eq("id", member_id).execute()
    return get_member(member_id)


@router.post("/{member_id}/deposit", response_model=DepositAdjustOut, status_code=201)
def adjust_deposit(member_id: str, body: DepositAdjustIn):
    result = supabase.table("members").select("id, deposit_balance").eq("id", member_id).execute()
    rows = result.data if result is not None else []
    if not rows:
        raise HTTPException(status_code=404, detail="Member not found")

    current_balance = rows[0]["deposit_balance"]
    new_balance = current_balance + body.amount

    history_result = supabase.table("deposit_history").insert({
        "member_id": member_id,
        "reason": body.reason,
        "amount": body.amount,
        "memo": body.memo,
    }).execute()

    supabase.table("members").update({"deposit_balance": new_balance}).eq("id", member_id).execute()

    history_row = history_result.data[0]
    return DepositAdjustOut(
        deposit_balance=new_balance,
        history=DepositHistoryItem(
            id=history_row["id"],
            reason=history_row["reason"],
            amount=history_row["amount"],
            applied_at=history_row["applied_at"],
            memo=history_row.get("memo"),
        ),
    )
