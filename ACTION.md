# FastAPI 学习项目复盘

## 1. 项目总览

这是一个基于 FastAPI、SQLModel、PostgreSQL、Redis 和 Celery 的 CRUD 项目。目标是实现用户注册、登录、角色权限、书籍管理、邮件发送和异步任务处理。

项目核心点：

- 使用 FastAPI 作为 Web 框架
- 使用 SQLModel 作为 ORM，并结合 PostgreSQL
- 使用 JWT 进行认证授权
- 使用 Redis 保存 token 黑名单、作为 Celery 的 broker 与 backend
- 使用 FastAPI-Mail 发送邮件
- 使用 Celery 作为异步任务队列

## 1.1 技术选型与架构

本项目的选型可以从三个角度理解：

- SQLModel：它既是 SQLAlchemy ORM 的封装，又兼具 Pydantic 的数据验证能力。在同一个模型里，既可以声明数据库字段，也可以直接用于 FastAPI 的请求和响应。当前项目采用 SQLModel，是为了方便模型与接口之间的映射，减少重复定义。但仍然要注意：数据库模型和输入/输出 schema 应该分开定义，避免敏感字段（比如 `password_hash`）直接暴露。

- Alembic：用于数据库版本管理。项目中的 `migrations/` 目录和 `alembic.ini` 负责跟踪数据库结构变化。当模型变更时，使用 `alembic revision --autogenerate` 生成迁移脚本，然后执行 `alembic upgrade head`。这是一种生产级数据库 schema 演进方式，避免直接用 `create_all` 导致数据丢失。

- Celery vs BackgroundTasks：
  - `BackgroundTasks` 适合简单、轻量级的请求上下文内异步任务，例如发送邮件、写日志、异步通知等，它依赖于当前应用进程，不能跨进程调度。
  - `Celery` 适合需要独立 worker、任务重试、持久化、可监控的场景。当前项目使用 Celery 处理邮件任务，这样即使主 API 进程重启，任务仍然可以由 Redis broker 和 worker 继续执行。

此外，本项目通过 JWT + Redis 黑名单实现 token 管理，增加了注销和令牌撤销能力。这种设计比单纯的 JWT 无状态方案更安全，但也需要额外的 Redis 依赖。

## 1.2 当前项目模块结构

当前项目的顶层结构如下：

- `src/config.py`：配置加载与环境变量管理。
- `src/db/main.py`：数据库引擎、会话和初始化逻辑。
- `src/db/models.py`：SQLModel ORM 实体，包括 `User`、`Book`、`Review`。
- `src/db/redis.py`：Redis 黑名单与 token 撤销逻辑。
- `src/auth/`：认证模块，包括路由、依赖、服务、工具函数、schemas。
- `src/books/`：书籍资源相关的 service 和路由。
- `src/reviews/`：评论资源的 schema、service、路由（项目已有但文档未充分覆盖）。
- `src/mail.py`：邮件发送配置与消息构建。
- `src/celery_tasks.py`：Celery task 以及邮件异步执行入口。
- `src/middleware.py`：日志、中间件和 CORS 配置。
- `src/errors.py`：统一异常定义与处理。
- `main.py` / `app.py`：应用启动入口（当前文档仍需补充对这部分启动流程的说明）。

## 2. 环境与配置

### 2.1 环境变量

推荐在项目根目录创建 `.env` 文件：

```env
DATABASE_URL=postgresql+asyncpg://wangtao:wangtao@localhost:5432/bookly_db
REDIS_URL=redis://localhost:6379/0
MAIL_USERNAME=...
MAIL_PASSWORD=...
MAIL_FROM=...
MAIL_SERVER=...
MAIL_PORT=587
MAIL_FROM_NAME=...
JWT_SECRET=...
JWT_ALGORITHM=HS256
```

### 2.2 配置类

建议使用 `pydantic_settings`：

```python
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    DATABASE_URL: str
    REDIS_URL: str
    MAIL_USERNAME: str
    MAIL_PASSWORD: str
    MAIL_FROM: str
    MAIL_SERVER: str
    MAIL_PORT: int
    MAIL_FROM_NAME: str
    JWT_SECRET: str
    JWT_ALGORITHM: str = "HS256"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

Config = Settings()
```

