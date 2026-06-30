#!/usr/bin/env python3
"""Send this directory's ASMI protocol YAML directly to the station worker."""

from __future__ import annotations

import argparse
from collections.abc import Mapping
import csv
import json
from pathlib import Path
import re
import sys
from typing import Any

import requests

HERE = Path(__file__).resolve().parent


class StationRequestError(RuntimeError):
    """The station worker request failed or returned an unsuccessful payload."""


def main() -> int:
    args = parse_args()
    base_url = args.asmi_base_url.rstrip("/")
    protocol_yaml = read_text(args.protocol_yaml)
    session = requests.Session()

    if not args.no_health_check:
        health = get_json(session, f"{base_url}/health", timeout=args.health_timeout_s)
        print(json.dumps({"health": health}, indent=2, sort_keys=True))

    response = post_json(
        session,
        f"{base_url}/run-protocol",
        {
            "run_id": args.run_id,
            "gantry_config": read_text(args.gantry_config),
            "deck_config": read_text(args.deck_config),
            "protocol_yaml": protocol_yaml,
            "mock_mode": args.mock_mode,
        },
        timeout=args.timeout_s,
    )
    if not response.get("success", False):
        raise StationRequestError(
            f"ASMI station run {args.run_id!r} failed: {response.get('error') or response!r}"
        )
    if args.output_csv:
        write_csv(args.output_csv, response, run_id=args.run_id, wells=protocol_wells(protocol_yaml))
        print(f"wrote CSV: {args.output_csv}")
    print(json.dumps(response, indent=2, sort_keys=True))
    return 0


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Send local protocol.yaml unchanged to the ASMI station worker."
    )
    parser.add_argument("--asmi-base-url", default="http://10.210.29.17:8000")
    parser.add_argument("--run-id", default="asmi-protocol")
    parser.add_argument("--protocol-yaml", type=Path, default=HERE / "protocol.yaml")
    parser.add_argument("--gantry-config", type=Path, default=HERE / "gantry_config.yaml")
    parser.add_argument("--deck-config", type=Path, default=HERE / "deck_config.yaml")
    parser.add_argument("--timeout-s", type=float, default=900.0)
    parser.add_argument("--health-timeout-s", type=float, default=3.0)
    parser.add_argument("--output-csv", type=Path, default=HERE / "asmi_result.csv")
    parser.add_argument("--mock-mode", action="store_true")
    parser.add_argument("--no-health-check", action="store_true")
    return parser.parse_args(argv)


def write_csv(path: Path, response: Mapping[str, Any], *, run_id: str, wells: list[str]) -> Path:
    rows = csv_rows(response, run_id=run_id, wells=wells)
    path = path.expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    preferred = [
        "run_id",
        "well",
        "sample_index",
        "timestamp_s",
        "z_position_mm",
        "raw_force_n",
        "corrected_force_n",
        "direction",
    ]
    extras = sorted({key for row in rows for key in row if key not in preferred})
    fieldnames = [key for key in preferred if any(key in row for row in rows)] + extras
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return path


def csv_rows(response: Mapping[str, Any], *, run_id: str, wells: list[str]) -> list[dict[str, Any]]:
    payloads = station_payloads(
        response,
        preferred_keys=(
            "measurements",
            "z_positions",
            "raw_forces",
            "corrected_forces",
            "sample_timestamps",
        ),
    )
    rows: list[dict[str, Any]] = []
    for payload_index, payload in enumerate(payloads):
        well = payload_well(payload) or at(wells, payload_index)
        for sample_index, sample in enumerate(asmi_samples(payload)):
            rows.append({"run_id": run_id, "well": well, "sample_index": sample_index, **sample})
    if rows:
        return rows
    return [{"run_id": run_id, "well": ",".join(wells), **flatten(response)}]


def asmi_samples(payload: Any) -> list[dict[str, Any]]:
    if not isinstance(payload, Mapping):
        return []

    measurements = payload.get("measurements")
    if isinstance(measurements, list):
        return [
            {
                "timestamp_s": sample.get("timestamp"),
                "z_position_mm": sample.get("z_mm"),
                "raw_force_n": sample.get("raw_force_n"),
                "corrected_force_n": sample.get("corrected_force_n"),
                "direction": sample.get("direction", "down"),
            }
            for sample in measurements
            if isinstance(sample, Mapping)
        ]

    z_positions = payload.get("z_positions") or []
    raw_forces = payload.get("raw_forces") or []
    corrected_forces = payload.get("corrected_forces") or []
    timestamps = payload.get("sample_timestamps") or []
    directions = payload.get("directions") or []
    count = max(len(z_positions), len(raw_forces), len(corrected_forces), len(timestamps), len(directions))
    return [
        {
            "timestamp_s": at(timestamps, index),
            "z_position_mm": at(z_positions, index),
            "raw_force_n": at(raw_forces, index),
            "corrected_force_n": at(corrected_forces, index),
            "direction": at(directions, index),
        }
        for index in range(count)
    ]


def station_payloads(value: Any, *, preferred_keys: tuple[str, ...]) -> list[Mapping[str, Any]]:
    found: list[Mapping[str, Any]] = []
    if isinstance(value, list):
        for item in value:
            found.extend(station_payloads(item, preferred_keys=preferred_keys))
    elif isinstance(value, Mapping):
        if any(key in value for key in preferred_keys):
            found.append(value)
        else:
            for child in value.values():
                found.extend(station_payloads(child, preferred_keys=preferred_keys))
    return found


def protocol_wells(protocol_yaml: str) -> list[str]:
    return [
        match.group(1).upper()
        for match in re.finditer(r"\bposition:\s*plate\.([A-Ha-h][1-9][0-2]?)\b", protocol_yaml)
    ]


def payload_well(payload: Mapping[str, Any]) -> str | None:
    for key in ("well", "target_well"):
        value = payload.get(key)
        if isinstance(value, str):
            return value.upper()
    position = payload.get("position")
    if isinstance(position, str):
        match = re.search(r"\bplate\.([A-Ha-h][1-9][0-2]?)\b", position)
        if match:
            return match.group(1).upper()
    return None


def flatten(value: Any, *, prefix: str = "") -> dict[str, Any]:
    if isinstance(value, Mapping):
        result: dict[str, Any] = {}
        for key, child in value.items():
            child_prefix = f"{prefix}.{key}" if prefix else str(key)
            result.update(flatten(child, prefix=child_prefix))
        return result
    if isinstance(value, list):
        return {prefix: json.dumps(value)}
    return {prefix: value}


def at(values: Any, index: int) -> Any:
    return values[index] if isinstance(values, list) and index < len(values) else None


def read_text(path: Path) -> str:
    return path.expanduser().resolve().read_text()


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


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except StationRequestError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
