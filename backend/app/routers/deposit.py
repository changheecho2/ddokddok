from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.database import supabase
from app.services.deposit_calculator import (
    MemberDeductionResult,
    calculate_all,
    calculate_one,
)

router = APIRouter(prefix="/deposit", tags=["deposit"])


# ── Response models ───────────────────────────────────────────────────────────

class DeductionBreakdown(BaseModel):
    meeting: int
    journal: int
    comment: int
    small_group: int


class CalculateResponse(BaseModel):
    member_id: str
    name: str
    current_balance: int
    deductions: DeductionBreakdown
    total_deduction: int
    expected_balance: int


class AppliedItem(BaseModel):
    reason: str
    amount: int  # 음수


class ApplyResponse(BaseModel):
    member_id: str
    name: str
    applied: List[AppliedItem]
    skipped: List[str]      # 이미 적용된 reason 목록
    deposit_balance: int


# ── 변환 헬퍼 ─────────────────────────────────────────────────────────────────

def _to_calculate_response(r: MemberDeductionResult) -> CalculateResponse:
    return CalculateResponse(
        member_id=r.member_id,
        name=r.name,
        current_balance=r.current_balance,
        deductions=DeductionBreakdown(
            meeting=r.meeting,
            journal=r.journal,
            comment=r.comment,
            small_group=r.small_group,
        ),
        total_deduction=r.total_deduction,
        expected_balance=r.expected_balance,
    )


def _apply_member(calc: MemberDeductionResult) -> ApplyResponse:
    """차감 계산 결과를 DB에 적용하고 결과를 반환한다."""
    if not calc.items:
        return ApplyResponse(
            member_id=calc.member_id,
            name=calc.name,
            applied=[],
            skipped=[],
            deposit_balance=calc.current_balance,
        )

    # 이미 적용된 reason 조회
    existing = (
        supabase.table("deposit_history")
        .select("reason")
        .eq("member_id", calc.member_id)
        .execute()
        .data
    )
    existing_reasons = {row["reason"] for row in existing}

    new_items = [item for item in calc.items if item.reason not in existing_reasons]
    skipped = [item.reason for item in calc.items if item.reason in existing_reasons]

    if new_items:
        # deposit_history 기록
        history_rows = [
            {
                "member_id": calc.member_id,
                "reason": item.reason,
                "amount": item.amount,
            }
            for item in new_items
        ]
        supabase.table("deposit_history").insert(history_rows).execute()

        # deposit_balance 업데이트
        total_new = sum(item.amount for item in new_items)
        new_balance = calc.current_balance + total_new
        supabase.table("members").update({"deposit_balance": new_balance}).eq(
            "id", calc.member_id
        ).execute()
    else:
        new_balance = calc.current_balance

    return ApplyResponse(
        member_id=calc.member_id,
        name=calc.name,
        applied=[AppliedItem(reason=i.reason, amount=i.amount) for i in new_items],
        skipped=skipped,
        deposit_balance=new_balance,
    )


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/calculate", response_model=List[CalculateResponse])
def calculate_all_members():
    results = calculate_all(supabase)
    return [_to_calculate_response(r) for r in results]


@router.get("/calculate/{member_id}", response_model=CalculateResponse)
def calculate_member(member_id: str):
    result = calculate_one(supabase, member_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Member not found")
    return _to_calculate_response(result)


@router.post("/apply", response_model=List[ApplyResponse])
def apply_all_members():
    results = calculate_all(supabase)
    return [_apply_member(r) for r in results]


@router.post("/apply/{member_id}", response_model=ApplyResponse)
def apply_member(member_id: str):
    result = calculate_one(supabase, member_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Member not found")
    return _apply_member(result)
