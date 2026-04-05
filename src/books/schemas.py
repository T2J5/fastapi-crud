import uuid
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, date
from src.reviews.schemas import ReviewModel


# book模型
class BookModel(BaseModel):
    uid: uuid.UUID
    title: str
    author: str
    price: float
    published_date: date
    created_at: datetime
    updated_at: datetime


class BookReviewModel(BookModel):
    reviews: Optional[List[ReviewModel]] = None  # 添加 reviews 字段，类型为可选的列表


# book更新模型
class BookUpdateModel(BaseModel):
    title: Optional[str] = None
    author: Optional[str] = None
    price: Optional[float] = None


# book创建模型
class BookCreateModel(BaseModel):
    title: str
    author: str
    price: float
    published_date: str
