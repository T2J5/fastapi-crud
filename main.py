from datetime import datetime
import logging
import time

from fastapi import Depends, FastAPI, Path, Query, HTTPException, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from sqlalchemy import DateTime, Float, String, func
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from rich import pretty, traceback
from rich.console import Console
from rich.logging import RichHandler
from rich.panel import Panel

# 安装 Rich 的 pretty print 和 traceback
pretty.install()
traceback.install(show_locals=True)

# 配置 Rich 日志
logging.basicConfig(
    level="INFO",
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(rich_tracebacks=True, markup=True)],
)
logger = logging.getLogger("app")
console = Console()

ASYNC_DATABASE_URL = (
    "mysql+aiomysql://root:wangtao@localhost:3306/fastapi?charset=utf8mb4"
)
async_engine = create_async_engine(
    ASYNC_DATABASE_URL, echo=True, pool_size=10, max_overflow=20
)


class Base(DeclarativeBase):
    create_time: Mapped[datetime] = mapped_column(
        DateTime, default=func.now, insert_default=func.now(), comment="创建时间"
    )
    update_time: Mapped[datetime] = mapped_column(
        DateTime,
        default=func.now,
        insert_default=func.now(),
        onupdate=func.now(),
        comment="更新时间",
    )


class Book(Base):
    __tablename__ = "books"

    id: Mapped[int] = mapped_column(
        primary_key=True, autoincrement=True, comment="书籍ID"
    )
    title: Mapped[str] = mapped_column(String(255), comment="书籍标题")
    price: Mapped[float] = mapped_column(Float, comment="书籍价格")


async def create_tables():
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)  # 使用模型类的元数据创建


app = FastAPI()


@app.on_event("startup")
async def startup_event():
    console.print(
        Panel.fit(
            "[bold cyan]FastAPI 服务已启动[/]\n"
            "[green]http://127.0.0.1:8000[/]",
            title="Startup",
        )
    )
    logger.info("[bold green]开始创建数据库表...[/]")
    await create_tables()
    logger.info("[bold green]数据库表创建完成[/]")


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    logger.info(
        f"[bold blue]{request.method}[/] [yellow]{request.url.path}[/]"
    )
    response = await call_next(request)
    process_time = (time.time() - start_time) * 1000
    logger.info(
        f"[bold magenta]{response.status_code}[/] "
        f"{request.method} {request.url.path} - "
        f"{process_time:.2f}ms"
    )
    return response


# async def common_params(
#     skip: int = Query(0, description="跳过的数量", lt=100),
#     limit: int = Query(10, description="返回的数量", gt=0, lt=100),
# ):
#     return {"skip": skip, "limit": limit}


@app.get("/")
async def read_root():
    return {"Hello": "World111"}


# 路径参数, 类型注解
# @app.get("/book/{book_id}/{t_id}")
# async def get_book(
#     book_id: int,
#     t_id: int = Path(
#         ..., gt=0, lt=101, description="这是书籍的id，必须是1-100之间的整数"
#     ),
# ):
#     return {"book_id": book_id, "t_id": t_id, "desc": f"这是第{t_id}本书籍"}


# @app.get("/author/{author_name}")
# async def get_author(
#     author_name: str = Path(
#         ...,
#         min_length=3,
#         max_length=50,
#         description="这是作者的名字，长度必须在3-50之间",
#     ),
# ):
#     return {"author_name": author_name, "desc": f"这是作者{author_name}的简介"}


# @app.get("/book/list")
# async def get_book_list(
#     skip: int = Query(0, description="跳过的书籍数量", lt=100),
#     limit: int = Query(10, description="返回的书籍数量", gt=0, lt=100),
# ):
#     return {"book_list": ["书籍1", "书籍2", "书籍3"]}


# class BookModel(BaseModel):
#     title: str = Field(
#         ..., min_length=1, max_length=100, description="书籍的标题，长度必须在1-100之间"
#     )
#     author: str
#     description: str


# @app.post("/book/create")
# async def create_book(book: BookModel):
#     return {"message": "书籍创建成功", "book": book}


# @app.get("/html", response_class=HTMLResponse)
# async def get_html():
#     return "<h1>Hello, World!</h1>"


# @app.get("/news/{id}", response_model=Book)
# async def get_news(id: int):
#     if id < 1 or id > 100:
#         raise HTTPException(status_code=404, detail="新闻未找到")
#     return Book(title=f"新闻{id}", author="新闻作者", description=f"这是新闻{id}的描述")


# @app.middleware("http")
# async def log_requests(request, call_next):
#     print(f"Incoming request: {request.method} {request.url}")
#     response = await call_next(request)
#     print(f"Response status: {response.status_code}")
#     return response


# @app.get("/news_list")
# async def get_news_list_common(params: dict = Depends(common_params)):
#     return params
