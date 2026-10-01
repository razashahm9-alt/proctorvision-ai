"""Small security helpers for a protected supervisor demonstration."""

from __future__ import annotations

import hashlib
import hmac
from urllib.parse import urlsplit

from .config import Settings, settings


COOKIE_PURPOSE = b"proctorvision-supervisor-session-v1"


def build_access_cookie(access_token: str) -> str:
    """Derive an opaque cookie without storing the configured token itself."""

    return hmac.new(
        access_token.encode("utf-8"),
        COOKIE_PURPOSE,
        hashlib.sha256,
    ).hexdigest()


def access_cookie_is_valid(
    cookie_value: str | None,
    application_settings: Settings = settings,
) -> bool:
    """Allow open local mode or validate the protected-demo session cookie."""

    if not application_settings.access_protection_enabled:
        return True
    if not cookie_value:
        return False
    expected = build_access_cookie(application_settings.access_token)
    return hmac.compare_digest(cookie_value, expected)


def access_token_is_valid(
    supplied_token: str,
    application_settings: Settings = settings,
) -> bool:
    """Compare the supplied demo token without timing-sensitive equality."""

    if not application_settings.access_protection_enabled:
        return True
    return hmac.compare_digest(
        supplied_token.encode("utf-8"),
        application_settings.access_token.encode("utf-8"),
    )


def websocket_origin_is_allowed(
    origin: str | None,
    host: str | None,
    application_settings: Settings = settings,
) -> bool:
    """Accept same-origin WebSockets plus explicitly configured dev origins."""

    if not origin:
        return True
    normalized_origin = origin.rstrip("/")
    if normalized_origin in application_settings.cors_origin_list:
        return True
    try:
        origin_host = urlsplit(normalized_origin).netloc.lower()
    except ValueError:
        return False
    return bool(host and origin_host == host.lower())
