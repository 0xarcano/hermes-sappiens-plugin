"""RegistrationOffer CBOR + URI (registration-qr.md)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

from sappiens_hermes import b64, cbor_util
from sappiens_hermes.errors import ProtocolError
from sappiens_hermes.identity import AgentIdentity, derive_agent_id

SCHEMA_VERSION = "1"
URI_BASE = "sappiens://v1/register"
DEFAULT_TTL_MINUTES = 10
MAX_DISPLAY_NAME_CHARS = 64


def format_timestamp(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_timestamp(text: str, field: str = "timestamp") -> datetime:
    try:
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        return datetime.fromisoformat(text).astimezone(timezone.utc)
    except ValueError as exc:
        raise ProtocolError(f"{field} is not RFC 3339") from exc


@dataclass
class RegistrationOffer:
    schema_version: str
    offer_id: str
    agent_id: str
    display_name: str
    identity_pubkey: bytes
    x25519_pubkey: bytes
    relay_base_url: str
    issued_at: str
    expires_at: str
    signature: bytes

    def unsigned_map(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "offer_id": self.offer_id,
            "agent_id": self.agent_id,
            "display_name": self.display_name,
            "identity_pubkey": self.identity_pubkey,
            "x25519_pubkey": self.x25519_pubkey,
            "relay_base_url": self.relay_base_url,
            "issued_at": self.issued_at,
            "expires_at": self.expires_at,
        }

    def unsigned_cbor(self) -> bytes:
        return cbor_util.encode(self.unsigned_map())

    def to_cbor(self) -> bytes:
        data = self.unsigned_map()
        data["signature"] = self.signature
        return cbor_util.encode(data)

    def to_uri(self) -> str:
        return f"{URI_BASE}?offer={b64.encode(self.to_cbor())}"

    def to_create_offer_json(self) -> dict[str, str]:
        return {
            "offer_id": self.offer_id,
            "agent_id": self.agent_id,
            "display_name": self.display_name,
            "identity_pubkey": b64.encode(self.identity_pubkey),
            "x25519_pubkey": b64.encode(self.x25519_pubkey),
            "issued_at": self.issued_at,
            "expires_at": self.expires_at,
            "signature": b64.encode(self.signature),
        }

    @classmethod
    def new_signed(
        cls,
        *,
        identity: AgentIdentity,
        x25519_pubkey: bytes,
        display_name: str,
        relay_base_url: str,
        issued_at: datetime | None = None,
        ttl_minutes: int = DEFAULT_TTL_MINUTES,
    ) -> RegistrationOffer:
        now = issued_at or datetime.now(timezone.utc)
        name = display_name.strip()
        if not name or len(name) > MAX_DISPLAY_NAME_CHARS:
            raise ProtocolError("display_name must be 1-64 characters")
        relay = relay_base_url.rstrip("/")
        validate_relay_base_url(relay)
        if len(x25519_pubkey) != 32:
            raise ProtocolError("x25519_pubkey must be 32 bytes")
        offer = cls(
            schema_version=SCHEMA_VERSION,
            offer_id=str(uuid4()),
            agent_id=identity.agent_id,
            display_name=name,
            identity_pubkey=identity.public_bytes,
            x25519_pubkey=x25519_pubkey,
            relay_base_url=relay,
            issued_at=format_timestamp(now),
            expires_at=format_timestamp(now + timedelta(minutes=ttl_minutes)),
            signature=b"\x00" * 64,
        )
        offer.signature = identity.sign(offer.unsigned_cbor())
        return offer

    @classmethod
    def from_cbor(cls, data: bytes) -> RegistrationOffer:
        obj = cbor_util.decode(data)
        if not isinstance(obj, dict):
            raise ProtocolError("offer CBOR must be a map")
        required = [
            "schema_version",
            "offer_id",
            "agent_id",
            "display_name",
            "identity_pubkey",
            "x25519_pubkey",
            "relay_base_url",
            "issued_at",
            "expires_at",
            "signature",
        ]
        for key in obj:
            if key not in required:
                raise ProtocolError(f"unknown offer field: {key}")
        for key in required:
            if key not in obj:
                raise ProtocolError(f"missing offer field: {key}")
        return cls(
            schema_version=str(obj["schema_version"]),
            offer_id=str(obj["offer_id"]),
            agent_id=str(obj["agent_id"]),
            display_name=str(obj["display_name"]),
            identity_pubkey=bytes(obj["identity_pubkey"]),
            x25519_pubkey=bytes(obj["x25519_pubkey"]),
            relay_base_url=str(obj["relay_base_url"]),
            issued_at=str(obj["issued_at"]),
            expires_at=str(obj["expires_at"]),
            signature=bytes(obj["signature"]),
        )

    def validate(self, now: datetime | None = None) -> None:
        now = now or datetime.now(timezone.utc)
        if self.schema_version != SCHEMA_VERSION:
            raise ProtocolError(f"unsupported schema_version: {self.schema_version}")
        if self.agent_id != derive_agent_id(self.identity_pubkey):
            raise ProtocolError("agent_id mismatch")
        validate_relay_base_url(self.relay_base_url)
        issued = parse_timestamp(self.issued_at, "issued_at")
        expires = parse_timestamp(self.expires_at, "expires_at")
        if issued > expires:
            raise ProtocolError("issued_at after expires_at")
        if expires <= now:
            raise ProtocolError("offer expired")
        from sappiens_hermes.identity import verify

        verify(self.identity_pubkey, self.unsigned_cbor(), self.signature)


def validate_relay_base_url(url: str) -> None:
    if url.endswith("/"):
        raise ProtocolError("relay_base_url must not end with /")
    if "://" not in url:
        raise ProtocolError("relay_base_url missing scheme")
    scheme, authority = url.split("://", 1)
    if any(c in authority for c in "/?#"):
        raise ProtocolError("relay_base_url must be an origin without path")
    host = authority
    if ":" in authority:
        host_part, port = authority.rsplit(":", 1)
        if port.isdigit():
            host = host_part
    if not host:
        raise ProtocolError("relay_base_url missing host")
    if scheme == "https":
        return
    if scheme == "http" and host in ("localhost", "127.0.0.1", "[::1]", "10.0.2.2"):
        return
    raise ProtocolError("relay_base_url must be https (http only for loopback)")
