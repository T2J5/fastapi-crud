from passlib.context import CryptContext
from datetime import timedelta, datetime
import jwt
from src.config import Config
import uuid
import logging
from itsdangerous import URLSafeTimedSerializer


password_context = CryptContext(schemes=["bcrypt"])

ACCESS_TOKEN_EXPIRE_SECONDS = 60

serializer = URLSafeTimedSerializer(Config.JWT_SECRET, salt="email-confirmation-salt")


def create_url_safe_token(data: dict) -> str:
    return serializer.dumps(data)


def decode_url_safe_token(token: str) -> dict:
    try:
        data = serializer.loads(token)
        return data
    except Exception as e:
        logging.error(f"Token decoding error: {str(e)}")
        return {"error": "Invalid or expired token"}


def create_hashed_password(plain_password: str) -> str:
    return password_context.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return password_context.verify(plain_password, hashed_password)


def create_access_token(
    user_data: dict, expires_delta: timedelta | None = None, refresh: bool = False
) -> str:
    payload = {}

    payload["user"] = user_data
    payload["exp"] = datetime.now() + (
        expires_delta
        if expires_delta
        else timedelta(seconds=ACCESS_TOKEN_EXPIRE_SECONDS)
    )

    # 唯一的 JWT ID，用于标识该 token。uuid.uuid4() 生成的是UUID对象，str(uuid.uuid4()) 生成一个随机的 UUID，并将其转换为字符串形式。
    payload["jti"] = str(uuid.uuid4())

    payload["refresh"] = refresh

    token = jwt.encode(
        payload=payload,
        key=Config.JWT_SECRET,
        algorithm=Config.JWT_ALGORITHM,
    )

    return token


def decode_access_token(token: str) -> dict:
    try:
        payload = jwt.decode(
            jwt=token,
            key=Config.JWT_SECRET,
            algorithms=[Config.JWT_ALGORITHM],
        )
        return payload
    except jwt.ExpiredSignatureError:
        return {"error": "Token has expired"}
    except jwt.InvalidTokenError:
        return {"error": "Invalid token"}
    except jwt.PyJWKError as e:
        logging.error(f"JWT decoding error: {str(e)}")
        return {"error": "Error decoding token"}
