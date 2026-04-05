from fastapi import APIRouter, Depends, status
from fastapi.exceptions import HTTPException
from src.db.main import get_session
from src.books.service import BookService
from sqlmodel.ext.asyncio.session import AsyncSession
from src.books.schemas import (
    BookCreateModel,
    BookReviewModel,
    BookUpdateModel,
    BookModel,
)
from typing import List
from src.auth.dependencies import AccessTokenBearer, RoleChecker
from src.errors import (
    BookNotFound,
)

from rich import traceback, pretty

traceback.install()
pretty.install()

book_router = APIRouter()
book_service = BookService()
access_token_bearer = AccessTokenBearer()
role_checker = Depends(RoleChecker(allowed_roles=["admin", "user"]))


# 获取所有书籍
@book_router.get(
    "/",
    status_code=status.HTTP_200_OK,
    response_model=List[BookModel],
    dependencies=[role_checker],
)
async def get_all_books(
    session: AsyncSession = Depends(get_session),
    token_details: dict = Depends(access_token_bearer),
):
    """获取所有书籍"""
    books = await book_service.get_all_books(session=session)
    return books


# 根据id获取书籍
@book_router.get(
    "/{book_uid}",
    status_code=status.HTTP_200_OK,
    response_model=BookReviewModel,
    dependencies=[role_checker],
)
async def get_book_by_id(
    book_uid: str,
    session: AsyncSession = Depends(get_session),
    token_details: dict = Depends(access_token_bearer),
):
    """根据id获取书籍"""
    book = await book_service.get_book(book_uid, session)

    if book:
        return book
    raise BookNotFound()


# 根据user_id获取书籍
@book_router.get(
    "/user/{user_uid}",
    status_code=status.HTTP_200_OK,
    response_model=List[BookModel],
    dependencies=[role_checker],
)
async def get_books_by_user_id(
    user_uid: str, session: AsyncSession = Depends(get_session)
):
    """根据user_id获取书籍"""
    all_books = await book_service.get_all_books_by_user(user_uid, session)
    return all_books


# 创建一本书
@book_router.post(
    "/create_new_book",
    status_code=status.HTTP_201_CREATED,
    dependencies=[role_checker],
)
async def create_new_book(
    book_data: BookCreateModel,
    session: AsyncSession = Depends(get_session),
    token_details: dict = Depends(access_token_bearer),
):
    """创建一本书"""
    user_uid: str = token_details["user"]["user_uid"]
    new_book = await book_service.create_book(book_data, user_uid, session)
    return new_book


# 更新一本书
@book_router.put(
    "/update_book/{book_uid}",
    response_model=BookModel,
    status_code=status.HTTP_200_OK,
    dependencies=[role_checker],
)
async def update_book(
    book_uid: str,
    book_data: BookUpdateModel,
    session: AsyncSession = Depends(get_session),
    token_details: dict = Depends(access_token_bearer),
):
    book = await book_service.update_book(book_uid, book_data, session)
    if book:
        return book
    raise BookNotFound()


# 删除一本书
@book_router.delete(
    "/delete_book/{book_uid}",
    status_code=status.HTTP_200_OK,
    dependencies=[role_checker],
)
async def delete_book(
    book_uid: str,
    session: AsyncSession = Depends(get_session),
    token_details: dict = Depends(access_token_bearer),
):
    """删除一本书"""
    result = await book_service.delete_book(book_uid, session)
    if not result:
        raise BookNotFound()
    return None
