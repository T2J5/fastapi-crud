from sqlmodel import SQLModel, Field, Column, Relationship
from sqlalchemy.dialects import postgresql as pg
from typing import List
from typing import ClassVar, Optional
from datetime import date, datetime
from uuid import uuid4, UUID


class User(SQLModel, table=True):
    __tablename__ = "users"  # type: ignore  指定表名
    uid: UUID = Field(
        sa_column=Column(pg.UUID, nullable=False, primary_key=True, default=uuid4)
    )
    username: str
    email: str
    first_name: str
    last_name: str
    role: str = Field(
        sa_column=(Column(pg.VARCHAR, nullable=False, server_default="user"))
    )  # 添加角色字段，默认为 "user", server_default 现有用户默认角色为 "user"
    is_verified: bool = Field(default=False)
    password_hash: str = Field(exclude=True)  # 不在模型输出中显示密码哈希
    # 选择 IN 加载 - 通过 lazy='selectin' 或 selectinload() 选项可用，这种加载方式会发出第二个（或更多）SELECT语句，将父对象的键标识符组装到IN子句中，以便通过主键一次性加载相关集合/标量引用的所有成员。
    books: List["Book"] = Relationship(
        back_populates="user", sa_relationship_kwargs={"lazy": "selectin"}
    )  # 定义与 Book 的关系
    reviews: List["Review"] = Relationship(
        back_populates="user", sa_relationship_kwargs={"lazy": "selectin"}
    )  # 定义与 Review 的关系
    created_at: datetime = Field(
        sa_column=Column(pg.TIMESTAMP, nullable=False, default=datetime.now)
    )
    updated_at: datetime = Field(
        sa_column=Column(
            pg.TIMESTAMP, nullable=False, default=datetime.now, onupdate=datetime.now
        )
    )

    def __repr__(self):
        return f"<User {self.username}>"


class Book(SQLModel, table=True):
    __tablename__: ClassVar[str] = "books"  # type: ignore 指定表名为 "books"
    uid: UUID = Field(
        sa_column=Column(pg.UUID, primary_key=True, default=uuid4, nullable=False)
    )
    title: str
    author: str
    price: float
    published_date: date
    user_uid: Optional[UUID] = Field(
        default=None, foreign_key="users.uid"
    )  # 外键，允许为 null，表示未关联用户
    user: Optional["User"] = Relationship(
        back_populates="books"
    )  # 定义与 User 的关系，允许为 null
    reviews: List["Review"] = Relationship(
        back_populates="book", sa_relationship_kwargs={"lazy": "selectin"}
    )  # 定义与 Review 的关系，允许为 null, 这里的back_populates需要与 Review 中的 book 字段对应
    created_at: datetime = Field(sa_column=Column(pg.TIMESTAMP, default=datetime.now))
    updated_at: datetime = Field(sa_column=Column(pg.TIMESTAMP, default=datetime.now))

    def __repr__(self) -> str:
        return f"<Book {self.title}>"


class Review(SQLModel, table=True):
    __tablename__ = "reviews"  # type: ignore 指定表名为 "reviews"

    uid: UUID = Field(
        sa_column=Column(pg.UUID, primary_key=True, default=uuid4, nullable=False)
    )
    rating: int = Field(lt=5, ge=1)  # type: ignore 评分，必须在1到5之间
    content: str  # 评论内容
    user_uid: Optional[UUID] = Field(
        default=None, foreign_key="users.uid"
    )  # 外键，允许为 null，表示未关联用户
    book_uid: Optional[UUID] = Field(
        default=None, foreign_key="books.uid"
    )  # 外键，允许为 null，表示未关联书籍
    user: Optional[User] = Relationship(back_populates="reviews")
    book: Optional[Book] = Relationship(back_populates="reviews")

    created_at: datetime = Field(sa_column=Column(pg.TIMESTAMP, default=datetime.now))
    updated_at: datetime = Field(sa_column=Column(pg.TIMESTAMP, default=datetime.now))

    def __repr__(self) -> str:
        return f"<Review {self.rating} stars for book {self.book_uid} by user {self.user_uid}>"
