from fastapi import APIRouter, Depends
from sqlmodel.ext.asyncio.session import AsyncSession
from typing import List
from src.auth.dependencies import get_current_user
from src.db.models import User
from .schemas import ReviewCreateModel
from .service import ReviewService
from src.db.main import get_session

reviews_router = APIRouter()
review_service = ReviewService()


@reviews_router.post("/book/{book_uid}")
async def create_review(
    book_uid: str,
    review_data: ReviewCreateModel,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    new_review = await review_service.create_review_to_book(
        user_email=current_user.email,
        book_uid=book_uid,
        review_data=review_data,
        session=session,
    )

    return new_review
