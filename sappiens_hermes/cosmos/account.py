"""LCD account_number / sequence query."""

from __future__ import annotations

import base64
from dataclasses import dataclass
from typing import Any

import httpx

from sappiens_hermes.errors import BuilderError


@dataclass
class CosmosAccountNumbers:
    account_number: int
    sequence: int
    pubkey_compressed: bytes | None = None


def query_account_numbers(
    lcd_base: str,
    bech32_address: str,
    *,
    timeout: float = 30.0,
    client: httpx.Client | None = None,
) -> CosmosAccountNumbers:
    base = lcd_base.strip().rstrip("/")
    address = bech32_address.strip()
    if not address:
        raise BuilderError("signer bech32 address is required")
    url = f"{base}/cosmos/auth/v1beta1/accounts/{address}"
    owns = client is None
    http = client or httpx.Client(timeout=timeout)
    try:
        resp = http.get(url)
        body = resp.text
        if resp.status_code >= 400:
            raise BuilderError(f"LCD account query HTTP {resp.status_code}: {body}")
        data = resp.json()
    finally:
        if owns:
            http.close()

    account = data.get("account") or {}
    account_number, sequence, pub_key = _extract_fields(account)
    pubkey = _decode_secp256k1_pubkey(pub_key) if pub_key else None
    return CosmosAccountNumbers(
        account_number=account_number,
        sequence=sequence,
        pubkey_compressed=pubkey,
    )


def _extract_fields(account: dict[str, Any]) -> tuple[int, int, dict[str, Any] | None]:
    if isinstance(account.get("value"), dict):
        inner = account["value"]
        return (
            _parse_u64(inner.get("account_number"), "account_number"),
            _parse_u64(inner.get("sequence"), "sequence"),
            inner.get("pub_key"),
        )
    vesting = account.get("base_vesting_account")
    if isinstance(vesting, dict) and isinstance(vesting.get("base_account"), dict):
        inner = vesting["base_account"]
        return (
            _parse_u64(inner.get("account_number"), "account_number"),
            _parse_u64(inner.get("sequence"), "sequence"),
            inner.get("pub_key"),
        )
    return (
        _parse_u64(account.get("account_number"), "account_number"),
        _parse_u64(account.get("sequence"), "sequence"),
        account.get("pub_key"),
    )


def _parse_u64(value: Any, field: str) -> int:
    if value is None:
        raise BuilderError(f"LCD account missing {field}")
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise BuilderError(f"LCD {field} is not an integer") from exc


def _decode_secp256k1_pubkey(pub_key: dict[str, Any]) -> bytes | None:
    key_b64 = pub_key.get("key")
    if not key_b64:
        return None
    # LCD uses standard base64 for pubkey key field.
    pad = "=" * (-len(key_b64) % 4)
    raw = base64.b64decode(key_b64 + pad)
    if len(raw) != 33:
        return None
    return raw


def parse_pubkey_hex(pubkey_hex: str | None) -> bytes | None:
    if not pubkey_hex:
        return None
    cleaned = pubkey_hex.strip()
    if cleaned.startswith("secp256k1:"):
        cleaned = cleaned[len("secp256k1:") :]
    raw = bytes.fromhex(cleaned)
    if len(raw) != 33:
        raise BuilderError("pubkey must be 33-byte compressed secp256k1 hex")
    return raw
