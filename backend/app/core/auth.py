import time

from authlib.jose import JoseError, jwt
from fastapi import Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.db import get_db
from app.models.user import User

COOKIE_NAME = "session"
SESSION_TTL_SECONDS = 7 * 24 * 3600  # 7 days

# Fixed identity used only when settings.auth_disabled is true.
DEMO_GOOGLE_SUB = "demo-user"
DEMO_EMAIL = "demo@localhost"
DEMO_NAME = "Demo User"


def create_session_token(user_id: int) -> str:
    settings = get_settings()
    now = int(time.time())
    payload = {"sub": str(user_id), "iat": now, "exp": now + SESSION_TTL_SECONDS}
    token = jwt.encode({"alg": "HS256"}, payload, settings.secret_key)
    return token.decode() if isinstance(token, bytes) else token


def decode_session_token(token: str) -> int | None:
    settings = get_settings()
    try:
        claims = jwt.decode(token, settings.secret_key)
        claims.validate()  # enforces exp
        return int(claims["sub"])
    except (JoseError, KeyError, TypeError, ValueError):
        return None


async def get_or_create_demo_user(db: AsyncSession) -> User:
    result = await db.execute(select(User).where(User.google_sub == DEMO_GOOGLE_SUB))
    user = result.scalar_one_or_none()
    if user is None:
        user = User(google_sub=DEMO_GOOGLE_SUB, email=DEMO_EMAIL, name=DEMO_NAME)
        db.add(user)
        await db.commit()
        await db.refresh(user)
    return user


async def get_current_user(
    request: Request, db: AsyncSession = Depends(get_db)
) -> User:
    token = request.cookies.get(COOKIE_NAME)
    if token:
        user_id = decode_session_token(token)
        if user_id is not None:
            user = await db.get(User, user_id)
            if user is not None:
                return user

    if get_settings().auth_disabled:
        return await get_or_create_demo_user(db)

    raise HTTPException(status_code=401, detail="Not authenticated")
