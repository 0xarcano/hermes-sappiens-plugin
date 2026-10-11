"""Chain builders keyed by skill.yaml `builder` field."""

from __future__ import annotations

from importlib import import_module
from typing import Any, Protocol

from sappiens_hermes.errors import SkillError
from sappiens_hermes.presentation import ProposalPresentation


class ChainBuilder(Protocol):
    def send_tokens(self, skill: Any, params: dict[str, Any]) -> ProposalPresentation: ...

    def claim_node_rewards(
        self, skill: Any, params: dict[str, Any]
    ) -> ProposalPresentation: ...


def load_builder(name: str) -> Any:
    try:
        return import_module(f"sappiens_hermes.builders.{name}")
    except ImportError as exc:
        raise SkillError(f"unknown builder module: {name}") from exc
