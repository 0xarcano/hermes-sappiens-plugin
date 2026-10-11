"""Persisted pairing / authorization state."""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from sappiens_hermes import b64
from sappiens_hermes.config import Settings, default_state_path
from sappiens_hermes.errors import NotPairedError


@dataclass
class PendingOffer:
    offer_id: str
    x25519_secret: str  # base64url
    expires_at: str


@dataclass
class StoredAuthorization:
    authorization_id: str
    offer_id: str
    channel_key: str  # base64url
    wallet_x25519_pubkey: str = ""


@dataclass
class AgentState:
    display_name: str = "Hermes Sappiens Agent"
    pending_offer: PendingOffer | None = None
    authorizations: list[StoredAuthorization] = field(default_factory=list)
    last_proposal_id: str | None = None
    last_envelope_id: str | None = None

    def latest_authorization(self) -> StoredAuthorization:
        if not self.authorizations:
            raise NotPairedError(
                "No active Sappiens authorization. Run sappiens_pair first."
            )
        return self.authorizations[-1]

    def channel_key_bytes(self) -> bytes:
        return b64.decode(self.latest_authorization().channel_key)

    def to_dict(self) -> dict[str, Any]:
        return {
            "display_name": self.display_name,
            "pending_offer": asdict(self.pending_offer) if self.pending_offer else None,
            "authorizations": [asdict(a) for a in self.authorizations],
            "last_proposal_id": self.last_proposal_id,
            "last_envelope_id": self.last_envelope_id,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AgentState:
        pending = data.get("pending_offer")
        auths = [
            StoredAuthorization(**a) for a in data.get("authorizations") or []
        ]
        return cls(
            display_name=str(data.get("display_name") or "Hermes Sappiens Agent"),
            pending_offer=PendingOffer(**pending) if pending else None,
            authorizations=auths,
            last_proposal_id=data.get("last_proposal_id"),
            last_envelope_id=data.get("last_envelope_id"),
        )


class StateStore:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or default_state_path()

    def load(self) -> AgentState:
        if not self.path.exists():
            return AgentState()
        data = json.loads(self.path.read_text(encoding="utf-8"))
        return AgentState.from_dict(data)

    def save(self, state: AgentState) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(state.to_dict(), indent=2) + "\n", encoding="utf-8")
        os.replace(tmp, self.path)


def store_from_settings(settings: Settings) -> StateStore:
    return StateStore(settings.state_path or default_state_path())
