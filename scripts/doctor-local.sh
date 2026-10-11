#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

python3 - <<'PY'
from pathlib import Path
import yaml

root = Path(".")
assert (root / "plugin.yaml").is_file(), "missing plugin.yaml"
manifest = yaml.safe_load((root / "plugin.yaml").read_text())
assert manifest.get("name") == "sappiens-wallet"
tools = set(manifest.get("provides_tools") or [])
expected = {
    "sappiens_pair",
    "sappiens_status",
    "sappiens_skills",
    "sappiens_send",
    "sappiens_claim_rewards",
    "sappiens_propose_raw",
}
missing = expected - tools
assert not missing, f"plugin.yaml missing tools: {missing}"

from sappiens_hermes.plugin import register
from sappiens_hermes.skill_loader import discover_skills

class FakeCtx:
    def __init__(self):
        self.tools = []
        self.skills = []
        self.hooks = []
        self.commands = []

    def register_tool(self, **kwargs):
        self.tools.append(kwargs["name"])

    def register_skill(self, name, path):
        self.skills.append((name, str(path)))

    def register_hook(self, name, cb):
        self.hooks.append(name)

    def register_command(self, name, cb, description=""):
        self.commands.append(name)

ctx = FakeCtx()
register(ctx)
assert set(ctx.tools) == expected
assert any(n == "nyx" for n, _ in ctx.skills), ctx.skills
assert "pre_tool_call" in ctx.hooks
skills = discover_skills()
assert any(s.name == "nyx" for s in skills)
print("doctor-local: OK")
print(f"  tools={sorted(ctx.tools)}")
print(f"  skills={[s.name for s in skills]}")
PY
