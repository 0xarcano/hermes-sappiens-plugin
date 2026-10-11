"""Channel key agreement and envelope AEAD (handshake.md + envelopes.md)."""

from __future__ import annotations

import hashlib
import hmac
import os
from dataclasses import dataclass

from cryptography.hazmat.primitives.asymmetric.x25519 import (
    X25519PrivateKey,
    X25519PublicKey,
)
from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes

from sappiens_hermes.errors import ProtocolError

CHANNEL_INFO = b"sappiens/v1/channel"
NONCE_LEN = 12


@dataclass
class X25519KeyPair:
    private_key: X25519PrivateKey

    @classmethod
    def generate(cls) -> X25519KeyPair:
        return cls(X25519PrivateKey.generate())

    @classmethod
    def from_private_bytes(cls, raw: bytes) -> X25519KeyPair:
        if len(raw) != 32:
            raise ProtocolError("X25519 private key must be 32 bytes")
        return cls(X25519PrivateKey.from_private_bytes(raw))

    @property
    def private_bytes(self) -> bytes:
        return self.private_key.private_bytes_raw()

    @property
    def public_bytes(self) -> bytes:
        return self.private_key.public_key().public_bytes_raw()


def derive_channel_key(secret: X25519PrivateKey, peer_public: bytes) -> bytes:
    """HKDF-SHA256(ikm=ECDH, salt=None → 32 zero bytes, info=CHANNEL_INFO, L=32)."""
    if len(peer_public) != 32:
        raise ProtocolError("peer X25519 public key must be 32 bytes")
    if peer_public == b"\x00" * 32:
        raise ProtocolError("weak key agreement: low-order peer public key")
    peer = X25519PublicKey.from_public_bytes(peer_public)
    shared = secret.exchange(peer)
    if shared == b"\x00" * 32:
        raise ProtocolError("weak key agreement: non-contributory ECDH")
    return HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=None,
        info=CHANNEL_INFO,
    ).derive(shared)


def revoke_mac(channel_key: bytes, offer_id: str) -> bytes:
    mac = hmac.new(channel_key, digestmod=hashlib.sha256)
    mac.update(b"revoke|")
    mac.update(offer_id.encode("utf-8"))
    return mac.digest()


def revoke_commitment(mac: bytes) -> bytes:
    return hashlib.sha256(mac).digest()


def aead_encrypt(channel_key: bytes, nonce: bytes, plaintext: bytes, aad: bytes) -> bytes:
    if len(nonce) != NONCE_LEN:
        raise ProtocolError("nonce must be 12 bytes")
    return ChaCha20Poly1305(channel_key).encrypt(nonce, plaintext, aad)


def aead_decrypt(channel_key: bytes, nonce: bytes, ciphertext: bytes, aad: bytes) -> bytes:
    if len(nonce) != NONCE_LEN:
        raise ProtocolError("nonce must be 12 bytes")
    try:
        return ChaCha20Poly1305(channel_key).decrypt(nonce, ciphertext, aad)
    except Exception as exc:  # noqa: BLE001
        raise ProtocolError("decrypt failed") from exc


def random_nonce() -> bytes:
    return os.urandom(NONCE_LEN)


def sha256(data: bytes) -> bytes:
    return hashlib.sha256(data).digest()