## 3. 数据库与迁移

### 3.1 SQLModel 模型与 Schema

`books/schemas.py` 通过 Pydantic 验证请求参数和响应数据：

```python
from datetime import date, datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel

class BookModel(BaseModel):
    uid: UUID
    title: str
    author: str
    price: float
    published_date: date
    created_at: datetime
    updated_at: datetime

class BookUpdateModel(BaseModel):
    title: Optional[str] = None
    author: Optional[str] = None
    price: Optional[float] = None

class BookCreateModel(BaseModel):
    title: str
    author: str
    price: float
    published_date: str
```

`books/models.py` 定义 ORM 表结构：

```python
from typing import ClassVar
from datetime import date, datetime
from uuid import UUID, uuid4
import sqlalchemy.dialects.postgresql as pg
from sqlmodel import SQLModel, Field, Column

class Book(SQLModel, table=True):
    __tablename__: ClassVar[str] = "books"
    uid: UUID = Field(
        sa_column=Column(pg.UUID(as_uuid=True), primary_key=True, default=uuid4, nullable=False)
    )
    title: str
    author: str
    price: float
    published_date: date
    created_at: datetime = Field(sa_column=Column(pg.TIMESTAMP, default=datetime.now))
    updated_at: datetime = Field(sa_column=Column(pg.TIMESTAMP, default=datetime.now))

    def __repr__(self) -> str:
        return f"<Book {self.title}>"
```

在当前项目中，SQLModel 的使用不仅限于 `Book`：

- `src/db/models.py` 中还定义了 `User` 和 `Review`，它们使用 `Field(sa_column=Column(...))` 绑定 PostgreSQL 类型，如 `pg.UUID`、`pg.VARCHAR`、`pg.TIMESTAMP`。
- `Relationship` 用于建立实体间关系，例如 `User.books`、`Book.user`、`Review.user`、`Review.book`。当前项目通过 `sa_relationship_kwargs={"lazy": "selectin"}` 让关联加载更高效。
- 原则上，数据库模型和 API schema 需要分离：
  - `src/auth/schemas.py` 中定义 `UserCreateModel`、`UserModel`、`UserBooksModel`、`UserLoginModel` 等。
  - `UserModel` 中的 `password_hash = Field(exclude=True)` 是为了防止该字段出现在接口输出中。
- SQLModel 的好处在于：ORM 模型和 Pydantic 模型可以共享字段定义，同时仍然支持单独定义请求和响应的 schema。

这一部分补全了为什么选用 SQLModel、怎么在当前项目中实际使用以及为什么在文档里要区分数据库模型和 API schema。

### 3.2 数据库会话和异步引擎

当前文档中使用了 `AsyncEngine(create_engine(...))`，推荐直接使用 `create_async_engine`：

```python
from sqlmodel import SQLModel
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from typing import AsyncGenerator
from src.config import Config

async_engine = create_async_engine(Config.DATABASE_URL, echo=True)

async def init_db() -> None:
    async with async_engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

async def get_session() -> AsyncGenerator[AsyncSession, None]:
    SessionLocal = sessionmaker(
        bind=async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    async with SessionLocal() as session:
        yield session
```

### 3.3 数据迁移

使用 Alembic 进行迁移：

```bash
alembic init -t async migrations
```

在 `migrations/env.py` 中配置：

```python
config.set_main_option("sqlalchemy.url", Config.DATABASE_URL)
```

并在 `script.py.mako` 中导入 `sqlmodel`。

生成迁移并执行：

```bash
alembic revision --autogenerate -m "add review table"
alembic upgrade head
```

## 4. 业务层划分

### 4.1 Books Service

`books/service.py` 负责数据访问和业务逻辑：

