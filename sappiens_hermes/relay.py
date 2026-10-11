"""Sappiens relay OpenAPI client."""

from __future__ import annotations

import time
from typing import Any

import httpx

from sappiens_hermes.envelope import Envelope
from sappiens_hermes.errors import RelayError
from sappiens_hermes.offer import RegistrationOffer


class RelayClient:
    def __init__(
        self,
        relay_base_url: str,
        *,
        timeout: float = 30.0,
        client: httpx.Client | None = None,
    ) -> None:
        self.base = f"{relay_base_url.rstrip('/')}/v1"
        self._owns = client is None
        self.http = client or httpx.Client(timeout=timeout)

    def close(self) -> None:
        if self._owns:
            self.http.close()

    def create_offer(self, offer: RegistrationOffer) -> dict[str, Any]:
        resp = self.http.post(f"{self.base}/offers", json=offer.to_create_offer_json())
        if resp.status_code != 201:
            raise RelayError(
                f"createOffer failed: {resp.status_code} {resp.text}",
                status=resp.status_code,
            )
        return resp.json()

    def get_offer(self, offer_id: str) -> dict[str, Any]:
        resp = self.http.get(f"{self.base}/offers/{offer_id}")
        if resp.status_code >= 400:
            raise RelayError(
                f"getOffer failed: {resp.status_code} {resp.text}",
                status=resp.status_code,
            )
        return resp.json()

    def submit_envelope(self, envelope: Envelope) -> dict[str, Any]:
        """Retry transport / 5xx up to 3 times with the same envelope_id."""
        last_error = "unknown"
        payload = envelope.to_json()
        for attempt in range(4):
            if attempt > 0:
                time.sleep(0.5 * (2 ** (attempt - 1)))
            try:
                resp = self.http.post(f"{self.base}/envelopes", json=payload)
            except httpx.HTTPError as exc:
                last_error = str(exc)
                continue
            if resp.status_code in (201, 202):
                return resp.json()
            if resp.status_code >= 500:
                last_error = f"{resp.status_code} {resp.text}"
                continue
            raise RelayError(
                f"submitEnvelope rejected: {resp.status_code} {resp.text}",
                status=resp.status_code,
            )
        raise RelayError(f"submitEnvelope failed after retries: {last_error}")
