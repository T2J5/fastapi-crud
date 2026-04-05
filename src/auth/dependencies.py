from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer
from fastapi.security.http import HTTPAuthorizationCredentials
from sqlmodel.ext.asyncio.session import AsyncSession
from typing import List

from src.db.main import get_session
from src.db.redis import token_in_blacklist
from .utils import decode_access_token
from .service import UserService
from src.db.models import User
from src.errors import (
    AccountNotVerified,
    InsufficientPermissions,
    InvalidToken,
    RevokedToken,
    AccessTokenRequired,
    RefreshTokenRequired,
)

user_service = UserService()


class TokenBearer(HTTPBearer):
    def __init__(self, auto_error: bool = True):
        super().__init__(auto_error=auto_error)

    async def __call__(self, request: Request) -> HTTPAuthorizationCredentials | None:
        credentials = await super().__call__(request)

        if credentials is None:
            raise HTTPException(
                status_code=403, detail="Invalid authorization credentials"
            )
        token = credentials.credentials
        if not self.token_valid(token):
            raise InvalidToken()
        token_data = decode_access_token(token)
        if "error" in token_data:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"error": "Invalid or expired token"},
            )
        if await token_in_blacklist(token_data["jti"]):
            raise RevokedToken()
        # 验证 token_data 的内容，子类可以在这里实现特定的验证逻辑
        self.verify_token_data(token_data)

        return token_data  # type: ignore 这里直接返回 token_data，子类可以在 verify_token_data 方法中对其进行验证

    def token_valid(self, token: str) -> bool:
        token_data = decode_access_token(token)

        if "error" in token_data:
            return False

        return True

    def verify_token_data(self, token_data: dict):
        """
        子类需要实现这个方法来验证 token_data 中的内容
        """
        raise NotImplementedError(
            "Subclasses must implement the verify_token_data method"
        )


class AccessTokenBearer(TokenBearer):
    def verify_token_data(self, token_data: dict):
        if token_data and token_data.get("refresh"):
            raise AccessTokenRequired()


class RefreshTokenBearer(TokenBearer):
    def verify_token_data(self, token_data: dict):
        if token_data and not token_data.get("refresh"):
            raise RefreshTokenRequired()


async def get_current_user(
    token_data: dict = Depends(AccessTokenBearer()),
    session: AsyncSession = Depends(get_session),
):
    user_email: str = token_data["user"]["email"]

    user = await user_service.get_user_by_email(user_email, session)

    return user


class RoleChecker:
    def __init__(self, allowed_roles: List[str]):
        self.allowed_roles = allowed_roles

    def __call__(self, current_user: User = Depends(get_current_user)):
        if not current_user.is_verified:
            raise AccountNotVerified()

        if current_user.role in self.allowed_roles:
            return True
        raise InsufficientPermissions()
