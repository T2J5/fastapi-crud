from typing import AsyncGenerator
from sqlmodel import create_engine, SQLModel
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from src.config import Config
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.orm import sessionmaker

# 创建异步数据库引擎
async_engine = AsyncEngine(create_engine(url=Config.DATABASE_URL))
# async_engine = create_async_engine(url=Config.DATABASE_URL, echo=True)


# 初始化数据库
async def init_db():
    async with async_engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)


# 创建数据库会话
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    Session = sessionmaker(
        bind=async_engine, class_=AsyncSession, expire_on_commit=False
    )
    async with Session() as session:
        yield session
