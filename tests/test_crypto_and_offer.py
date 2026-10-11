"""Protocol crypto + offer CBOR tests."""

from __future__ import annotations

from datetime import datetime, timezone

from sappiens_hermes import b64
from sappiens_hermes.crypto import (
    X25519KeyPair,
    aead_decrypt,
    aead_encrypt,
    derive_channel_key,
    random_nonce,
    revoke_commitment,
    revoke_mac,
)
from sappiens_hermes.envelope import Envelope
from sappiens_hermes.identity import AgentIdentity, derive_agent_id
from sappiens_hermes.offer import RegistrationOffer
from sappiens_hermes.presentation import (
    HumanReadableView,
    ProposalDocument,
    ProposalPresentation,
    TechnicalView,
)


def test_both_sides_derive_same_channel_key():
    wallet = X25519KeyPair.from_private_bytes(bytes([1] * 32))
    agent = X25519KeyPair.from_private_bytes(bytes([2] * 32))
    assert derive_channel_key(wallet.private_key, agent.public_bytes) == derive_channel_key(
        agent.private_key, wallet.public_bytes
    )


def test_low_order_peer_rejected():
    secret = X25519KeyPair.from_private_bytes(bytes([1] * 32))
    try:
        derive_channel_key(secret.private_key, bytes(32))
        assert False, "expected ProtocolError"
    except Exception as exc:
        assert "weak" in str(exc).lower() or "low-order" in str(exc).lower()


def test_offer_uri_round_trip():
    identity = AgentIdentity.from_seed(bytes([3] * 32))
    offer = RegistrationOffer.new_signed(
        identity=identity,
        x25519_pubkey=bytes([4] * 32),
        display_name="Test Agent",
        relay_base_url="http://127.0.0.1:8080",
        issued_at=datetime.now(timezone.utc),
    )
    offer.validate()
    uri = offer.to_uri()
    assert uri.startswith("sappiens://v1/register?offer=")
    payload = uri.split("offer=", 1)[1]
    parsed = RegistrationOffer.from_cbor(b64.decode(payload))
    assert parsed.offer_id == offer.offer_id
    assert parsed.agent_id == derive_agent_id(identity.public_bytes)
    assert parsed.signature == offer.signature


def test_envelope_seal_open_roundtrip():
    identity = AgentIdentity.from_seed(bytes([5] * 32))
    key = bytes([9] * 32)
    env = Envelope.seal(
        channel_key=key,
        identity=identity,
        authorization_id="00000000-0000-4000-8000-000000000001",
        agent_id=identity.agent_id,
        plaintext=b"proposal-bytes",
        envelope_id="00000000-0000-4000-8000-000000000002",
    )
    env.verify_sender(identity.public_bytes)
    assert env.open(key) == b"proposal-bytes"
    wire = env.to_json()
    back = Envelope.from_json(wire)
    assert back.open(key) == b"proposal-bytes"


def test_aead_aad_binds_ids():
    key = bytes([1] * 32)
    nonce = random_nonce()
    ct = aead_encrypt(key, nonce, b"hi", b"auth" + b"env")
    assert aead_decrypt(key, nonce, ct, b"auth" + b"env") == b"hi"
    try:
        aead_decrypt(key, nonce, ct, b"auth" + b"OTHER")
        assert False
    except Exception:
        pass


def test_revoke_commitment_stable():
    mac = revoke_mac(bytes([9] * 32), "00000000-0000-4000-8000-000000000000")
    assert revoke_commitment(mac) == revoke_commitment(mac)


def test_proposal_document_cbor_with_presentation():
    presentation = ProposalPresentation(
        human=HumanReadableView(
            action="Send tokens",
            assets="NYM",
            amounts="1 NYM",
            counterparties="n1to",
            chain="Nyx (Nym)",
        ),
        technical=TechnicalView(
            chain="nyx",
            destination="n1to",
            payload_fields={"amount": "1000000", "denom": "unym"},
            sign_payload=b"sign-doc-bytes",
        ),
    )
    doc = ProposalDocument.new("Send 1 NYM", {}, presentation)
    raw = doc.to_cbor()
    assert b"nyx" in raw
    assert b"sign-doc-bytes" in raw
