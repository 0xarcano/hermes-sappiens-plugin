"""Sealed proposal envelopes (envelopes.md)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from sappiens_hermes import b64
from sappiens_hermes.crypto import aead_decrypt, aead_encrypt, random_nonce, sha256
from sappiens_hermes.errors import ProtocolError
from sappiens_hermes.identity import AgentIdentity, verify
from sappiens_hermes.offer import format_timestamp

SCHEMA_VERSION = "1"
NONCE_LEN = 12


def _aad(authorization_id: str, envelope_id: str) -> bytes:
    return authorization_id.encode("utf-8") + envelope_id.encode("utf-8")


@dataclass
class Envelope:
    schema_version: str
    envelope_id: str
    authorization_id: str
    agent_id: str
    created_at: str
    nonce: bytes
    ciphertext: bytes
    sender_auth: bytes

    def metadata_hash(self) -> bytes:
        data = (
            self.schema_version.encode("utf-8")
            + self.envelope_id.encode("utf-8")
            + self.authorization_id.encode("utf-8")
            + self.agent_id.encode("utf-8")
            + self.created_at.encode("utf-8")
            + self.nonce
            + self.ciphertext
        )
        return sha256(data)

    def to_json(self) -> dict[str, str]:
        return {
            "schema_version": self.schema_version,
            "envelope_id": self.envelope_id,
            "authorization_id": self.authorization_id,
            "agent_id": self.agent_id,
            "created_at": self.created_at,
            "nonce": b64.encode(self.nonce),
            "ciphertext": b64.encode(self.ciphertext),
            "sender_auth": b64.encode(self.sender_auth),
        }

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> Envelope:
        return cls(
            schema_version=str(data["schema_version"]),
            envelope_id=str(data["envelope_id"]),
            authorization_id=str(data["authorization_id"]),
            agent_id=str(data["agent_id"]),
            created_at=str(data["created_at"]),
            nonce=b64.decode(str(data["nonce"])),
            ciphertext=b64.decode(str(data["ciphertext"])),
            sender_auth=b64.decode(str(data["sender_auth"])),
        )

    def verify_sender(self, identity_pubkey: bytes) -> None:
        if len(self.sender_auth) != 64:
            raise ProtocolError("sender_auth must be 64 bytes")
        verify(identity_pubkey, self.metadata_hash(), self.sender_auth)

    def open(self, channel_key: bytes) -> bytes:
        return aead_decrypt(
            channel_key,
            self.nonce,
            self.ciphertext,
            _aad(self.authorization_id, self.envelope_id),
        )

    @classmethod
    def seal(
        cls,
        *,
        channel_key: bytes,
        identity: AgentIdentity,
        authorization_id: str | UUID,
        agent_id: str,
        plaintext: bytes,
        envelope_id: str | UUID | None = None,
        created_at: datetime | None = None,
    ) -> Envelope:
        eid = str(envelope_id or uuid4())
        aid = str(authorization_id)
        # Canonical lowercase UUID form required by contract.
        UUID(eid)
        UUID(aid)
        if eid != eid.lower() or aid != aid.lower():
            raise ProtocolError("UUIDs must be lowercase hyphenated")
        nonce = random_nonce()
        ciphertext = aead_encrypt(
            channel_key,
            nonce,
            plaintext,
            _aad(aid, eid),
        )
        env = cls(
            schema_version=SCHEMA_VERSION,
            envelope_id=eid,
            authorization_id=aid,
            agent_id=agent_id,
            created_at=format_timestamp(created_at or datetime.now(timezone.utc)),
            nonce=nonce,
            ciphertext=ciphertext,
            sender_auth=b"",
        )
        env.sender_auth = identity.sign(env.metadata_hash())
        return env
