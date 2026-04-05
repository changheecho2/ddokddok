"""디파짓 차감 계산 로직"""
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date
from typing import Dict, List

# ── 차감 규칙 상수 ────────────────────────────────────────────────────────────

# 정기모임 불참 횟수별 차감액 (1회 이하 = 0, 4회 이상은 4회와 동일)
MEETING_DEDUCTION_TABLE: Dict[int, int] = {
    0: 0,
    1: 0,
    2: 10_000,
    3: 30_000,
    4: 50_000,
}

JOURNAL_DEDUCTION_PER = 10_000      # 일지 미작성 건당
COMMENT_DEDUCTION_PER = 10_000      # 댓글 미달 건당
SMALL_GROUP_DEDUCTION = 50_000      # 조모임 미충족 차감액


# ── 데이터 클래스 ─────────────────────────────────────────────────────────────

@dataclass
class DeductionItem:
    """실제 deposit_history에 기록될 개별 차감 항목"""
    reason: str
    amount: int  # 음수 (차감), 예: -10000


@dataclass
class MemberDeductionResult:
    member_id: str
    name: str
    current_balance: int

    # 항목별 차감 합계 (양수)
    meeting: int = 0
    journal: int = 0
    comment: int = 0
    small_group: int = 0

    # apply용 개별 항목 목록
    items: List[DeductionItem] = field(default_factory=list)

    @property
    def total_deduction(self) -> int:
        return self.meeting + self.journal + self.comment + self.small_group

    @property
    def expected_balance(self) -> int:
        return self.current_balance - self.total_deduction


# ── 단일 멤버 계산 ────────────────────────────────────────────────────────────

def calculate_for_member(
    member_id: str,
    name: str,
    current_balance: int,
    absent_count: int,
    unwritten_hashtags: List[str],    # 미작성 일지 hashtag 목록
    unsatisfied_hashtags: List[str],  # 댓글 미달 일지 hashtag 목록
    small_group_satisfied,            # True=충족, False=미충족, None=미입력
) -> MemberDeductionResult:
    result = MemberDeductionResult(
        member_id=member_id,
        name=name,
        current_balance=current_balance,
    )

    # 1. 정기모임 차감
    meeting_amount = MEETING_DEDUCTION_TABLE.get(
        min(absent_count, 4), MEETING_DEDUCTION_TABLE[4]
    )
    if meeting_amount > 0:
        result.meeting = meeting_amount
        result.items.append(
            DeductionItem(
                reason=f"정기모임 {absent_count}회 불참",
                amount=-meeting_amount,
            )
        )

    # 2. 일지 미작성 차감
    for hashtag in unwritten_hashtags:
        result.journal += JOURNAL_DEDUCTION_PER
        result.items.append(
            DeductionItem(
                reason=f"일지 미작성 ({hashtag})",
                amount=-JOURNAL_DEDUCTION_PER,
            )
        )

    # 3. 댓글 미달 차감
    for hashtag in unsatisfied_hashtags:
        result.comment += COMMENT_DEDUCTION_PER
        result.items.append(
            DeductionItem(
                reason=f"댓글 미달 ({hashtag})",
                amount=-COMMENT_DEDUCTION_PER,
            )
        )

    # 4. 조모임 미충족 차감 (False일 때만, None=미입력은 차감 없음)
    if small_group_satisfied is False:
        result.small_group = SMALL_GROUP_DEDUCTION
        result.items.append(
            DeductionItem(
                reason="조모임 미충족",
                amount=-SMALL_GROUP_DEDUCTION,
            )
        )

    return result


# ── 배치 데이터 로드 + 전체 계산 ──────────────────────────────────────────────

