"""Non-secret settings from Hermes plugin config / env / defaults."""

from __future__ import annotations

import os
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any


DEFAULT_RELAY_URL = "http://127.0.0.1:8080"
DEFAULT_DISPLAY_NAME = "Hermes Sappiens Agent"
DEFAULT_OFFER_TTL_MINUTES = 10
DEFAULT_POLL_INTERVAL_SECONDS = 2
DEFAULT_COMMAND_TIMEOUT = 90

_ConfigGetter = Callable[..., Any]
_config_getter: _ConfigGetter | None = None


def bind_config_getter(getter: _ConfigGetter | None) -> None:
    """Bind Hermes ctx.get_config for Settings resolution (called from register)."""
    global _config_getter
    _config_getter = getter


def _plugin_str(key: str) -> str | None:
    if _config_getter is None:
        return None
    try:
        value = _config_getter(key, default=None)
    except Exception:  # noqa: BLE001
        return None
    if value is None:
        return None
    text = str(value).strip()
    return text or None


@dataclass(frozen=True)
class Settings:
    relay_url: str = DEFAULT_RELAY_URL
    advertise_relay: str | None = None
    display_name: str = DEFAULT_DISPLAY_NAME
    offer_ttl_minutes: int = DEFAULT_OFFER_TTL_MINUTES
    poll_interval_seconds: float = DEFAULT_POLL_INTERVAL_SECONDS
    command_timeout: float = DEFAULT_COMMAND_TIMEOUT
    state_path: Path | None = None

    @property
    def advertise_url(self) -> str:
        return (self.advertise_relay or self.relay_url).rstrip("/")

    @classmethod
    def from_env(cls, env: dict[str, str] | None = None) -> Settings:
        env = env or dict(os.environ)
        state = env.get("SAPPIENS_STATE_PATH", "").strip()

        relay_url = (
            _plugin_str("relay_url")
            or env.get("SAPPIENS_RELAY_URL", "").strip()
            or DEFAULT_RELAY_URL
        )
        advertise = _plugin_str("advertise_relay")
        if advertise is None:
            advertise = (env.get("SAPPIENS_ADVERTISE_RELAY") or "").strip() or None

        return cls(
            relay_url=relay_url,
            advertise_relay=advertise,
            display_name=env.get("SAPPIENS_DISPLAY_NAME", DEFAULT_DISPLAY_NAME).strip()
            or DEFAULT_DISPLAY_NAME,
            offer_ttl_minutes=int(
                env.get("SAPPIENS_OFFER_TTL_MINUTES", str(DEFAULT_OFFER_TTL_MINUTES))
            ),
            poll_interval_seconds=float(
                env.get(
                    "SAPPIENS_POLL_INTERVAL_SECONDS",
                    str(DEFAULT_POLL_INTERVAL_SECONDS),
                )
            ),
            command_timeout=float(
                env.get("SAPPIENS_COMMAND_TIMEOUT", str(DEFAULT_COMMAND_TIMEOUT))
            ),
            state_path=Path(state) if state else None,
        )


def default_state_path() -> Path:
    """Prefer Hermes plugin_data_dir when available; else ~/.hermes/sappiens-wallet/."""
    try:
        # Optional Hermes host helper (present when running inside Hermes).
        from hermes_agent.plugins import plugin_data_dir  # type: ignore

        return Path(plugin_data_dir("sappiens-wallet")) / "state.json"
    except Exception:  # noqa: BLE001
        home = Path(os.environ.get("HERMES_HOME", Path.home() / ".hermes"))
        return home / "sappiens-wallet" / "state.json"
