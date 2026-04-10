"""디스코드 웹훅을 통한 알림 서비스"""
import os
from datetime import date, datetime, timezone, timedelta
from typing import Dict, List, Optional, Tuple

import httpx

from app.database import supabase
from app.services.deposit_calculator import today_kst

DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL", "")
KST = timezone(timedelta(hours=9))


# ── 헬퍼 ────────────────────────────────────────────────────────────────────

def _load_members() -> Dict[str, str]:
    """멤버 {id: name} 맵 반환."""
    rows = supabase.table("members").select("id, name").execute().data
    return {m["id"]: m["name"] for m in rows}


def _journals_by_check_date(ref_date: date) -> list:
    """check_date == ref_date 인 일지 반환."""
    journals = supabase.table("journals").select("id, hashtag, check_date, comment_check_date").execute().data
    return [j for j in journals if j.get("check_date") == ref_date.isoformat()]


def _journals_by_comment_check_date(ref_date: date) -> list:
    """comment_check_date == ref_date 인 일지 반환."""
    journals = supabase.table("journals").select("id, hashtag, check_date, comment_check_date").execute().data
    return [j for j in journals if j.get("comment_check_date") == ref_date.isoformat()]


def _get_journal_status(journal_ids: List[str], member_map: Dict[str, str]) -> Tuple[List[str], List[str]]:
    """일지 작성 현황. (작성자 리스트, 미작성자 리스트) 반환."""
    jc_rows = supabase.table("journal_checks").select("member_id, journal_id, is_written").execute().data

    written = []
    not_written = []
    for jc in jc_rows:
        if jc["journal_id"] not in journal_ids:
            continue
        name = member_map.get(jc["member_id"], "알 수 없음")
        if jc["is_written"]:
            written.append(name)
        else:
            not_written.append(name)

    return sorted(set(written)), sorted(set(not_written))


def _get_comment_status(journal_ids: List[str], member_map: Dict[str, str]) -> Tuple[List[str], List[str]]:
    """댓글 현황. (충족자 리스트 [(name, count)], 미달자 리스트 [(name, count)]) 반환."""
    cc_rows = supabase.table("comment_checks").select("member_id, journal_id, is_satisfied, comment_count").execute().data

    satisfied = []
    not_satisfied = []
    for cc in cc_rows:
        if cc["journal_id"] not in journal_ids:
            continue
        name = member_map.get(cc["member_id"], "알 수 없음")
        count = cc.get("comment_count", 0)
        if cc.get("is_satisfied"):
            satisfied.append((name, count))
        else:
            not_satisfied.append((name, count))

    return sorted(set(satisfied)), sorted(set(not_satisfied))


# ── 메시지 생성 ──────────────────────────────────────────────────────────────

def build_journal_warning(ref_date: date) -> Optional[str]:
    """일지 마감 3시간 전 경고 메시지."""
    journals = _journals_by_check_date(ref_date)
    if not journals:
        return None

    member_map = _load_members()
    journal_ids = [j["id"] for j in journals]
    hashtags = [j["hashtag"] for j in journals]
    written, not_written = _get_journal_status(journal_ids, member_map)

    lines = [
        f"⏰ **[일지] 마감 3시간 전 알림**",
        f"📌 대상: {', '.join(hashtags)} (마감일: {ref_date})",
        "",
        f"✅ **작성 완료 ({len(written)}명):**",
    ]
    if written:
        lines.append(f"  {', '.join(written)}")
    else:
        lines.append("  없음")

    lines.append("")
    lines.append(f"❌ **미작성 ({len(not_written)}명):**")
    if not_written:
        lines.append(f"  {', '.join(not_written)}")
    else:
        lines.append("  없음 — 전원 작성 완료! 🎉")

    return "\n".join(lines)


