from authlib.integrations.starlette_client import OAuth, OAuthError
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import COOKIE_NAME, create_session_token, get_current_user
from app.core.config import get_settings
from app.core.db import get_db
from app.models.user import User

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


@router.get("/login")
async def login(request: Request):
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

    response = RedirectResponse(url=settings.frontend_url)
    response.set_cookie(
        key=COOKIE_NAME,
        value=create_session_token(user.id),
        httponly=True,
        samesite="lax",
        secure=settings.environment == "production",
        max_age=7 * 24 * 3600,
        path="/",
    )
    return response


@router.get("/me")
async def me(user: User = Depends(get_current_user)):
    return {"id": user.id, "email": user.email, "name": user.name}


@router.post("/logout")
async def logout():
    response = RedirectResponse(url="/", status_code=303)
    response.delete_cookie(COOKIE_NAME, path="/")
    return response
