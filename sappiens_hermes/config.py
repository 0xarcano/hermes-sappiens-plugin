"""Non-secret settings from env / defaults."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


DEFAULT_RELAY_URL = "http://127.0.0.1:8080"
DEFAULT_DISPLAY_NAME = "Hermes Sappiens Agent"
DEFAULT_OFFER_TTL_MINUTES = 10
DEFAULT_POLL_INTERVAL_SECONDS = 2
DEFAULT_COMMAND_TIMEOUT = 90


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
        state = env.get("SAPPENS_STATE_PATH", "").strip()
        return cls(
            relay_url=env.get("SAPPENS_RELAY_URL", DEFAULT_RELAY_URL).strip()
            or DEFAULT_RELAY_URL,
            advertise_relay=(env.get("SAPPENS_ADVERTISE_RELAY") or "").strip() or None,
            display_name=env.get("SAPPENS_DISPLAY_NAME", DEFAULT_DISPLAY_NAME).strip()
            or DEFAULT_DISPLAY_NAME,
            offer_ttl_minutes=int(
                env.get("SAPPENS_OFFER_TTL_MINUTES", str(DEFAULT_OFFER_TTL_MINUTES))
            ),
            poll_interval_seconds=float(
                env.get(
                    "SAPPENS_POLL_INTERVAL_SECONDS",
                    str(DEFAULT_POLL_INTERVAL_SECONDS),
                )
            ),
            command_timeout=float(
                env.get("SAPPENS_COMMAND_TIMEOUT", str(DEFAULT_COMMAND_TIMEOUT))
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