```python
from datetime import datetime
from sqlmodel import select, desc
from sqlmodel.ext.asyncio.session import AsyncSession
from .schemas import BookCreateModel, BookUpdateModel
from .models import Book

class BookService:
    async def get_all_books(self, session: AsyncSession):
        statement = select(Book).order_by(desc(Book.created_at))
        result = await session.exec(statement)
        return result.all()

    async def get_book(self, book_uid: str, session: AsyncSession):
        statement = select(Book).where(Book.uid == book_uid)
        result = await session.exec(statement)
        return result.first()

    async def create_book(self, book_data: BookCreateModel, session: AsyncSession) -> Book:
        data = book_data.model_dump()
        data["published_date"] = datetime.strptime(data["published_date"], "%Y-%m-%d").date()
        new_book = Book(**data)
        session.add(new_book)
        await session.commit()
        await session.refresh(new_book)
        return new_book

    async def update_book(self, book_uid: str, update_data: BookUpdateModel, session: AsyncSession):
        book = await self.get_book(book_uid, session)
        if not book:
            return None
        for k, v in update_data.model_dump().items():
            if v is not None:
                setattr(book, k, v)
        await session.commit()
        await session.refresh(book)
        return book

    async def delete_book(self, book_uid: str, session: AsyncSession):
        book = await self.get_book(book_uid, session)
        if not book:
            return False
        await session.delete(book)
        await session.commit()
        return True
```

### 4.2 Books Router

`books/routes.py` 是接口层：

```python
from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from src.db.main import get_session
from src.books.service import BookService
from sqlmodel.ext.asyncio.session import AsyncSession
from src.books.schemas import BookCreateModel, BookUpdateModel, BookModel

book_router = APIRouter()
book_service = BookService()

@book_router.get("/", response_model=List[BookModel], status_code=status.HTTP_200_OK)
async def get_all_books(session: AsyncSession = Depends(get_session)):
    """获取所有书籍"""
    return await book_service.get_all_books(session=session)

@book_router.get("/{book_uid}", response_model=BookModel, status_code=status.HTTP_200_OK)
async def get_book_by_id(book_uid: str, session: AsyncSession = Depends(get_session)):
    """根据id获取书籍"""
    book = await book_service.get_book(book_uid, session)
    if not book:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="书籍不存在")
    return book

@book_router.post("/", status_code=status.HTTP_201_CREATED, response_model=BookModel)
async def create_new_book(book_data: BookCreateModel, session: AsyncSession = Depends(get_session)):
    """创建一本书"""
    return await book_service.create_book(book_data, session)

@book_router.put("/{book_uid}", response_model=BookModel, status_code=status.HTTP_200_OK)
async def update_book(book_uid: str, book_data: BookUpdateModel, session: AsyncSession = Depends(get_session)):
    """更新一本书"""
    book = await book_service.update_book(book_uid, book_data, session)
    if not book:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="书籍不存在")
    return book

@book_router.delete("/{book_uid}", status_code=status.HTTP_200_OK)
async def delete_book(book_uid: str, session: AsyncSession = Depends(get_session)):
    """删除一本书"""
    if not await book_service.delete_book(book_uid, session):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="书籍不存在")
    return {"message": "删除成功"}
```

### 4.3 认证与授权

#### 4.3.1 密码管理

使用 `passlib` 进行密码哈希和验证：

```python
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def create_hashed_password(plain_password: str) -> str:
    return pwd_context.hash(plain_password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)
```

创建用户时，不要保存明文密码：

```python
new_user.password_hash = create_hashed_password(user_data_dict["password"])
new_user.role = "user"
```

#### 4.3.2 JWT Token

使用 `pyjwt` 生成、验证 token：

```python
import jwt
from datetime import datetime, timedelta
import uuid
from src.config import Config

ACCESS_TOKEN_EXPIRE_SECONDS = 60
REFRESH_TOKEN_EXPIRE_SECONDS = 7 * 24 * 3600

def create_access_token(user_data: dict, expires_delta: timedelta | None = None, refresh: bool = False) -> str:
    payload = {
        "user": user_data,
        "exp": datetime.utcnow() + (expires_delta or timedelta(seconds=ACCESS_TOKEN_EXPIRE_SECONDS)),
        "jti": str(uuid.uuid4()),
        "refresh": refresh,
    }
    return jwt.encode(payload, Config.JWT_SECRET, algorithm=Config.JWT_ALGORITHM)

def decode_access_token(token: str) -> dict:
    try:
        return jwt.decode(token, Config.JWT_SECRET, algorithms=[Config.JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        return {"error": "Token has expired"}
    except jwt.InvalidTokenError:
        return {"error": "Invalid token"}
```

