"""ProposalDocument + dual presentation CBOR."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from sappiens_hermes import cbor_util
from sappiens_hermes.errors import ProtocolError
from sappiens_hermes.offer import format_timestamp

SCHEMA_VERSION = "1"
MAX_SUMMARY_CHARS = 120
MAX_HUMAN_FIELD_CHARS = 500
MAX_TECHNICAL_CHAIN_CHARS = 200
MAX_TECHNICAL_DESTINATION_CHARS = 500
MAX_SIGN_PAYLOAD_LEN = 65536


def _trim_check(field: str, value: str, max_len: int) -> str:
    if value != value.strip() or not value:
        raise ProtocolError(f"{field} must be non-empty trimmed text")
    if len(value) > max_len:
        raise ProtocolError(f"{field} exceeds max length {max_len}")
    return value


def _validate_payload_fields(value: Any) -> None:
    if not isinstance(value, dict) or not value:
        raise ProtocolError("payload_fields must be a non-empty map")
    for key, val in value.items():
        if not isinstance(key, str) or not key:
            raise ProtocolError("payload_fields keys must be non-empty text")
        _validate_display_value(val)


def _validate_display_value(value: Any) -> None:
    if isinstance(value, str):
        return
    if isinstance(value, list):
        for item in value:
            _validate_display_value(item)
        return
    if isinstance(value, dict):
        for key, val in value.items():
            if not isinstance(key, str) or not key:
                raise ProtocolError("nested map keys must be non-empty text")
            _validate_display_value(val)
        return
    raise ProtocolError("payload_fields values must be text or nested maps/arrays of text")


@dataclass
class HumanReadableView:
    action: str
    assets: str
    amounts: str
    counterparties: str
    chain: str

    def validate(self) -> None:
        for field, value in [
            ("action", self.action),
            ("assets", self.assets),
            ("amounts", self.amounts),
            ("counterparties", self.counterparties),
            ("chain", self.chain),
        ]:
            _trim_check(field, value, MAX_HUMAN_FIELD_CHARS)

    def to_map(self) -> dict[str, str]:
        return {
            "action": self.action,
            "assets": self.assets,
            "amounts": self.amounts,
            "counterparties": self.counterparties,
            "chain": self.chain,
        }


@dataclass
class TechnicalView:
    chain: str
    destination: str
    payload_fields: dict[str, Any]
    sign_payload: bytes

    def validate(self) -> None:
        _trim_check("chain", self.chain, MAX_TECHNICAL_CHAIN_CHARS)
        _trim_check("destination", self.destination, MAX_TECHNICAL_DESTINATION_CHARS)
        _validate_payload_fields(self.payload_fields)
        n = len(self.sign_payload)
        if n < 1 or n > MAX_SIGN_PAYLOAD_LEN:
            raise ProtocolError("sign_payload length must be 1..65536")

    def to_map(self) -> dict[str, Any]:
        return {
            "chain": self.chain,
            "destination": self.destination,
            "payload_fields": self.payload_fields,
            "sign_payload": self.sign_payload,
        }


@dataclass
class ProposalPresentation:
    human: HumanReadableView
    technical: TechnicalView

    def validate(self) -> None:
        self.human.validate()
        self.technical.validate()

    def to_map(self) -> dict[str, Any]:
        return {"human": self.human.to_map(), "technical": self.technical.to_map()}


@dataclass
class ProposalDocument:
    schema_version: str
    proposal_id: str
    summary: str
    body: dict[str, Any]
    created_at: str
    presentation: ProposalPresentation | None

    def validate(self) -> None:
        if self.schema_version != SCHEMA_VERSION:
            raise ProtocolError(f"unsupported schema_version: {self.schema_version}")
        n = len(self.summary)
        if n < 1 or n > MAX_SUMMARY_CHARS:
            raise ProtocolError("summary must be 1-120 characters")
        if not isinstance(self.body, dict):
            raise ProtocolError("body must be a map")
        if self.presentation is not None:
            self.presentation.validate()

    def to_cbor(self) -> bytes:
        data: dict[str, Any] = {
            "schema_version": self.schema_version,
            "proposal_id": self.proposal_id,
            "summary": self.summary,
            "body": self.body,
            "created_at": self.created_at,
        }
        if self.presentation is not None:
            data["presentation"] = self.presentation.to_map()
        return cbor_util.encode(data)

    @classmethod
    def new(
        cls,
        summary: str,
        body: dict[str, Any] | None = None,
        presentation: ProposalPresentation | None = None,
        *,
        now: datetime | None = None,
        proposal_id: str | None = None,
    ) -> ProposalDocument:
        doc = cls(
            schema_version=SCHEMA_VERSION,
            proposal_id=proposal_id or str(uuid4()),
            summary=summary.strip(),
            body=body if body is not None else {},
            created_at=format_timestamp(now or datetime.now(timezone.utc)),
            presentation=presentation,
        )
        doc.validate()
        return doc
