from pydantic import BaseModel, Field
from uuid import UUID
from typing import Optional
from datetime import datetime


class ReviewModel(BaseModel):
    uid: UUID
    rating: int = Field(..., gt=0, lt=6, description="Rating must be between 1 and 5")
    content: str = Field(..., description="Content of the review")
    user_uid: Optional[UUID]
    book_uid: Optional[UUID]
    created_at: datetime
    updated_at: datetime


class ReviewCreateModel(BaseModel):
    rating: int = Field(..., gt=0, lt=6, description="Rating must be between 1 and 5")
    content: str = Field(..., description="Content of the review")