#### 4.3.3 依赖注入与权限检查

`dependencies.py` 中定义了通用的 token 验证逻辑：

```python
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer
from fastapi.security.http import HTTPAuthorizationCredentials

class TokenBearer(HTTPBearer):
    def __init__(self, auto_error: bool = True):
        super().__init__(auto_error=auto_error)

    async def __call__(self, request: Request):
        credentials = await super().__call__(request)
        if credentials is None:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid authorization credentials")

        token = credentials.credentials
        token_data = decode_access_token(token)
        if "error" in token_data:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=token_data["error"])
        if await token_in_blacklist(token_data["jti"]):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Token has been revoked")

        self.verify_token_data(token_data)
        return token_data

    def verify_token_data(self, token_data: dict):
        raise NotImplementedError

class AccessTokenBearer(TokenBearer):
    def verify_token_data(self, token_data: dict):
        if token_data.get("refresh"):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access token required")

class RefreshTokenBearer(TokenBearer):
    def verify_token_data(self, token_data: dict):
        if not token_data.get("refresh"):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Refresh token required")
```

通过 `Depends(AccessTokenBearer())` 注入登录用户信息，并通过角色检查器保护接口：

```python
class RoleChecker:
    def __init__(self, allowed_roles: list[str]):
        self.allowed_roles = allowed_roles

    def __call__(self, current_user: User = Depends(get_current_user)):
        if not current_user.is_verified:
            raise AccountNotVerified()
        if current_user.role not in self.allowed_roles:
            raise InsufficientPermissions()
        return True
```

调用方式示例：

```python
@book_router.get("/", dependencies=[Depends(role_checker)])
async def get_all_books(
    session: AsyncSession = Depends(get_session),
    token_details: dict = Depends(AccessTokenBearer()),
):
    """获取所有书籍"""
    books = await book_service.get_all_books(session=session)
    return books
```

#### 4.3.4 当前项目认证流程

当前项目的认证流程已经覆盖了大部分典型场景：

- `POST /api/v1/auth/signup`：用户注册后，调用 `UserService.create_user` 创建用户，并通过 Celery 异步发送邮箱验证链接。
- `GET /api/v1/auth/verify/{token}`：用户点击邮件中的链接后，使用 `itsdangerous` 生成的 URL-safe token 验证邮箱，并将 `is_verified` 设置为 `True`。
- `POST /api/v1/auth/login`：通过邮箱和密码登录，检查 `password_hash`，再生成 `access_token` 和 `refresh_token`。
- `GET /api/v1/auth/refresh_token`：使用 refresh token 获取新的 access token。
- `GET /api/v1/auth/me`：返回当前用户信息，依赖 `AccessTokenBearer()` 和 `RoleChecker` 进行身份验证与权限校验。
- `POST /api/v1/auth/logout`：将 access token 的 `jti` 写入 Redis 黑名单，实现注销撤销。
- `POST /api/v1/auth/password_reset` / `GET /api/v1/auth/password_reset_confirm/{token}`：实现密码重置请求和确认逻辑，通过邮件发送验证码/链接。

这个流程已经比较完整，但仍有优化空间：

- `refresh_token` 目前只基于 token payload 的 `refresh` 标记，而没有实际存储 refresh token 或做白名单验证。建议后续补齐 refresh token 的持久化和撤销策略。
- `signup` 发送邮件时，当前代码直接使用 `send_email.delay(...)`，这已经很好，但需要补充失败重试和日志记录机制。
- `RoleChecker` 的当前配置为 `allowed_roles=["admin", "user"]`，这个权限表达式是可用的，但实际项目中应该根据接口实际访问范围设置更细粒度的角色。

#### 4.3.5 Token 刷新与注销

刷新 token 路由：

