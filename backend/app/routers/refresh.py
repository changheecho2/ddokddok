import os
from datetime import date, datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.database import supabase
from app.services.band_client import collect_journal_data
from app.services.deposit_calculator import calculate_all
from app.routers.deposit import _apply_member, ApplyResponse

router = APIRouter(prefix="/refresh", tags=["refresh"])

COOLDOWN_MINUTES = 60


# ── 상태 저장 헬퍼 ─────────────────────────────────────────────────────────────

def _get_last_refresh() -> Optional[datetime]:
    try:
        rows = (
            supabase.table("system_settings")
            .select("value")
            .eq("key", "last_refresh_at")
            .execute()
            .data
        )
        if rows:
            return datetime.fromisoformat(rows[0]["value"])
    except Exception:
        pass
    return None


def _set_last_refresh(dt: datetime):
    supabase.table("system_settings").upsert(
        {"key": "last_refresh_at", "value": dt.isoformat()},
        on_conflict="key",
    ).execute()


# ── Response models ───────────────────────────────────────────────────────────

class RefreshStatusResponse(BaseModel):
    last_refresh_at: Optional[str]
    next_available_at: Optional[str]
    is_cooling_down: bool


class RefreshResponse(BaseModel):
    synced_journals: List[str]
    skipped_journals: List[str]
    applied_deductions: List[ApplyResponse]


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/status", response_model=RefreshStatusResponse)
def get_refresh_status():
    last = _get_last_refresh()
    if last is None:
        return RefreshStatusResponse(
            last_refresh_at=None,
            next_available_at=None,
            is_cooling_down=False,
        )
    now = datetime.now(timezone.utc)
    # last가 timezone-naive면 UTC로 간주
    if last.tzinfo is None:
        last = last.replace(tzinfo=timezone.utc)
    next_available = last + timedelta(minutes=COOLDOWN_MINUTES)
    return RefreshStatusResponse(
        last_refresh_at=last.isoformat(),
        next_available_at=next_available.isoformat(),
        is_cooling_down=now < next_available,
    )


@router.post("", response_model=RefreshResponse)
async def full_refresh(force: bool = Query(default=False)):
    access_token = os.getenv("BAND_ACCESS_TOKEN", "")
    band_key = os.getenv("BAND_KEY", "")
    if not access_token or not band_key:
        raise HTTPException(status_code=500, detail="BAND_ACCESS_TOKEN or BAND_KEY is not set")

    now = datetime.now(timezone.utc)

    # 쿨타임 체크 (force=true면 무시)
    if not force:
        last = _get_last_refresh()
        if last is not None:
            if last.tzinfo is None:
                last = last.replace(tzinfo=timezone.utc)
            next_available = last + timedelta(minutes=COOLDOWN_MINUTES)
            if now < next_available:
                raise HTTPException(
                    status_code=429,
                    detail={
                        "error": "쿨타임 중",
                        "next_available_at": next_available.isoformat(),
                    },
                )

    today = date.today()

    # 1. 전체 멤버 deposit_balance 50,000 초기화
    members = supabase.table("members").select("id, name").execute().data
    for m in members:
        supabase.table("members").update({"deposit_balance": 50000}).eq("id", m["id"]).execute()

    # 2. deposit_history 전체 삭제
    supabase.table("deposit_history").delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()

    # 3. journals 분류 및 싱크
    journals = supabase.table("journals").select("id, hashtag, check_date").order("check_date").execute().data
    name_map: Dict[str, str] = {m["name"]: m["id"] for m in members}
    all_member_ids = set(name_map.values())

    synced_journals: List[str] = []
    skipped_journals: List[str] = []

    for journal in journals:
        raw_date = journal.get("check_date")
        if not raw_date or date.fromisoformat(raw_date) >= today:
            skipped_journals.append(journal["hashtag"])
            continue

        check_date = date.fromisoformat(raw_date)
        result = await collect_journal_data(access_token, band_key, journal["hashtag"], name_map, check_date)

        supabase.table("journal_checks").upsert(
            [{"member_id": mid, "journal_id": journal["id"], "is_written": mid in result["journal_writes"]} for mid in all_member_ids],
            on_conflict="member_id,journal_id",
        ).execute()

        supabase.table("comment_checks").upsert(
            [{"member_id": mid, "journal_id": journal["id"], "comment_count": result["comment_counts"].get(mid, 0)} for mid in all_member_ids],
            on_conflict="member_id,journal_id",
        ).execute()

        synced_journals.append(journal["hashtag"])

    # 4. 전체 차감 계산 및 적용
    calcs = calculate_all(supabase)
    applied = [_apply_member(c) for c in calcs]

    # 5. 마지막 실행 시간 저장
    _set_last_refresh(now)

    return RefreshResponse(
        synced_journals=synced_journals,
        skipped_journals=skipped_journals,
        applied_deductions=applied,
    )
