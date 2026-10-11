"""Seal dual-presentation proposals and submit to the relay."""

from __future__ import annotations

from typing import Any

from sappiens_hermes.envelope import Envelope
from sappiens_hermes.identity import AgentIdentity
from sappiens_hermes.presentation import ProposalDocument, ProposalPresentation
from sappiens_hermes.relay import RelayClient
from sappiens_hermes.store import StateStore


def seal_and_submit(
    *,
    identity: AgentIdentity,
    store: StateStore,
    relay: RelayClient,
    presentation: ProposalPresentation,
    summary: str,
    body: dict[str, Any] | None = None,
) -> dict[str, Any]:
    state = store.load()
    auth = state.latest_authorization()
    channel_key = state.channel_key_bytes()

    doc = ProposalDocument.new(
        summary=summary[:120],
        body=body or {},
        presentation=presentation,
    )
    envelope = Envelope.seal(
        channel_key=channel_key,
        identity=identity,
        authorization_id=auth.authorization_id,
        agent_id=identity.agent_id,
        plaintext=doc.to_cbor(),
    )
    receipt = relay.submit_envelope(envelope)
    state.last_proposal_id = doc.proposal_id
    state.last_envelope_id = envelope.envelope_id
    store.save(state)
    return {
        "ok": True,
        "proposal_id": doc.proposal_id,
        "envelope_id": envelope.envelope_id,
        "authorization_id": auth.authorization_id,
        "summary": doc.summary,
        "chain": presentation.technical.chain,
        "destination": presentation.technical.destination,
        "payload_fields": presentation.technical.payload_fields,
        "sign_payload_len": len(presentation.technical.sign_payload),
        "relay_receipt": receipt,
        "note": (
            "Sealed proposal queued on the relay. The person must open Sappiens, "
            "review dual presentation, Approve, and sign on device. "
            "The wallet broadcasts; this agent does not submit the signed tx."
        ),
    }


def propose_raw(
    *,
    identity: AgentIdentity,
    store: StateStore,
    relay: RelayClient,
    summary: str,
    human: dict[str, str],
    technical: dict[str, Any],
    sign_payload: bytes,
    body: dict[str, Any] | None = None,
) -> dict[str, Any]:
    from sappiens_hermes.presentation import HumanReadableView, TechnicalView

    presentation = ProposalPresentation(
        human=HumanReadableView(
            action=str(human["action"]),
            assets=str(human["assets"]),
            amounts=str(human["amounts"]),
            counterparties=str(human["counterparties"]),
            chain=str(human["chain"]),
        ),
        technical=TechnicalView(
            chain=str(technical["chain"]),
            destination=str(technical["destination"]),
            payload_fields=dict(technical.get("payload_fields") or {"raw": "true"}),
            sign_payload=sign_payload,
        ),
    )
    return seal_and_submit(
        identity=identity,
        store=store,
        relay=relay,
        presentation=presentation,
        summary=summary,
        body=body,
    )
