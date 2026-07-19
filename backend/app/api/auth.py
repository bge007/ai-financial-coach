from datetime import date

from authlib.integrations.starlette_client import OAuth, OAuthError
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import COOKIE_NAME, SESSION_TTL_SECONDS, create_session_token, get_current_user, get_or_create_demo_user
from app.core.config import get_settings
from app.core.db import get_db
from app.core.passwords import hash_password, verify_password
from app.models.schemas import AuthUserOut, LoginIn, SignupIn
from app.models.user import User
from app.models.user_profile import UserProfile

router = APIRouter(prefix="/auth", tags=["auth"])

_settings = get_settings()

oauth = OAuth()
oauth.register(
    name="google",
    client_id=_settings.google_client_id,
    client_secret=_settings.google_client_secret,
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile"},
)


def _age_from_dob(dob: date) -> int | None:
    today = date.today()
    age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
    if age < 18 or age > 100:
        return None
    return age


def _user_out(user: User) -> dict:
    return AuthUserOut(
        id=user.id,
        email=user.email,
        name=user.name,
        dob=user.dob,
        gender=user.gender,
    ).model_dump(mode="json")


def _set_session_cookie(response: Response, user_id: int) -> None:
    settings = get_settings()
    response.set_cookie(
        key=COOKIE_NAME,
        value=create_session_token(user_id),
        httponly=True,
        samesite="lax",
        secure=settings.environment == "production",
        max_age=SESSION_TTL_SECONDS,
        path="/",
    )


@router.post("/signup")
async def signup(body: SignupIn, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(User).where(User.email == body.email))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status_code=409, detail="An account with this email already exists")

    user = User(
        google_sub=None,
        email=body.email,
        name=body.name,
        password_hash=hash_password(body.password),
        dob=body.dob,
        gender=body.gender,
    )
    db.add(user)
    await db.flush()

    profile = UserProfile(
        user_id=user.id,
        name=body.name,
        age=_age_from_dob(body.dob),
    )
    db.add(profile)
    await db.commit()
    await db.refresh(user)

    response = JSONResponse(content=_user_out(user), status_code=201)
    _set_session_cookie(response, user.id)
    return response


@router.post("/login")
async def password_login(body: LoginIn, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if not user.password_hash:
        raise HTTPException(
            status_code=401,
            detail="This account has no password set. Sign up with email/password to continue.",
        )
    if not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    response = JSONResponse(content=_user_out(user))
    _set_session_cookie(response, user.id)
    return response


@router.get("/login")
async def google_login(request: Request):
    """Legacy Google OAuth entry (unused by the demo UI)."""
    settings = get_settings()
    return await oauth.google.authorize_redirect(
        request, settings.oauth_redirect_uri
    )


@router.get("/callback")
async def callback(request: Request, db: AsyncSession = Depends(get_db)):
    settings = get_settings()
    try:
        token = await oauth.google.authorize_access_token(request)
    except OAuthError as exc:
        raise HTTPException(status_code=401, detail=f"OAuth failed: {exc.error}")

    userinfo = token.get("userinfo")
    if not userinfo or "sub" not in userinfo:
        raise HTTPException(status_code=401, detail="OAuth response missing userinfo")

    result = await db.execute(
        select(User).where(User.google_sub == userinfo["sub"])
    )
    user = result.scalar_one_or_none()
    if user is None:
        user = User(
            google_sub=userinfo["sub"],
            email=userinfo.get("email", ""),
            name=userinfo.get("name", ""),
        )
        db.add(user)
    else:
        user.email = userinfo.get("email", user.email)
        user.name = userinfo.get("name", user.name)
    await db.commit()
    await db.refresh(user)

    response = RedirectResponse(url=f"{settings.frontend_url.rstrip('/')}/data")
    _set_session_cookie(response, user.id)
    return response


@router.post("/demo")
async def demo_login(db: AsyncSession = Depends(get_db)):
    """Dev-only: sign in as the fixed demo user when AUTH_DISABLED is enabled."""
    if not get_settings().auth_disabled:
        raise HTTPException(status_code=404, detail="Not available")
    user = await get_or_create_demo_user(db)
    response = JSONResponse(content=_user_out(user))
    _set_session_cookie(response, user.id)
    return response


@router.get("/me")
async def me(user: User = Depends(get_current_user)):
    return _user_out(user)


@router.post("/logout")
async def logout():
    response = JSONResponse(content={"ok": True})
    response.delete_cookie(COOKIE_NAME, path="/")
    return response
