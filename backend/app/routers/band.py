import os
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.database import supabase
from app.services.band_client import collect_journal_data

router = APIRouter(prefix="/band", tags=["band"])


def _get_band_env() -> tuple[str, str]:
    access_token = os.getenv("BAND_ACCESS_TOKEN", "")
    band_key = os.getenv("BAND_KEY", "")
    if not access_token:
        raise HTTPException(status_code=500, detail="BAND_ACCESS_TOKEN is not set")
    if not band_key:
        raise HTTPException(status_code=500, detail="BAND_KEY is not set")
    return access_token, band_key


# ── Response models ──────────────────────────────────────────────────────────

class SyncResponse(BaseModel):
    journal_id: str
    hashtag: str
    synced_posts: int
    synced_comments: int
    unmatched_members: List[str]


class MemberStatus(BaseModel):
    member_id: str
    name: str


class MemberCommentStatus(BaseModel):
    member_id: str
    name: str
    comment_count: int


class SyncResultResponse(BaseModel):
    journal_id: str
    hashtag: str
    label: str
    written: List[MemberStatus]
    unwritten: List[MemberStatus]
    comment_satisfied: List[MemberCommentStatus]
    comment_unsatisfied: List[MemberCommentStatus]


# ── Endpoints ────────────────────────────────────────────────────────────────


@router.post("/sync/{journal_id}", response_model=SyncResponse)
async def sync_journal(journal_id: str):
    access_token, band_key = _get_band_env()

    # 1. journal 조회
    journal_rows = supabase.table("journals").select("id, hashtag, check_date").eq("id", journal_id).execute().data
    if not journal_rows:
        raise HTTPException(status_code=404, detail="Journal not found")
    hashtag: str = journal_rows[0]["hashtag"]

    from datetime import date as _date
    raw_date = journal_rows[0].get("check_date")
    check_date = _date.fromisoformat(raw_date) if raw_date else None

    # 2. 전체 멤버 name→id 맵
    members = supabase.table("members").select("id, name").execute().data
    name_map: Dict[str, str] = {m["name"]: m["id"] for m in members}

    # 3. 밴드 데이터 수집 (check_date 이하 포스트만)
    result = await collect_journal_data(access_token, band_key, hashtag, name_map, check_date)

    all_member_ids = set(name_map.values())

    # 4. journal_checks upsert — 전체 멤버 대상 (작성: True, 미작성: False)
    journal_check_rows = [
        {
            "member_id": mid,
            "journal_id": journal_id,
            "is_written": mid in result["journal_writes"],
        }
        for mid in all_member_ids
    ]
    supabase.table("journal_checks").upsert(
        journal_check_rows, on_conflict="member_id,journal_id"
    ).execute()

    # 5. comment_checks upsert — 전체 멤버 대상 (댓글 없으면 0)
    comment_check_rows = [
        {
            "member_id": mid,
            "journal_id": journal_id,
            "comment_count": result["comment_counts"].get(mid, 0),
        }
        for mid in all_member_ids
    ]
    supabase.table("comment_checks").upsert(
        comment_check_rows, on_conflict="member_id,journal_id"
    ).execute()

    return SyncResponse(
        journal_id=journal_id,
        hashtag=hashtag,
        synced_posts=result["synced_posts"],
        synced_comments=result["total_comments"],
        unmatched_members=result["unmatched"],
    )


@router.get("/sync/{journal_id}/result", response_model=SyncResultResponse)
def get_sync_result(journal_id: str):
    # journal 조회
    journal_rows = supabase.table("journals").select("id, hashtag, label").eq("id", journal_id).execute().data
    if not journal_rows:
        raise HTTPException(status_code=404, detail="Journal not found")
    journal = journal_rows[0]

    # 전체 멤버
    members = supabase.table("members").select("id, name").order("name").execute().data
    member_map: Dict[str, str] = {m["id"]: m["name"] for m in members}
    all_ids = set(member_map.keys())

    # journal_checks
    jc_rows = supabase.table("journal_checks").select("member_id, is_written").eq("journal_id", journal_id).execute().data
    written_ids = {row["member_id"] for row in jc_rows if row["is_written"]}

    # comment_checks
    cc_rows = supabase.table("comment_checks").select("member_id, comment_count, is_satisfied").eq("journal_id", journal_id).execute().data
    comment_map: Dict[str, int] = {row["member_id"]: row["comment_count"] for row in cc_rows}

    written = [MemberStatus(member_id=mid, name=member_map[mid]) for mid in written_ids if mid in member_map]
    unwritten = [MemberStatus(member_id=mid, name=member_map[mid]) for mid in all_ids if mid not in written_ids]

    comment_satisfied = [
        MemberCommentStatus(member_id=mid, name=member_map[mid], comment_count=cnt)
        for mid, cnt in comment_map.items()
        if cnt >= 15 and mid in member_map
    ]
    comment_unsatisfied = [
        MemberCommentStatus(member_id=mid, name=member_map[mid], comment_count=comment_map.get(mid, 0))
        for mid in all_ids
        if comment_map.get(mid, 0) < 15
    ]

    # 정렬
    written.sort(key=lambda x: x.name)
    unwritten.sort(key=lambda x: x.name)
    comment_satisfied.sort(key=lambda x: x.name)
    comment_unsatisfied.sort(key=lambda x: x.name)

    return SyncResultResponse(
        journal_id=journal_id,
        hashtag=journal["hashtag"],
        label=journal["label"],
        written=written,
        unwritten=unwritten,
        comment_satisfied=comment_satisfied,
        comment_unsatisfied=comment_unsatisfied,
    )