def calculate_all(supabase) -> List[MemberDeductionResult]:
    """전체 멤버에 대해 차감액을 계산한다 (배치 쿼리, N+1 없음)"""
    members = (
        supabase.table("members")
        .select("id, name, deposit_balance, small_group_satisfied")
        .order("name")
        .execute()
        .data
    )
    journals = supabase.table("journals").select("id, hashtag, check_date, comment_check_date").execute().data
    today = date.today()
    # 마감일이 지난 journal만 차감 대상
    journal_map: Dict[str, str] = {j["id"]: j["hashtag"] for j in journals}
    journal_check_due: Dict[str, bool] = {
        j["id"]: (date.fromisoformat(j["check_date"]) < today) for j in journals if j.get("check_date")
    }
    comment_check_due: Dict[str, bool] = {
        j["id"]: (date.fromisoformat(j["comment_check_date"]) < today) for j in journals if j.get("comment_check_date")
    }

    all_attendance = (
        supabase.table("meeting_attendance")
        .select("member_id, is_attended")
        .execute()
        .data
    )
    all_jc = (
        supabase.table("journal_checks")
        .select("member_id, journal_id, is_written")
        .execute()
        .data
    )
    all_cc = (
        supabase.table("comment_checks")
        .select("member_id, journal_id, is_satisfied")
        .execute()
        .data
    )

    # 멤버별 집계
    absent_map: Dict[str, int] = defaultdict(int)
    for a in all_attendance:
        if not a["is_attended"]:
            absent_map[a["member_id"]] += 1

    unwritten_map: Dict[str, List[str]] = defaultdict(list)
    for jc in all_jc:
        # 마감일이 지난 일지만 차감
        if not jc["is_written"] and journal_check_due.get(jc["journal_id"], False):
            hashtag = journal_map.get(jc["journal_id"], jc["journal_id"])
            unwritten_map[jc["member_id"]].append(hashtag)

    unsatisfied_map: Dict[str, List[str]] = defaultdict(list)
    for cc in all_cc:
        # 마감일이 지난 댓글만 차감
        if not cc["is_satisfied"] and comment_check_due.get(cc["journal_id"], False):
            hashtag = journal_map.get(cc["journal_id"], cc["journal_id"])
            unsatisfied_map[cc["member_id"]].append(hashtag)

    return [
        calculate_for_member(
            member_id=m["id"],
            name=m["name"],
            current_balance=m["deposit_balance"],
            absent_count=absent_map[m["id"]],
            unwritten_hashtags=unwritten_map[m["id"]],
            unsatisfied_hashtags=unsatisfied_map[m["id"]],
            small_group_satisfied=m.get("small_group_satisfied"),
        )
        for m in members
    ]


def calculate_one(supabase, member_id: str) -> MemberDeductionResult:
    """특정 멤버 차감액 계산"""
    result_rows = (
        supabase.table("members")
        .select("id, name, deposit_balance, small_group_satisfied")
        .eq("id", member_id)
        .execute()
    )
    rows = result_rows.data if result_rows else []
    if not rows:
        return None

    m = rows[0]
    journals = supabase.table("journals").select("id, hashtag, check_date, comment_check_date").execute().data
    today = date.today()
    journal_map = {j["id"]: j["hashtag"] for j in journals}
    journal_check_due = {j["id"]: (date.fromisoformat(j["check_date"]) < today) for j in journals if j.get("check_date")}
    comment_check_due = {j["id"]: (date.fromisoformat(j["comment_check_date"]) < today) for j in journals if j.get("comment_check_date")}

    attendances = (
        supabase.table("meeting_attendance")
        .select("is_attended")
        .eq("member_id", member_id)
        .execute()
        .data
    )
    absent_count = sum(1 for a in attendances if not a["is_attended"])

    jc_rows = (
        supabase.table("journal_checks")
        .select("journal_id, is_written")
        .eq("member_id", member_id)
        .execute()
        .data
    )
    unwritten = [
        journal_map.get(jc["journal_id"], jc["journal_id"])
        for jc in jc_rows
        if not jc["is_written"] and journal_check_due.get(jc["journal_id"], False)
    ]

    cc_rows = (
        supabase.table("comment_checks")
        .select("journal_id, is_satisfied")
        .eq("member_id", member_id)
        .execute()
        .data
    )
    unsatisfied = [
        journal_map.get(cc["journal_id"], cc["journal_id"])
        for cc in cc_rows
        if not cc["is_satisfied"] and comment_check_due.get(cc["journal_id"], False)
    ]

    return calculate_for_member(
        member_id=m["id"],
        name=m["name"],
        current_balance=m["deposit_balance"],
        absent_count=absent_count,
        unwritten_hashtags=unwritten,
        unsatisfied_hashtags=unsatisfied,
        small_group_satisfied=m.get("small_group_satisfied"),
    )