```python
@auth_router.get("/refresh_token")
async def refresh_access_token(token_details: dict = Depends(RefreshTokenBearer())):
    """刷新 access token 的接口，前端可以在 access token 即将过期时调用这个接口来获取新的 access token"""
    if datetime.fromtimestamp(token_details["exp"]) <= datetime.utcnow():
        raise InvalidToken()
    return {"access_token": create_access_token(user_data=token_details["user"])}
```

注销流程使用 Redis 黑名单：

```python
from redis.asyncio import Redis
from src.config import Config

redis_token_blacklist = Redis.from_url(Config.REDIS_URL)

async def add_jti_to_blacklist(jti: str):
    """将 jti 添加到黑名单中，并设置过期时间"""
    await redis_token_blacklist.set(name=jti, value="", ex=3600)

async def token_in_blacklist(jti: str) -> bool:
    """检查 jti 是否在黑名单中"""
    return await redis_token_blacklist.exists(jti) == 1
```

注销接口：

```python
@auth_router.post("/logout")
async def logout_user(token_details: dict = Depends(AccessTokenBearer())):
    """注销用户，添加 jti 到黑名单"""
    await add_jti_to_blacklist(token_details["jti"])
    return {"message": "Logout successful. The token has been revoked."}
```

## 5. 邮件与异步任务

### 5.1 FastAPI-Mail

`mail.py`:

```python
from fastapi_mail import FastMail, ConnectionConfig, MessageSchema, MessageType
from pathlib import Path
from src.config import Config

BASE_DIR = Path(__file__).resolve().parent

mail_config = ConnectionConfig(
    MAIL_USERNAME=Config.MAIL_USERNAME,
    MAIL_PASSWORD=Config.MAIL_PASSWORD,
    MAIL_FROM=Config.MAIL_FROM,
    MAIL_PORT=Config.MAIL_PORT,
    MAIL_SERVER=Config.MAIL_SERVER,
    MAIL_FROM_NAME=Config.MAIL_FROM_NAME,
    MAIL_STARTTLS=True,
    MAIL_SSL_TLS=False,
    USE_CREDENTIALS=True,
    VALIDATE_CERTS=True,
    TEMPLATE_FOLDER=BASE_DIR / "templates",
)

mail = FastMail(config=mail_config)

def create_message(recipients: list[str], subject: str, body: str):
    return MessageSchema(
        recipients=recipients,
        subject=subject,
        body=body,
        subtype=MessageType.html,
    )
```

### 5.2 FastAPI BackgroundTasks

对于简单异步邮件发送，使用 `BackgroundTasks` 就足够：

```python
from fastapi import BackgroundTasks

@auth_router.post("/send_mail")
async def send_mail(emails: EmailModel, bg_tasks: BackgroundTasks):
    message = create_message(recipients=emails.addresses, subject="Welcome", body="<h1>Welcome to the app!</h1>")
    bg_tasks.add_task(mail.send_message, message)
    return {"message": "Email task added"}
```

### 5.3 Celery

Celery 适合高并发、需要重试的异步任务场景。配置示例：

```python
from celery import Celery
from src.mail import mail, create_message
from asgiref.sync import async_to_sync
from typing import List

c_app = Celery("bookly")
CLOUD = {
    "broker_url": Config.REDIS_URL,
    "result_backend": Config.REDIS_URL,
    "broker_connection_retry_on_startup": True,
}
c_app.conf.update(CLOUD)

@c_app.task()
def send_email(recipients: List[str], subject: str, body: str):
    message = create_message(recipients=recipients, subject=subject, body=body)
    async_to_sync(mail.send_message)(message)
```

调用 Celery 任务：

```python
@auth_router.post("/send_mail")
async def send_mail(emails: EmailModel):
    send_email.delay(emails.addresses, "Welcome", "<h1>Welcome to the app!</h1>")
    return {"message": "Email task queued"}
```

启动 worker：

```bash
celery -A src.celery_tasks worker --loglevel=info
```

启动 Flower：

```bash
celery -A src.celery_tasks flower
```

对于当前项目，`auth/routes.py` 中注册用户时的邮件发送流程已经体现出两种实现思路：

