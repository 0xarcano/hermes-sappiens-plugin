"""Hermes tool handlers."""

from __future__ import annotations

import json
import logging
from typing import Any

from sappiens_hermes import b64
from sappiens_hermes.config import Settings
from sappiens_hermes.errors import SappiensError
from sappiens_hermes.identity import AgentIdentity
from sappiens_hermes.pairing import create_offer, status_snapshot, wait_for_registration
from sappiens_hermes.propose import propose_raw, seal_and_submit
from sappiens_hermes.relay import RelayClient
from sappiens_hermes.skill_loader import SkillRegistry
from sappiens_hermes.store import store_from_settings

logger = logging.getLogger(__name__)

_WRITE_TOOLS = frozenset(
    {"sappiens_send", "sappiens_claim_rewards", "sappiens_propose_raw"}
)


def _settings() -> Settings:
    return Settings.from_env()


def _identity() -> AgentIdentity:
    return AgentIdentity.from_env()


def _skills() -> SkillRegistry:
    return SkillRegistry()


def _json(data: Any) -> str:
    return json.dumps(data, indent=2, default=str)


def _err(exc: BaseException) -> str:
    return _json({"ok": False, "error": f"{type(exc).__name__}: {exc}"})


def sappiens_pair(params: dict[str, Any] | None = None) -> str:
    params = params or {}
    try:
        settings = _settings()
        store = store_from_settings(settings)
        identity = _identity()
        wait = bool(params.get("wait"))
        # If there is already a pending offer and wait requested, finish handshake.
        state = store.load()
        if wait and state.pending_offer and not params.get("display_name"):
            auth = wait_for_registration(
                identity=identity, settings=settings, store=store
            )
            return _json(
                {
                    "ok": True,
                    "paired": True,
                    "authorization_id": auth.authorization_id,
                    "offer_id": auth.offer_id,
                    "note": "Handshake complete; channel key stored.",
                }
            )
        result = create_offer(
            identity=identity,
            settings=settings,
            store=store,
            display_name=params.get("display_name"),
            wait=wait,
        )
        return _json(result)
    except Exception as exc:  # noqa: BLE001
        logger.exception("sappiens_pair failed")
        return _err(exc)


def sappiens_status(params: dict[str, Any] | None = None) -> str:
    del params
    try:
        settings = _settings()
        store = store_from_settings(settings)
        identity = _identity()
        skills = [s.summary() for s in _skills().list()]
        return _json(
            status_snapshot(
                identity=identity,
                settings=settings,
                store=store,
                skills_summary=skills,
            )
        )
    except Exception as exc:  # noqa: BLE001
        return _err(exc)


def sappiens_skills(params: dict[str, Any] | None = None) -> str:
    params = params or {}
    try:
        reg = _skills()
        name = (params.get("name") or "").strip()
        if name:
            skill = reg.get(name)
            return _json(
                {
                    "ok": True,
                    "skill": skill.summary(),
                    "operations": skill.operations,
                    "skill_md": str(skill.skill_md),
                }
            )
        return _json({"ok": True, "skills": [s.summary() for s in reg.list()]})
    except Exception as exc:  # noqa: BLE001
        return _err(exc)


def sappiens_send(params: dict[str, Any] | None = None) -> str:
    params = params or {}
    try:
        settings = _settings()
        store = store_from_settings(settings)
        identity = _identity()
        skill_name = str(params.get("skill") or "nyx")
        skill = _skills().get(skill_name)
        presentation = skill.run("send_tokens", params)
        summary = str(params.get("summary") or presentation.human.action)[:120]
        relay = RelayClient(settings.relay_url, timeout=settings.command_timeout)
        try:
            result = seal_and_submit(
                identity=identity,
                store=store,
                relay=relay,
                presentation=presentation,
                summary=summary,
                body={"skill": skill_name, "operation": "send_tokens"},
            )
        finally:
            relay.close()
        return _json(result)
    except Exception as exc:  # noqa: BLE001
        logger.exception("sappiens_send failed")
        return _err(exc)


def sappiens_claim_rewards(params: dict[str, Any] | None = None) -> str:
    params = params or {}
    try:
        settings = _settings()
        store = store_from_settings(settings)
        identity = _identity()
        skill_name = str(params.get("skill") or "nyx")
        skill = _skills().get(skill_name)
        presentation = skill.run("claim_node_rewards", params)
        summary = str(params.get("summary") or presentation.human.action)[:120]
        relay = RelayClient(settings.relay_url, timeout=settings.command_timeout)
        try:
            result = seal_and_submit(
                identity=identity,
                store=store,
                relay=relay,
                presentation=presentation,
                summary=summary,
                body={"skill": skill_name, "operation": "claim_node_rewards"},
            )
        finally:
            relay.close()
        return _json(result)
    except Exception as exc:  # noqa: BLE001
        logger.exception("sappiens_claim_rewards failed")
        return _err(exc)


def sappiens_propose_raw(params: dict[str, Any] | None = None) -> str:
    params = params or {}
    try:
        settings = _settings()
        store = store_from_settings(settings)
        identity = _identity()
        sign_payload = b64.decode(str(params["sign_payload_b64"]))
        payload_fields = params.get("payload_fields") or {"raw": "true"}
        if not isinstance(payload_fields, dict):
            raise SappiensError("payload_fields must be an object")
        relay = RelayClient(settings.relay_url, timeout=settings.command_timeout)
        try:
            result = propose_raw(
                identity=identity,
                store=store,
                relay=relay,
                summary=str(params["summary"]),
                human={
                    "action": str(params["human_action"]),
                    "assets": str(params["human_assets"]),
                    "amounts": str(params["human_amounts"]),
                    "counterparties": str(params["human_counterparties"]),
                    "chain": str(params["human_chain"]),
                },
                technical={
                    "chain": str(params["technical_chain"]),
                    "destination": str(params["destination"]),
                    "payload_fields": {
                        str(k): str(v) if not isinstance(v, (dict, list)) else v
                        for k, v in payload_fields.items()
                    },
                },
                sign_payload=sign_payload,
            )
        finally:
            relay.close()
        return _json(result)
    except Exception as exc:  # noqa: BLE001
        logger.exception("sappiens_propose_raw failed")
        return _err(exc)


def approval_message(tool_name: str, args: dict[str, Any]) -> str | None:
    """Human-readable sentence for Hermes pre_tool_call approve gate."""
    if tool_name == "sappiens_send":
        skill = args.get("skill") or "nyx"
        return (
            f"Sappiens propose SEND via skill {skill}: "
            f"{args.get('amount')} to {args.get('to_address')} "
            f"from {args.get('from_address')}"
        )
    if tool_name == "sappiens_claim_rewards":
        skill = args.get("skill") or "nyx"
        return (
            f"Sappiens propose CLAIM node rewards via skill {skill} "
            f"for {args.get('from_address')}"
        )
    if tool_name == "sappiens_propose_raw":
        return (
            f"Sappiens propose RAW: {args.get('summary')} "
            f"→ {args.get('destination')} on {args.get('technical_chain')}"
        )
    return None


def is_write_tool(tool_name: str) -> bool:
    return tool_name in _WRITE_TOOLS
