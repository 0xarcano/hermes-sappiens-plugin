"""Tool wiring + approval helper tests."""

from __future__ import annotations

import json
from pathlib import Path

from sappiens_hermes import b64
from sappiens_hermes.identity import AgentIdentity
from sappiens_hermes.plugin import register
from sappiens_hermes import tools


class FakeCtx:
    def __init__(self):
        self.tools = {}
        self.skills = []
        self.hooks = {}
        self.commands = []

    def register_tool(self, **kwargs):
        self.tools[kwargs["name"]] = kwargs

    def register_skill(self, name, path):
        self.skills.append((name, Path(path)))

    def register_hook(self, name, cb):
        self.hooks[name] = cb

    def register_command(self, name, cb, description=""):
        self.commands.append(name)


def test_register_wires_tools_skills_hook():
    ctx = FakeCtx()
    register(ctx)
    assert "sappiens_send" in ctx.tools
    assert "sappiens_claim_rewards" in ctx.tools
    assert any(n == "nyx" for n, _ in ctx.skills)
    assert "pre_tool_call" in ctx.hooks
    directive = ctx.hooks["pre_tool_call"](
        tool_name="sappiens_send",
        args={
            "from_address": "n1a",
            "to_address": "n1b",
            "amount": "1",
        },
    )
    assert directive["action"] == "approve"
    assert "SEND" in directive["message"]


def test_status_with_seed(tmp_path: Path, monkeypatch):
    identity = AgentIdentity.from_seed(bytes([21] * 32))
    seed = b64.encode(identity.private_key.private_bytes_raw())
    monkeypatch.setenv("SAPPIENS_AGENT_ED25519_SEED", seed)
    monkeypatch.setenv("SAPPIENS_STATE_PATH", str(tmp_path / "state.json"))
    monkeypatch.setenv("SAPPIENS_RELAY_URL", "http://127.0.0.1:8080")
    out = json.loads(tools.sappiens_status({}))
    assert out["ok"] is True
    assert out["agent_id"].startswith("ed25519:")
    assert out["paired"] is False
    assert any(s["name"] == "nyx" for s in out["skills"])


def test_skills_tool():
    out = json.loads(tools.sappiens_skills({}))
    assert out["ok"]
    assert any(s["name"] == "nyx" for s in out["skills"])
    detail = json.loads(tools.sappiens_skills({"name": "nyx"}))
    assert "claim_node_rewards" in detail["operations"]
