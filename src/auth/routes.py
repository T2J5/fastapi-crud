from fastapi import APIRouter, Depends, status, BackgroundTasks
from fastapi.responses import JSONResponse

from src.db.redis import add_jti_to_blacklist
from .schemas import (
    PasswordResetConfirmModel,
    UserCreateModel,
    UserModel,
    UserLoginModel,
    UserBooksModel,
    EmailModel,
    PasswordResetModel,
)
from .service import UserService
from src.db.main import get_session
from sqlmodel.ext.asyncio.session import AsyncSession
from .utils import (
    create_access_token,
    create_hashed_password,
    create_url_safe_token,
    decode_url_safe_token,
    verify_password,
)
from datetime import timedelta, datetime
from typing import List
from .dependencies import (
    RefreshTokenBearer,
    AccessTokenBearer,
    get_current_user,
    RoleChecker,
)
from src.errors import InvalidToken, UserAlreadyExists, InvalidCredentials, UserNotFound
from src.config import Config
from src.celery_tasks import send_email

auth_router = APIRouter()
user_service = UserService()
role_checker = RoleChecker(
    allowed_roles=["admin", "user"]
)  # 这里我们创建了一个 RoleChecker 实例，并将 allowed_roles 设置为 ["admin"]，表示只有具有 "admin" 角色的用户才能通过这个检查器的验证。你可以根据需要调整 allowed_roles 列表来允许其他角色访问特定的接口。

REFRESH_TOKEN_EXPIRE_SECONDS = 7 * 24 * 60 * 60


@auth_router.get("/verify/{token}")
async def verify_user_email(token: str, session: AsyncSession = Depends(get_session)):
    decoded_token_data = decode_url_safe_token(token)

    user_email = decoded_token_data.get("email")

    if user_email:
        user = await user_service.get_user_by_email(user_email, session)

        if not user:
            raise UserNotFound()
        await user_service.update_user(
            user=user, user_data={"is_verified": True}, session=session
        )
        return JSONResponse(
            content={"message": "Email verified successfully. You can now log in."},
            status_code=status.HTTP_200_OK,
        )
    return JSONResponse(
        content={"message": "Invalid or expired token."},
        status_code=status.HTTP_400_BAD_REQUEST,
    )


@auth_router.post("/signup", status_code=status.HTTP_201_CREATED)
async def create_user_account(
    user_data: UserCreateModel,
    bg_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
):
    email = user_data.email

    user_exists = await user_service.user_exists(email, session)

    if user_exists:
        raise UserAlreadyExists()
    else:
        new_user = await user_service.create_user(user_data, session)

        token = create_url_safe_token({"email": new_user.email})
        link = f"http://{Config.DOMAIN}/api/v1/auth/verify/{token}"
        html_message = f"""
        <h1>Welcome to the app!</h1>
        <p>Please confirm your email by clicking the link below:</p>
        <a href="{link}">{link}</a>
        """

        # message = create_message(
        #     recipients=[new_user.email],
        #     subject="Email Confirmation",
        #     body=html_message,
        # )

        send_email.delay([new_user.email], "Email Confirmation", html_message)
        # bg_tasks.add_task(mail.send_message, message)
        # await mail.send_message(message)

        return {
            "message": "User created successfully. Please check your email to confirm your account.",
            "user": new_user,
        }


@auth_router.get("/users", response_model=List[UserModel])
async def get_all_users(session: AsyncSession = Depends(get_session)):
    users = await user_service.get_all_users(session)

    return users


@auth_router.post("/login")
async def login_user(
    user_login_data: UserLoginModel, session: AsyncSession = Depends(get_session)
):
    email = user_login_data.email
    password = user_login_data.password

    user = await user_service.get_user_by_email(email, session)

    if user is not None:
        password_valid = verify_password(
            plain_password=password, hashed_password=user.password_hash
        )
        if password_valid:
            access_token = create_access_token(
                user_data={
                    "email": user.email,
                    "user_uid": str(user.uid),
                    "role": user.role,
                }
            )

            refresh_token = create_access_token(
                user_data={
                    "email": user.email,
                    "user_uid": str(user.uid),
                    "role": user.role,
                },
                refresh=True,
                expires_delta=timedelta(seconds=REFRESH_TOKEN_EXPIRE_SECONDS),
            )
            return JSONResponse(
                content={
                    "message": "Login successful",
                    "access_token": access_token,
                    "refresh_token": refresh_token,
                    "user": {
                        "email": user.email,
                        "user_uid": str(user.uid),
                        "role": user.role,
                    },
                },
                status_code=status.HTTP_200_OK,
            )
    raise InvalidCredentials()


