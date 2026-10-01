"""Optional cookie-based access gate for a private supervisor demo."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, Response, status
from pydantic import BaseModel, Field

from ..core.config import settings
from ..core.security import (
    access_cookie_is_valid,
    access_token_is_valid,
    build_access_cookie,
)


router = APIRouter(prefix="/auth", tags=["Demo Access"])


class LoginRequest(BaseModel):
    access_token: str = Field(min_length=1, max_length=256)


class AccessStatus(BaseModel):
    required: bool
    authenticated: bool


@router.get("/status", response_model=AccessStatus)
def access_status(request: Request) -> AccessStatus:
    """Tell the frontend whether the optional deployment gate is unlocked."""

    authenticated = access_cookie_is_valid(
        request.cookies.get(settings.access_cookie_name)
    )
    return AccessStatus(
        required=settings.access_protection_enabled,
        authenticated=authenticated,
    )


@router.post("/login", response_model=AccessStatus)
def login(payload: LoginRequest, response: Response) -> AccessStatus:
    """Exchange the configured supervisor token for an HTTP-only cookie."""

    if not access_token_is_valid(payload.access_token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="The supervisor access token is incorrect.",
        )

    if settings.access_protection_enabled:
        response.set_cookie(
            key=settings.access_cookie_name,
            value=build_access_cookie(settings.access_token),
            max_age=settings.access_session_hours * 60 * 60,
            httponly=True,
            secure=settings.secure_cookies,
            samesite="strict",
            path="/",
        )
    return AccessStatus(required=settings.access_protection_enabled, authenticated=True)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(response: Response) -> Response:
    """Clear the private-demo session cookie."""

    response.delete_cookie(
        key=settings.access_cookie_name,
        path="/",
        secure=settings.secure_cookies,
        httponly=True,
        samesite="strict",
    )
    response.status_code = status.HTTP_204_NO_CONTENT
    return response