- `BackgroundTasks` 适用于简单场景，但它依赖于当前请求进程；如果进程崩溃，任务可能丢失。
- Celery 更适合邮件发送这种外部 I/O 任务：`src/celery_tasks.py` 将邮件发送封装成独立任务，`auth/routes.py` 在 `signup` 中通过 `send_email.delay(...)` 调度。

因此，当前项目中使用 Celery 发送注册验证邮件是合理的，但在文档中也要说明为什么保留 `BackgroundTasks` 作为轻量级备选方案。

## 6. 错误处理与中间件

### 6.1 自定义异常

`errors.py` 用于定义业务异常并注册统一响应：

```python
from typing import Any, Callable
from fastapi import FastAPI, status
from fastapi.requests import Request
from fastapi.responses import JSONResponse

class BooklyException(Exception):
    """Base exception for Bookly application."""

    pass

class InvalidToken(BooklyException):
    """Exception raised for invalid authentication tokens."""

    pass

class RevokedToken(BooklyException):
    """Exception raised for revoked authentication tokens."""

    pass

class AccessTokenRequired(BooklyException):
    """Exception raised for missing access tokens."""

    pass

class RefreshTokenRequired(BooklyException):
    """Exception raised for missing refresh tokens."""

    pass

class UserAlreadyExists(BooklyException):
    """Exception raised when trying to create a user that already exists."""

    pass

class InvalidCredentials(BooklyException):
    """Exception raised when invalid credentials are provided during login."""

    pass

class InsufficientPermissions(BooklyException):
    """Exception raised when a user does not have sufficient permissions to access a resource."""

    pass

class BookNotFound(BooklyException):
    """Exception raised when a requested book is not found."""

    pass

class UserNotFound(BooklyException):
    """Exception raised when a requested user is not found."""

    pass

class AccountNotVerified(Exception):
    """Exception raised for unverified account login attempts."""

    pass

def create_exception_handler(status_code: int, initial_detail: Any) -> Callable[[Request, Exception], JSONResponse]:
    """创建一个通用的异常处理器，用于将 BooklyException 转换为 HTTPException"""

    def exception_handler(request: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(
            status_code=status_code,
            content=initial_detail,
        )

    return exception_handler

def register_all_errors(app: FastAPI):
    app.add_exception_handler(
        InvalidCredentials,
        create_exception_handler(
            status.HTTP_401_UNAUTHORIZED,
            {"message": "Invalid email or password.", "code": "invalid_credentials"},
        ),
    )
    app.add_exception_handler(
        UserAlreadyExists,
        create_exception_handler(
            status_code=status.HTTP_403_FORBIDDEN,
            initial_detail={
                "message": "User with this email already exists.",
                "code": "user_already_exists",
            },
        ),
    )
    app.add_exception_handler(
        AccountNotVerified,
        create_exception_handler(
            status.HTTP_403_FORBIDDEN,
            {
                "message": "Account not verified. Please verify your email before logging in.",
                "error_code": "account_not_verified",
                "resolution": "Please check your email for the verification link and click it to verify your account.",
            },
        ),
    )

    @app.exception_handler(500)
    async def internal_server_error_handler(request, exc):
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "detail": "An unexpected error occurred. Please try again later.",
                "code": "internal_server_error",
            },
        )
```

建议补充 `HTTPException` 处理和 422 验证失败返回的统一格式。

### 6.2 中间件

`middleware.py` 注册日志、CORS、和 TrustedHost：

```python
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
import time
from rich.console import Console
from rich.text import Text

console = Console()

def register_middleware(app: FastAPI):
    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        start_time = time.time()
        method = request.method
        path = request.url.path
        client = request.client.host if request.client else "unknown"

        console.print(Text("INFO", style="bold white on green"), f"[bold]{method}[/bold] {path} from {client}")
        response = await call_next(request)
        console.print(Text("INFO", style="bold white on green"), f"[bold]{method}[/bold] {path} -> [bold]{response.status_code}[/bold] in {time.time() - start_time:.2f}s")
        return response

    app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"], allow_credentials=True)
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["localhost", "127.0.0.1"])
```

## 7. 代码问题与建议

