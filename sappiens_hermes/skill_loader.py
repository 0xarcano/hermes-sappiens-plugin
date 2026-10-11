"""Discover and load chain SKILLs from skills/*/SKILL.md + skill.yaml."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from sappiens_hermes.builders import load_builder
from sappiens_hermes.errors import SkillError
from sappiens_hermes.presentation import ProposalPresentation


def plugin_root() -> Path:
    return Path(__file__).resolve().parent.parent


def skills_dir() -> Path:
    return plugin_root() / "skills"


@dataclass
class ChainSkill:
    name: str
    path: Path
    skill_md: Path
    chain_id: str
    display_name: str
    bech32_prefix: str
    denom: str
    rpc: str
    lcd: str
    builder_name: str
    operations: dict[str, Any] = field(default_factory=dict)
    raw: dict[str, Any] = field(default_factory=dict)

    def summary(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "chain_id": self.chain_id,
            "display_name": self.display_name,
            "denom": self.denom,
            "rpc": self.rpc,
            "lcd": self.lcd,
            "operations": sorted(self.operations.keys()),
            "skill_view": f"sappiens-wallet:{self.name}",
            "path": str(self.path),
        }

    def run(self, operation: str, params: dict[str, Any]) -> ProposalPresentation:
        if operation not in self.operations:
            raise SkillError(
                f"skill {self.name} has no operation '{operation}'. "
                f"Available: {sorted(self.operations)}"
            )
        mod = load_builder(self.builder_name)
        fn = getattr(mod, operation, None)
        if fn is None:
            raise SkillError(
                f"builder '{self.builder_name}' missing function '{operation}'"
            )
        return fn(self, params)


def load_skill(directory: Path) -> ChainSkill:
    skill_md = directory / "SKILL.md"
    skill_yaml = directory / "skill.yaml"
    if not skill_md.is_file():
        raise SkillError(f"missing SKILL.md in {directory}")
    if not skill_yaml.is_file():
        raise SkillError(f"missing skill.yaml in {directory}")
    raw = yaml.safe_load(skill_yaml.read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        raise SkillError(f"skill.yaml must be a mapping: {skill_yaml}")
    name = str(raw.get("name") or directory.name)
    required = ["chain_id", "display_name", "bech32_prefix", "denom", "rpc", "lcd", "builder"]
    for key in required:
        if not raw.get(key):
            raise SkillError(f"skill.yaml missing '{key}' for {name}")
    ops = raw.get("operations") or {}
    if not isinstance(ops, dict) or not ops:
        raise SkillError(f"skill.yaml operations must be a non-empty map for {name}")
    return ChainSkill(
        name=name,
        path=directory,
        skill_md=skill_md,
        chain_id=str(raw["chain_id"]),
        display_name=str(raw["display_name"]),
        bech32_prefix=str(raw["bech32_prefix"]),
        denom=str(raw["denom"]),
        rpc=str(raw["rpc"]),
        lcd=str(raw["lcd"]),
        builder_name=str(raw["builder"]),
        operations=dict(ops),
        raw=raw,
    )


def discover_skills(root: Path | None = None) -> list[ChainSkill]:
    base = root or skills_dir()
    if not base.is_dir():
        return []
    skills: list[ChainSkill] = []
    for child in sorted(base.iterdir()):
        if child.is_dir() and (child / "SKILL.md").is_file():
            skills.append(load_skill(child))
    return skills


class SkillRegistry:
    def __init__(self, skills: list[ChainSkill] | None = None) -> None:
        self._skills = {s.name: s for s in (skills if skills is not None else discover_skills())}

    def list(self) -> list[ChainSkill]:
        return [self._skills[k] for k in sorted(self._skills)]

    def get(self, name: str) -> ChainSkill:
        if name not in self._skills:
            raise SkillError(
                f"unknown skill '{name}'. Available: {sorted(self._skills)}"
            )
        return self._skills[name]

    def get_for_chain(self, chain_id: str) -> ChainSkill:
        for skill in self._skills.values():
            if skill.chain_id == chain_id:
                return skill
        raise SkillError(f"no skill for chain_id '{chain_id}'")
