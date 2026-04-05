from typing import List

from fastapi import APIRouter

from app.database import supabase
from app.models.journal import Journal

router = APIRouter(prefix="/journals", tags=["journals"])


@router.get("", response_model=List[Journal])
def get_journals():
    data = supabase.table("journals").select("*").order("check_date").execute().data
    return data
