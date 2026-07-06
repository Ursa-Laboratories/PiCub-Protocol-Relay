"""Reusable client for sending CubOS protocol bundles to a station worker."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

import requests


class StationRequestError(RuntimeError):
    """The station worker request failed or returned an unsuccessful payload."""


@dataclass(frozen=True)
class ProtocolBundle:
    """The three YAML files a station worker needs to execute a CubOS protocol."""

    gantry_config: str
    deck_config: str
    protocol_yaml: str

    @classmethod
    def from_paths(
        cls,
        *,
        gantry_config: Path,
        deck_config: Path,
        protocol_yaml: Path,
    ) -> "ProtocolBundle":
        return cls(
            gantry_config=read_text(gantry_config),
            deck_config=read_text(deck_config),
            protocol_yaml=read_text(protocol_yaml),
        )

    def as_payload(self) -> dict[str, str]:
        return {
            "gantry_config": self.gantry_config,
            "deck_config": self.deck_config,
            "protocol_yaml": self.protocol_yaml,
        }


class StationClient:
    """HTTP client for the station-worker API."""

    def __init__(self, base_url: str, *, session: requests.Session | None = None) -> None:
        self.base_url = base_url.rstrip("/")
        self.session = session or requests.Session()

    def health(self, *, timeout: float) -> dict[str, Any]:
        return get_json(self.session, f"{self.base_url}/health", timeout=timeout)

    def validate_protocol(
        self,
        bundle: ProtocolBundle,
        *,
        run_id: str | None = None,
        timeout: float,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = bundle.as_payload()
        if run_id:
            payload["run_id"] = run_id
        return post_json(self.session, f"{self.base_url}/validate-protocol", payload, timeout=timeout)

    def run_protocol(
        self,
        bundle: ProtocolBundle,
        *,
        run_id: str,
        mock_mode: bool = False,
        metadata: dict[str, Any] | None = None,
        timeout: float,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "run_id": run_id,
            **bundle.as_payload(),
            "mock_mode": mock_mode,
        }
        if metadata:
            payload["metadata"] = metadata
        response = post_json(self.session, f"{self.base_url}/run-protocol", payload, timeout=timeout)
        if not response.get("success", False):
            raise StationRequestError(
                f"station run {run_id!r} failed: {response.get('error') or response!r}"
            )
        return response


def read_text(path: Path) -> str:
    return path.expanduser().resolve().read_text()


def metadata_from_json(value: str | None) -> dict[str, Any] | None:
    if not value:
        return None
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError as exc:
        raise StationRequestError(f"--metadata-json is not valid JSON: {exc}") from exc
    if not isinstance(parsed, dict):
        raise StationRequestError("--metadata-json must decode to a JSON object")
    return parsed


def print_json(label: str, payload: Any) -> None:
    print(json.dumps({label: payload}, indent=2, sort_keys=True))


def get_json(session: requests.Session, url: str, *, timeout: float) -> dict[str, Any]:
    try:
        response = session.get(url, timeout=timeout)
    except requests.RequestException as exc:
        raise StationRequestError(f"GET {url} failed: {exc}") from exc
    return decode_json(response, url)


def post_json(
    session: requests.Session,
    url: str,
    payload: dict[str, Any],
    *,
    timeout: float,
) -> dict[str, Any]:
    try:
        response = session.post(url, json=payload, timeout=timeout)
    except requests.RequestException as exc:
        raise StationRequestError(f"POST {url} failed: {exc}") from exc
    return decode_json(response, url)


def decode_json(response: requests.Response, url: str) -> dict[str, Any]:
    if response.status_code >= 400:
        raise StationRequestError(f"{url} -> HTTP {response.status_code}: {safe_body(response)}")
    try:
        data = response.json()
    except ValueError as exc:
        raise StationRequestError(f"{url} -> non-JSON response: {response.text[:200]!r}") from exc
    if not isinstance(data, dict):
        raise StationRequestError(f"{url} -> JSON response is not an object: {data!r}")
    return data


def safe_body(response: requests.Response) -> str:
    try:
        return str(response.json())
    except ValueError:
        return response.text[:300]
