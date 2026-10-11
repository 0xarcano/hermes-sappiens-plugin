"""Plugin-facing errors."""

from __future__ import annotations


class SappiensError(Exception):
    """Base error for the Sappiens Hermes plugin."""


class ConfigError(SappiensError):
    """Missing or invalid configuration / secrets."""


class ProtocolError(SappiensError):
    """Wire / CBOR / crypto protocol failure."""


class RelayError(SappiensError):
    """Relay HTTP failure."""

    def __init__(self, message: str, *, status: int | None = None) -> None:
        super().__init__(message)
        self.status = status


class NotPairedError(SappiensError):
    """No active authorization with a wallet."""


class SkillError(SappiensError):
    """Skill load or operation failure."""


class BuilderError(SappiensError):
    """Chain payload builder failure."""
