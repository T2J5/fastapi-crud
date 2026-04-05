from redis.asyncio import Redis
from src.config import Config

JTI_EXPIRATION_SECONDS = (
    1 * 60 * 60
)  # jti 在 Redis 中的过期时间，单位为秒，这里设置为1小时
# redis_token_blacklist = Redis(host=Config.REDIS_HOST, port=Config.REDIS_PORT, db=0)
redis_token_blacklist = Redis.from_url(Config.REDIS_URL)


async def add_jti_to_blacklist(jti: str):
    """将 jti 添加到黑名单中，并设置过期时间"""
    await redis_token_blacklist.set(name=jti, ex=JTI_EXPIRATION_SECONDS, value="")


async def token_in_blacklist(jti: str) -> bool:
    """检查 jti 是否在黑名单中"""
    is_blacklisted = await redis_token_blacklist.exists(jti)
    return is_blacklisted == 1
