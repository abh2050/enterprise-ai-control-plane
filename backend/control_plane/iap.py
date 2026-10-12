"""Identity-Aware Proxy JWT verification (Section 10).

Every request in IAP mode must carry ``x-goog-iap-jwt-assertion``. The token must be an
ES256 JWT signed by one of IAP's published keys, with issuer
``https://cloud.google.com/iap``, the configured audience
(``/projects/NUMBER/locations/REGION/services/NAME`` for Cloud Run), and a valid expiry.
Public keys are cached for an hour. Any failure rejects the request.
"""

from __future__ import annotations

import json
import threading
import time
import urllib.request
from collections.abc import Callable
from typing import Any

from google.auth import exceptions, jwt

IAP_ISSUER = "https://cloud.google.com/iap"
PUBLIC_KEYS_URL = "https://www.gstatic.com/iap/verify/public_key"
KEY_TTL_SECONDS = 3600


class IapError(Exception):
    pass


class KeyCache:
    def __init__(self, fetch: Callable[[], dict[str, str]] | None = None) -> None:
        self._fetch = fetch or _fetch_keys
        self._keys: dict[str, str] = {}
        self._loaded_at = 0.0
        self._lock = threading.Lock()

    def keys(self) -> dict[str, str]:
        with self._lock:
            if not self._keys or time.monotonic() - self._loaded_at > KEY_TTL_SECONDS:
                self._keys = self._fetch()
                self._loaded_at = time.monotonic()
            return self._keys


def _fetch_keys() -> dict[str, str]:
    with urllib.request.urlopen(PUBLIC_KEYS_URL, timeout=10) as resp:  # noqa: S310 (fixed https)
        data: dict[str, str] = json.loads(resp.read())
    return data


def verify(token: str | None, audience: str | None, cache: KeyCache) -> dict[str, Any]:
    """Return the verified claims, or raise IapError."""
    if not token:
        raise IapError("missing IAP assertion")
    if not audience:
        raise IapError("IAP audience is not configured")
    try:
        header = jwt.decode_header(token)
    except (ValueError, exceptions.GoogleAuthError) as exc:
        raise IapError("malformed IAP assertion") from exc
    if header.get("alg") != "ES256":
        raise IapError("unexpected signing algorithm")
    try:
        claims: dict[str, Any] = jwt.decode(token, certs=cache.keys(), audience=audience)
    except (ValueError, exceptions.GoogleAuthError) as exc:
        raise IapError(f"IAP assertion rejected: {type(exc).__name__}") from exc
    if claims.get("iss") != IAP_ISSUER:
        raise IapError("unexpected issuer")
    if not claims.get("email"):
        raise IapError("assertion has no email")
    return claims
