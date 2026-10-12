"""Settings resolution: plugin config > env > defaults."""

from __future__ import annotations

from sappiens_hermes.config import Settings, bind_config_getter


def teardown_function() -> None:
    bind_config_getter(None)


def test_defaults_when_unbound(monkeypatch):
    monkeypatch.delenv("SAPPIENS_RELAY_URL", raising=False)
    monkeypatch.delenv("SAPPIENS_ADVERTISE_RELAY", raising=False)
    bind_config_getter(None)
    settings = Settings.from_env({})
    assert settings.relay_url == "http://127.0.0.1:8080"
    assert settings.advertise_relay is None
    assert settings.advertise_url == "http://127.0.0.1:8080"


def test_env_relay_and_empty_advertise(monkeypatch):
    monkeypatch.setenv("SAPPIENS_RELAY_URL", "http://relay.env:8080")
    monkeypatch.delenv("SAPPIENS_ADVERTISE_RELAY", raising=False)
    bind_config_getter(None)
    settings = Settings.from_env()
    assert settings.relay_url == "http://relay.env:8080"
    assert settings.advertise_relay is None
    assert settings.advertise_url == "http://relay.env:8080"


def test_plugin_config_beats_env(monkeypatch):
    monkeypatch.setenv("SAPPIENS_RELAY_URL", "http://from.env")
    monkeypatch.setenv("SAPPIENS_ADVERTISE_RELAY", "http://adv.env")
    values = {
        "relay_url": "http://from.plugin",
        "advertise_relay": "http://adv.plugin",
    }
    bind_config_getter(lambda key, default=None: values.get(key, default))
    settings = Settings.from_env()
    assert settings.relay_url == "http://from.plugin"
    assert settings.advertise_relay == "http://adv.plugin"
    assert settings.advertise_url == "http://adv.plugin"


def test_empty_plugin_advertise_falls_back_to_relay(monkeypatch):
    monkeypatch.setenv("SAPPIENS_RELAY_URL", "http://from.env")
    values = {"relay_url": "http://plugin.relay", "advertise_relay": ""}
    bind_config_getter(lambda key, default=None: values.get(key, default))
    settings = Settings.from_env()
    assert settings.relay_url == "http://plugin.relay"
    assert settings.advertise_relay is None
    assert settings.advertise_url == "http://plugin.relay"
