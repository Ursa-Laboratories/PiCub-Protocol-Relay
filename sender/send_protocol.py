#!/usr/bin/env python3
"""Send a CubOS protocol YAML bundle directly to any station worker."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from station_sender import (
    ProtocolBundle,
    StationClient,
    StationRequestError,
    print_json,
)

HERE = Path(__file__).resolve().parent


def main() -> int:
    args = parse_args()
    client = StationClient(args.base_url)
    bundle = ProtocolBundle.from_paths(
        gantry_config=args.gantry,
        deck_config=args.deck,
        protocol_yaml=args.protocol,
    )

    if not args.no_health_check:
        print_json("health", client.health(timeout=args.health_timeout_s))

    if args.validate_only:
        validation = client.validate_protocol(bundle, run_id=args.experiment_id, timeout=args.timeout_s)
        print(json.dumps(validation, indent=2, sort_keys=True))
        return 0 if validation.get("valid", False) else 1

    response = client.run_protocol(
        bundle,
        run_id=args.experiment_id,
        mock_mode=args.mock_mode,
        timeout=args.timeout_s,
    )
    print(json.dumps(response, indent=2, sort_keys=True))
    return 0


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Send gantry, deck, and protocol YAMLs unchanged to a station worker."
    )
    parser.add_argument("--base-url", required=True, help="Station worker base URL, e.g. http://pi:8000")
    parser.add_argument("--experiment-id", required=True)
    parser.add_argument("--gantry", type=Path, required=True)
    parser.add_argument("--deck", type=Path, required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--timeout-s", type=float, default=900.0)
    parser.add_argument("--health-timeout-s", type=float, default=3.0)
    parser.add_argument("--mock-mode", action="store_true")
    parser.add_argument("--no-health-check", action="store_true")
    parser.add_argument("--validate-only", action="store_true")
    return parser.parse_args(argv)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except StationRequestError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
