"""base64url without padding (Sappiens contract v1)."""

from __future__ import annotations

import base64


def encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def decode(text: str) -> bytes:
    pad = "=" * (-len(text) % 4)
    return base64.urlsafe_b64decode(text + pad)


def decode_fixed(text: str, size: int, field: str = "bytes") -> bytes:
    raw = decode(text)
    if len(raw) != size:
        raise ValueError(f"{field} must be {size} bytes, got {len(raw)}")
    return raw
