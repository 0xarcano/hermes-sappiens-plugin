"""Deterministic CBOR helpers matching sappiens-protocol (RFC 8949 §4.2.1)."""

from __future__ import annotations

from typing import Any, Mapping

import cbor2


def encode(value: Any) -> bytes:
    """Encode with canonical map key ordering."""
    return cbor2.dumps(value, canonical=True)


def decode(data: bytes) -> Any:
    return cbor2.loads(data)


def text_map(entries: Mapping[str, Any] | list[tuple[str, Any]]) -> dict[str, Any]:
    if isinstance(entries, Mapping):
        return dict(entries)
    return dict(entries)
