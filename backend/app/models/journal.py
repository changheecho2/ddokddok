from pydantic import BaseModel
from uuid import UUID
from datetime import date


class Journal(BaseModel):
    id: UUID
    hashtag: str
    label: str
    check_date: date
    comment_check_date: date
