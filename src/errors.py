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
    """Exception raised when a user tries to log in with an unverified account."""

    pass


def create_exception_handler(
    status_code: int, initial_detail: Any
) -> Callable[[Request, Exception], JSONResponse]:
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
