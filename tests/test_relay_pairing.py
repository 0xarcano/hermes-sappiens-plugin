"""Mocked relay pairing + propose flow."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import httpx
import respx

from sappiens_hermes import b64
from sappiens_hermes.config import Settings
from sappiens_hermes.builders import nyx as nyx_builder
from sappiens_hermes.cosmos.account import CosmosAccountNumbers
from sappiens_hermes.crypto import X25519KeyPair
from sappiens_hermes.identity import AgentIdentity
from sappiens_hermes.pairing import create_offer, wait_for_registration
from sappiens_hermes.propose import seal_and_submit
from sappiens_hermes.relay import RelayClient
from sappiens_hermes.skill_loader import SkillRegistry
from sappiens_hermes.store import AgentState, StateStore, StoredAuthorization


def test_create_offer_and_wait_handshake(tmp_path: Path):
    identity = AgentIdentity.from_seed(bytes([11] * 32))
    settings = Settings(
        relay_url="http://relay.test",
        advertise_relay="http://127.0.0.1:8080",
        state_path=tmp_path / "state.json",
        poll_interval_seconds=0.01,
    )
    store = StateStore(settings.state_path)
    wallet = X25519KeyPair.generate()

    with respx.mock(assert_all_called=False) as router:
        create_route = router.post("http://relay.test/v1/offers").mock(
            return_value=httpx.Response(201, json={"offer_id": "x", "status": "pending"})
        )

        result = create_offer(
            identity=identity,
            settings=settings,
            store=store,
            wait=False,
        )
        assert result["ok"]
        assert result["uri"].startswith("sappiens://v1/register?offer=")
        assert create_route.called

        state = store.load()
        offer_id = state.pending_offer.offer_id
        assert offer_id

        # Simulate wallet confirm: getOffer returns consumed + wallet pubkey
        router.get(f"http://relay.test/v1/offers/{offer_id}").mock(
            return_value=httpx.Response(
                200,
                json={
                    "offer_id": offer_id,
                    "status": "consumed",
                    "authorization_id": "11111111-1111-4111-8111-111111111111",
                    "wallet_x25519_pubkey": b64.encode(wallet.public_bytes),
                },
            )
        )
        auth = wait_for_registration(
            identity=identity, settings=settings, store=store
        )
        assert auth.authorization_id == "11111111-1111-4111-8111-111111111111"
        ck = b64.decode(auth.channel_key)
        assert len(ck) == 32
        assert store.load().pending_offer is None


def test_seal_and_submit_after_pair(tmp_path: Path):
    identity = AgentIdentity.from_seed(bytes([12] * 32))
    settings = Settings(
        relay_url="http://relay.test",
        state_path=tmp_path / "state.json",
    )
    store = StateStore(settings.state_path)
    channel_key = bytes([7] * 32)
    store.save(
        AgentState(
            display_name="t",
            authorizations=[
                StoredAuthorization(
                    authorization_id="22222222-2222-4222-8222-222222222222",
                    offer_id="33333333-3333-4333-8333-333333333333",
                    channel_key=b64.encode(channel_key),
                )
            ],
        )
    )

    skill = SkillRegistry().get("nyx")
    account = CosmosAccountNumbers(1, 0)
    with patch(
        "sappiens_hermes.builders.nyx.query_account_numbers", return_value=account
    ):
        presentation = nyx_builder.send_tokens(
            skill,
            {
                "from_address": "n1fromaddressxxxxxxxxxxxxxxxxxxxxxxxxxxx",
                "to_address": "n1toaddressyyyyyyyyyyyyyyyyyyyyyyyyyyyy",
                "amount": "1000",
            },
        )

    with respx.mock:
        route = respx.post("http://relay.test/v1/envelopes").mock(
            return_value=httpx.Response(
                202,
                json={
                    "envelope_id": "44444444-4444-4444-8444-444444444444",
                    "delivery_state": "queued",
                },
            )
        )
        relay = RelayClient("http://relay.test")
        try:
            result = seal_and_submit(
                identity=identity,
                store=store,
                relay=relay,
                presentation=presentation,
                summary="Send test",
            )
        finally:
            relay.close()
        assert result["ok"]
        assert route.called
        body = json.loads(route.calls.last.request.content)
        assert body["schema_version"] == "1"
        assert body["authorization_id"] == "22222222-2222-4222-8222-222222222222"
        assert "ciphertext" in body
        assert "sender_auth" in body


def test_submit_envelope_403():
    identity = AgentIdentity.from_seed(bytes([13] * 32))
    env_mock = MagicMock()
    env_mock.to_json.return_value = {
        "schema_version": "1",
        "envelope_id": "55555555-5555-4555-8555-555555555555",
        "authorization_id": "66666666-6666-4666-8666-666666666666",
        "agent_id": identity.agent_id,
        "created_at": "2026-01-01T00:00:00Z",
        "nonce": b64.encode(bytes(12)),
        "ciphertext": b64.encode(b"x" * 20),
        "sender_auth": b64.encode(bytes(64)),
    }
    with respx.mock:
        respx.post("http://relay.test/v1/envelopes").mock(
            return_value=httpx.Response(403, text="revoked")
        )
        relay = RelayClient("http://relay.test")
        try:
            try:
                relay.submit_envelope(env_mock)
                assert False, "expected RelayError"
            except Exception as exc:
                assert "403" in str(exc) or getattr(exc, "status", None) == 403
        finally:
            relay.close()