def build_journal_result(ref_date: date) -> Optional[str]:
    """일지 마감 후 결과 메시지."""
    journals = _journals_by_check_date(ref_date)
    if not journals:
        return None

    member_map = _load_members()
    journal_ids = [j["id"] for j in journals]
    hashtags = [j["hashtag"] for j in journals]
    written, not_written = _get_journal_status(journal_ids, member_map)

    lines = [
        f"🚨 **[일지] 마감 완료**",
        f"📌 대상: {', '.join(hashtags)} (마감일: {ref_date})",
        "",
        f"✅ **작성 완료 ({len(written)}명):**",
    ]
    if written:
        lines.append(f"  {', '.join(written)}")
    else:
        lines.append("  없음")

    lines.append("")
    if not_written:
        lines.append(f"❌ **미작성 ({len(not_written)}명)** → 1건당 10,000원 차감:")
        lines.append(f"  {', '.join(not_written)}")
        lines.append("")
        lines.append(f"💰 예상 차감: {len(not_written) * 10_000:,}원")
    else:
        lines.append("✅ 전원 작성 완료! 차감 없음 🎉")

    return "\n".join(lines)


def build_comment_warning(ref_date: date) -> Optional[str]:
    """댓글 마감 3시간 전 경고 메시지."""
    journals = _journals_by_comment_check_date(ref_date)
    if not journals:
        return None

    member_map = _load_members()
    journal_ids = [j["id"] for j in journals]
    hashtags = [j["hashtag"] for j in journals]
    satisfied, not_satisfied = _get_comment_status(journal_ids, member_map)

    lines = [
        f"⏰ **[댓글] 마감 3시간 전 알림**",
        f"📌 대상: {', '.join(hashtags)} (마감일: {ref_date})",
        f"📊 기준: 15개 이상",
        "",
        f"✅ **충족 ({len(satisfied)}명):**",
    ]
    if satisfied:
        entries = [f"{name}({count}개)" for name, count in satisfied]
        lines.append(f"  {', '.join(entries)}")
    else:
        lines.append("  없음")

    lines.append("")
    lines.append(f"❌ **미달 ({len(not_satisfied)}명):**")
    if not_satisfied:
        entries = [f"{name}({count}개)" for name, count in not_satisfied]
        lines.append(f"  {', '.join(entries)}")
    else:
        lines.append("  없음 — 전원 충족! 🎉")

    return "\n".join(lines)


def build_comment_result(ref_date: date) -> Optional[str]:
    """댓글 마감 후 결과 메시지."""
    journals = _journals_by_comment_check_date(ref_date)
    if not journals:
        return None

    member_map = _load_members()
    journal_ids = [j["id"] for j in journals]
    hashtags = [j["hashtag"] for j in journals]
    satisfied, not_satisfied = _get_comment_status(journal_ids, member_map)

    lines = [
        f"🚨 **[댓글] 마감 완료**",
        f"📌 대상: {', '.join(hashtags)} (마감일: {ref_date})",
        f"📊 기준: 15개 이상",
        "",
        f"✅ **충족 ({len(satisfied)}명):**",
    ]
    if satisfied:
        entries = [f"{name}({count}개)" for name, count in satisfied]
        lines.append(f"  {', '.join(entries)}")
    else:
        lines.append("  없음")

    lines.append("")
    if not_satisfied:
        lines.append(f"❌ **미달 ({len(not_satisfied)}명)** → 1건당 10,000원 차감:")
        entries = [f"{name}({count}개)" for name, count in not_satisfied]
        lines.append(f"  {', '.join(entries)}")
        lines.append("")
        lines.append(f"💰 예상 차감: {len(not_satisfied) * 10_000:,}원")
    else:
        lines.append("✅ 전원 충족! 차감 없음 🎉")

    return "\n".join(lines)


# ── 전송 ─────────────────────────────────────────────────────────────────────

def send_discord_message(content: str, webhook_url: Optional[str] = None):
    """디스코드 웹훅으로 메시지 전송."""
    url = webhook_url or DISCORD_WEBHOOK_URL
    if not url:
        raise ValueError("DISCORD_WEBHOOK_URL이 설정되지 않았습니다.")

    resp = httpx.post(url, json={"content": content}, timeout=10.0)
    resp.raise_for_status()
    return resp.status_code
