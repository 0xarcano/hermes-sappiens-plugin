"""Registration offer mint + handshake wait."""

from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any

from sappiens_hermes import b64
from sappiens_hermes.config import Settings
from sappiens_hermes.crypto import X25519KeyPair, derive_channel_key
from sappiens_hermes.errors import ProtocolError
from sappiens_hermes.identity import AgentIdentity
from sappiens_hermes.offer import RegistrationOffer, parse_timestamp
from sappiens_hermes.relay import RelayClient
from sappiens_hermes.store import PendingOffer, StateStore, StoredAuthorization


def create_offer(
    *,
    identity: AgentIdentity,
    settings: Settings,
    store: StateStore,
    relay: RelayClient | None = None,
    display_name: str | None = None,
    wait: bool = False,
) -> dict[str, Any]:
    state = store.load()
    name = (display_name or settings.display_name).strip()
    state.display_name = name
    x25519 = X25519KeyPair.generate()
    offer = RegistrationOffer.new_signed(
        identity=identity,
        x25519_pubkey=x25519.public_bytes,
        display_name=name,
        relay_base_url=settings.advertise_url,
        ttl_minutes=settings.offer_ttl_minutes,
    )
    offer.validate()
    client = relay or RelayClient(
        settings.relay_url, timeout=settings.command_timeout
    )
    try:
        client.create_offer(offer)
    finally:
        if relay is None:
            client.close()

    state.pending_offer = PendingOffer(
        offer_id=offer.offer_id,
        x25519_secret=b64.encode(x25519.private_bytes),
        expires_at=offer.expires_at,
    )
    store.save(state)

    result: dict[str, Any] = {
        "ok": True,
        "offer_id": offer.offer_id,
        "agent_id": offer.agent_id,
        "display_name": offer.display_name,
        "expires_at": offer.expires_at,
        "relay": settings.relay_url.rstrip("/"),
        "advertise_relay": settings.advertise_url,
        "uri": offer.to_uri(),
        "instruction": (
            "Show this URI as a QR in the Sappiens wallet scanner "
            "(Plugins / Agents → Register). Scan and confirm on the phone."
        ),
    }
    if wait:
        auth = wait_for_registration(
            identity=identity,
            settings=settings,
            store=store,
            relay=relay,
        )
        result["authorization"] = {
            "authorization_id": auth.authorization_id,
            "offer_id": auth.offer_id,
        }
        result["paired"] = True
    else:
        result["paired"] = False
        result["next"] = (
            "After the wallet confirms, call sappiens_pair with wait=true "
            "(or wait=true on this call) to finish the handshake."
        )
    return result


def wait_for_registration(
    *,
    identity: AgentIdentity,
    settings: Settings,
    store: StateStore,
    relay: RelayClient | None = None,
) -> StoredAuthorization:
    del identity  # identity not needed for wait; channel uses pending x25519
    state = store.load()
    pending = state.pending_offer
    if pending is None:
        raise ProtocolError("no pending offer; run sappiens_pair first")
    expires_at = parse_timestamp(pending.expires_at, "expires_at")
    client = relay or RelayClient(
        settings.relay_url, timeout=settings.command_timeout
    )
    try:
        while True:
            status = client.get_offer(pending.offer_id)
            st = status.get("status")
            if st == "consumed":
                break
            if st == "declined":
                raise ProtocolError("the wallet declined the offer")
            if st == "expired":
                raise ProtocolError("the offer expired before the wallet confirmed")
            if st == "pending" and datetime.now(timezone.utc) >= expires_at:
                raise ProtocolError("the offer expired before the wallet confirmed")
            if st != "pending":
                raise ProtocolError(f"unexpected offer status: {st}")
            time.sleep(settings.poll_interval_seconds)
    finally:
        if relay is None:
            client.close()

    authorization_id = status.get("authorization_id")
    wallet_pub_b64 = status.get("wallet_x25519_pubkey")
    if not authorization_id or not wallet_pub_b64:
        raise ProtocolError("consumed offer missing authorization_id or wallet pubkey")

    wallet_pub = b64.decode_fixed(str(wallet_pub_b64), 32, "wallet_x25519_pubkey")
    secret = X25519KeyPair.from_private_bytes(
        b64.decode_fixed(pending.x25519_secret, 32, "x25519_secret")
    )
    channel_key = derive_channel_key(secret.private_key, wallet_pub)
    stored = StoredAuthorization(
        authorization_id=str(authorization_id),
        offer_id=pending.offer_id,
        channel_key=b64.encode(channel_key),
        wallet_x25519_pubkey=str(wallet_pub_b64),
    )
    state.pending_offer = None
    state.authorizations.append(stored)
    store.save(state)
    return stored


def status_snapshot(
    *,
    identity: AgentIdentity,
    settings: Settings,
    store: StateStore,
    skills_summary: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    state = store.load()
    paired = bool(state.authorizations)
    auth = state.authorizations[-1] if paired else None
    return {
        "ok": True,
        "agent_id": identity.agent_id,
        "display_name": state.display_name,
        "relay": settings.relay_url.rstrip("/"),
        "paired": paired,
        "pending_offer_id": state.pending_offer.offer_id if state.pending_offer else None,
        "authorization_id": auth.authorization_id if auth else None,
        "last_proposal_id": state.last_proposal_id,
        "last_envelope_id": state.last_envelope_id,
        "skills": skills_summary or [],
        "seed_configured": True,
    }
