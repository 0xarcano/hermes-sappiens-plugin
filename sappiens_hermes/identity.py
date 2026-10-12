"""Agent Ed25519 identity and agent_id derivation."""

from __future__ import annotations

import os
from dataclasses import dataclass

from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

from sappiens_hermes import b64
from sappiens_hermes.errors import ConfigError

AGENT_ID_PREFIX = "ed25519:"
SEED_ENV = "SAPPIENS_AGENT_ED25519_SEED"


@dataclass(frozen=True)
class AgentIdentity:
    private_key: Ed25519PrivateKey

    @property
    def public_bytes(self) -> bytes:
        return self.private_key.public_key().public_bytes_raw()

    @property
    def agent_id(self) -> str:
        return derive_agent_id(self.public_bytes)

    def sign(self, message: bytes) -> bytes:
        return self.private_key.sign(message)

    @classmethod
    def from_seed(cls, seed: bytes) -> AgentIdentity:
        if len(seed) != 32:
            raise ConfigError("Ed25519 seed must be 32 bytes")
        return cls(Ed25519PrivateKey.from_private_bytes(seed))

    @classmethod
    def from_env(cls, env: dict[str, str] | None = None) -> AgentIdentity:
        source = env if env is not None else dict(os.environ)
        raw = source.get(SEED_ENV, "").strip()
        if not raw:
            raise ConfigError(
                f"Set {SEED_ENV} to a base64url-no-pad 32-byte Ed25519 seed"
            )
        try:
            seed = b64.decode(raw)
        except Exception as exc:  # noqa: BLE001
            raise ConfigError(f"{SEED_ENV} is not valid base64url") from exc
        return cls.from_seed(seed)

    @classmethod
    def generate(cls) -> AgentIdentity:
        return cls(Ed25519PrivateKey.generate())


def derive_agent_id(identity_pubkey: bytes) -> str:
    if len(identity_pubkey) != 32:
        raise ConfigError("identity pubkey must be 32 bytes")
    return f"{AGENT_ID_PREFIX}{b64.encode(identity_pubkey)}"


def fingerprint(identity_pubkey: bytes) -> str:
    return f"{identity_pubkey[:4].hex()}…{identity_pubkey[-4:].hex()}"


def verify(identity_pubkey: bytes, message: bytes, signature: bytes) -> None:
    key = Ed25519PublicKey.from_public_bytes(identity_pubkey)
    key.verify(signature, message)
