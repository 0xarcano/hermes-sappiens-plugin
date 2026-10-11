"""Hermes register(ctx) entry for the Sappiens wallet plugin."""

from __future__ import annotations

import logging
from pathlib import Path

from sappiens_hermes import schemas, tools
from sappiens_hermes.skill_loader import discover_skills, skills_dir

logger = logging.getLogger(__name__)

TOOLSET = "sappiens-wallet"


def register(ctx) -> None:
    """Wire tools, write-approval hook, and bundled chain skills."""
    registrations = [
        ("sappiens_pair", schemas.SAPPENS_PAIR, tools.sappiens_pair),
        ("sappiens_status", schemas.SAPPENS_STATUS, tools.sappiens_status),
        ("sappiens_skills", schemas.SAPPENS_SKILLS, tools.sappiens_skills),
        ("sappiens_send", schemas.SAPPENS_SEND, tools.sappiens_send),
        (
            "sappiens_claim_rewards",
            schemas.SAPPENS_CLAIM_REWARDS,
            tools.sappiens_claim_rewards,
        ),
        (
            "sappiens_propose_raw",
            schemas.SAPPENS_PROPOSE_RAW,
            tools.sappiens_propose_raw,
        ),
    ]
    for name, schema, handler in registrations:
        ctx.register_tool(
            name=name,
            toolset=TOOLSET,
            schema=schema,
            handler=handler,
        )

    def pre_tool_call(tool_name: str = "", args: dict | None = None, **kwargs):
        del kwargs
        args = args or {}
        if not tools.is_write_tool(tool_name):
            return None
        message = tools.approval_message(tool_name, args)
        if not message:
            return None
        return {"action": "approve", "message": message}

    if hasattr(ctx, "register_hook"):
        try:
            ctx.register_hook("pre_tool_call", pre_tool_call)
        except Exception as exc:  # pragma: no cover
            logger.debug("pre_tool_call hook skipped: %s", exc)

    # Bundle skills for skill_view("sappiens-wallet:<name>")
    if hasattr(ctx, "register_skill"):
        for skill in discover_skills(skills_dir()):
            try:
                ctx.register_skill(skill.name, skill.skill_md)
            except Exception as exc:  # pragma: no cover
                logger.warning("register_skill(%s) failed: %s", skill.name, exc)

    def _cmd_pair(args: str = "") -> str:
        params: dict = {}
        if args.strip():
            params["display_name"] = args.strip()
        return tools.sappiens_pair(params)

    def _cmd_status(_args: str = "") -> str:
        return tools.sappiens_status({})

    if hasattr(ctx, "register_command"):
        try:
            ctx.register_command(
                "sappiens-pair",
                _cmd_pair,
                description="Start Sappiens Wallet pairing (QR URI)",
            )
            ctx.register_command(
                "sappiens-status",
                _cmd_status,
                description="Sappiens Wallet pairing status",
            )
        except Exception as exc:  # pragma: no cover
            logger.debug("slash command registration skipped: %s", exc)

    logger.info(
        "sappiens-wallet plugin registered (%d tools, skills_dir=%s)",
        len(registrations),
        skills_dir(),
    )


def plugin_path() -> Path:
    return Path(__file__).resolve().parent.parent