### 7.1 文档层面

- 当前文档中存在缩进和语法不一致的问题，建议统一使用 Markdown 标题、代码块和段落。
- 代码示例和说明应分离，避免行内注释过多导致阅读困难。
- 少量拼写错误需修正，如 `pydantic_seetings`、`get*session`、`auth*router`、`src.selery_tasks`。

### 7.2 项目实现层面

- `AsyncEngine(create_engine(...))` 不推荐。应使用 `create_async_engine` 配合 `AsyncSession`。
- `get_session` 要有正确名称和类型提示。
- 如果 `expire_on_commit=False`，需要在提交后 `await session.refresh(model)` 来确保新生成字段可访问。
- 不要在 API 返回中暴露 `password_hash`。
- 在 `BookUpdateModel` 中，只更新非 None 字段，避免意外覆盖。
- 角色校验逻辑可以更清晰：使用 `Depends(role_checker)` 时，`RoleChecker` 返回 `True` 或抛出异常。
- 在 `refresh_token` 接口中，若 `exp` 已过期应直接返回 403，对返回值格式保持一致。
- `send_email.delay([new_user.email], ...)` 代码示例中应使用 `emails.addresses` 或传入实际变量。

### 7.3 FastAPI 设计建议

- 建议将路由路径设计成 RESTful 风格，例如：
  - `GET /books` 获取列表
  - `GET /books/{uid}` 获取详情
  - `POST /books` 创建
  - `PUT /books/{uid}` 更新
  - `DELETE /books/{uid}` 删除
- 业务逻辑应保持在 service 层，router 层只负责请求参数解析、权限校验、响应返回。
- 对于邮件这类操作，优先用 `BackgroundTasks` 解决简单异步场景，使用 Celery 时考虑任务可重试、持久化和监控。
- 日志中间件需要注意性能，生产环境建议配合 `uvicorn` 日志或者 `structlog`。

## 8. TODO 学习计划

- [ ] 完善项目启动与路由注册流程，确认 `main.py` / `app.py` 中的应用初始化、错误处理、依赖注册和中间件加载是否完整。
- [ ] 修正当前数据库配置中的不一致，实现 `create_async_engine` + `AsyncSession`。保证 `get_session` 的实现符合异步 SQLAlchemy 最佳实践。
- [ ] 完善 SQLModel 设计：保留 `src/db/models.py` 中的关系定义，同时进一步区分数据库模型和 API schema，避免 `password_hash`、内部字段直接作为响应返回。
- [ ] 补全认证流程中的关键功能：邮箱验证流程、刷新 token 逻辑、token 撤销逻辑、密码重置流程、角色权限校验。
- [ ] 强化邮件异步执行的可靠性：评估当前 Celery 发送邮件方案，补充失败重试、错误告警、Flower 监控使用说明。
- [ ] 完成 `BackgroundTasks` 与 Celery 的对比说明，明确当前项目为何使用 Celery 以及何时可以回退到 `BackgroundTasks`。
- [ ] 给 `Alembic` 迁移流程补齐项目级说明：当前项目如何从 `models.py` 自动生成迁移、如何执行升级、如何管理版本脚本。
- [ ] 覆盖关键功能的测试：用户注册、登录、权限接口、书籍 CRUD、邮件发送入口、Redis token 黑名单、异常处理。
- [ ] 规划生产环境部署：`uvicorn` 参数、日志、CORS、TrustedHost、环境变量、安全配置、Redis/数据库连接、容器化方案。
- [ ] 未来能力预期：希望最终达到“完整可用的用户认证与授权系统、稳定的书籍管理 API、可靠的异步邮件任务处理、清晰一致的代码文档和可维护项目结构”。

## 9. 个人复盘建议

- 多做小项目：把一个 CRUD 项目拆成多个子功能，逐步实现并测试。
- 读官方文档：FastAPI、SQLModel、Alembic、Celery 都有很好示例。
- 用代码写文档：先写实现，再写说明，最后把说明和实现对齐。
- 代码复盘时，从设计原则出发，而不是只看功能是否可行。
- 随时修正不一致的代码和文档，保持项目可读性。