@auth_router.get("/refresh_token")
async def refresh_access_token(token_details: dict = Depends(RefreshTokenBearer())):
    """刷新 access token 的接口，前端可以在 access token 即将过期时调用这个接口来获取新的 access token"""
    # 这里的实现会依赖于你如何存储和管理 refresh token。通常情况下，你需要在数据库中存储 refresh token，并且在用户登录时生成一个新的 refresh token。
    # 当用户调用这个接口时，你需要验证他们提供的 refresh token 是否有效，如果有效，则生成一个新的 access token 并返回给用户。
    expired_timestamp = token_details["exp"]
    if datetime.fromtimestamp(expired_timestamp) > datetime.now():
        new_access_token = create_access_token(
            user_data=token_details["user"],
        )
        return JSONResponse(
            content={
                "access_token": new_access_token,
            }
        )
    raise InvalidToken()


@auth_router.get("/me", response_model=UserBooksModel)
async def get_current_user_details(
    user=Depends(get_current_user), _: bool = Depends(role_checker)
):
    """获取当前用户信息的接口，前端可以在用户登录后调用这个接口来获取当前用户的信息"""
    return user


@auth_router.post("/logout")
async def logout_user(token_details: dict = Depends(AccessTokenBearer())):
    jti = token_details["jti"]

    await add_jti_to_blacklist(jti)

    return JSONResponse(
        content={
            "message": "Logout successful. The token has been revoked and cannot be used anymore."
        },
        status_code=status.HTTP_200_OK,
    )


@auth_router.post("/send_mail")
async def send_mail(emails: EmailModel):
    recipients = emails.addresses

    html = "<h1>Welcome to the app !</h1>"

    send_email.delay(recipients, "Welcome", html)

    # message = create_message(
    #     recipients=recipients,
    #     subject="Welcome",
    #     body=html,
    # )

    # await mail.send_message(message)
    return {"message": "Email sent successfully"}


@auth_router.post("/password_reset")
async def password_reset_request(
    email_data: PasswordResetModel,
    password: PasswordResetConfirmModel,
    session: AsyncSession = Depends(get_session),
):
    email = email_data.email
    new_password = password.new_password
    confirm_new_password = password.confirm_new_password

    user = await user_service.get_user_by_email(email, session)

    if not user:
        raise UserNotFound()

    token = create_url_safe_token(
        {
            "email": user.email,
            "new_password": new_password,
            "confirm_new_password": confirm_new_password,
        }
    )
    link = f"http://{Config.DOMAIN}/api/v1/auth/password_reset_confirm/{token}"
    html_message = f"""
    <h1>Password Reset Request</h1>
    <p>You requested a password reset. Click the link below to reset your password:</p>
    <a href="{link}">{link}</a>
    """

    send_email.delay([user.email], "Password Reset Request", html_message)
    # message = create_message(
    #     recipients=[user.email],
    #     subject="Password Reset Request",
    #     body=html_message,
    # )

    # await mail.send_message(message)

    return JSONResponse(
        content={
            "message": "Password reset email sent successfully. Please check your email for the reset link."
        },
        status_code=status.HTTP_200_OK,
    )


@auth_router.get("/password_reset_confirm/{token}")
async def password_reset_confirm(
    token: str, session: AsyncSession = Depends(get_session)
):
    token_data = decode_url_safe_token(token)
    email = token_data.get("email")
    new_password = token_data.get("new_password")
    confirm_new_password = token_data.get("confirm_new_password")

    if not email or not new_password or not confirm_new_password:
        return JSONResponse(
            content={
                "message": "Invalid token data.",
            },
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    if new_password != confirm_new_password:
        return JSONResponse(
            content={
                "message": "Passwords do not match.",
            },
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    user = await user_service.get_user_by_email(email, session)
    if not user:
        raise UserNotFound()

    await user_service.update_user(
        user, {"password_hash": create_hashed_password(new_password)}, session
    )

    return JSONResponse(
        content={
            "message": "Password reset successful.",
        },
        status_code=status.HTTP_200_OK,
    )
