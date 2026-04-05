from typing import List
from pydantic import BaseModel, Field
import uuid
from datetime import datetime

from src.books.schemas import BookModel
from src.reviews.schemas import ReviewModel


class UserCreateModel(BaseModel):
    """用户创建模型"""

    username: str = Field(max_length=8)
    email: str = Field(max_length=40)
    password: str = Field(min_length=4)
    first_name: str = Field(max_length=20)
    last_name: str = Field(max_length=20)


class UserModel(BaseModel):
    """用户模型"""

    uid: uuid.UUID
    username: str
    email: str
    first_name: str
    last_name: str
    is_verified: bool
    password_hash: str = Field(exclude=True)  # 不在模型输出中显示密码哈希
    created_at: datetime
    updated_at: datetime


class UserBooksModel(UserModel):
    """用户模型，包含书籍信息"""

    books: List[BookModel] = Field(
        default_factory=list
    )  # 添加 books 字段，默认值为一个空列表
    reviews: List[ReviewModel] = Field(
        default_factory=list
    )  # 添加 reviews 字段，默认值为一个空列表


class UserLoginModel(BaseModel):
    """用户登录模型"""

    email: str = Field(max_length=40)
    password: str = Field(min_length=4)


class EmailModel(BaseModel):
    """邮件模型"""

    addresses: List[str]


class PasswordResetModel(BaseModel):
    """密码重置模型"""

    email: str


class PasswordResetConfirmModel(BaseModel):
    """密码重置确认模型"""

    new_password: str
    confirm_new_password: str
