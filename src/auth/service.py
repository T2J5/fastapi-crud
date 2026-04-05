from .schemas import UserCreateModel
from src.db.models import User
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select, desc
from .utils import create_hashed_password


class UserService:
    async def create_user(self, user_data: UserCreateModel, session: AsyncSession):
        user_data_dict = user_data.model_dump()

        new_user = User(**user_data_dict)

        new_user.password_hash = create_hashed_password(user_data_dict["password"])
        new_user.role = "user"  # 默认角色为 "user"

        session.add(new_user)

        await session.commit()

        return new_user

    async def get_user_by_email(self, email: str, session: AsyncSession):
        statement = select(User).where(User.email == email)

        result = await session.exec(statement)

        user = result.first()

        return user if user is not None else None

    async def user_exists(self, email: str, session: AsyncSession):
        user = await self.get_user_by_email(email, session)

        return True if user is not None else False

    async def get_all_users(self, session: AsyncSession):
        statement = select(User).order_by(desc(User.created_at))

        result = await session.exec(statement)

        users = result.all()

        return users

    async def get_user_by_id(self, user_id: str, session: AsyncSession):
        statement = select(User).where(User.uid == user_id)

        result = await session.exec(statement)

        user = result.first()

        return user if user is not None else None

    async def update_user(self, user: User, user_data: dict, session: AsyncSession):
        for k, v in user_data.items():
            setattr(user, k, v)

        await session.commit()

        return user
