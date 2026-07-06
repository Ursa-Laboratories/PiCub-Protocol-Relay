# PiCub Protocol Sender

Reusable CubOS protocol sender for relaying protocol bundles from a controller
machine to a Raspberry Pi station worker.

## Intended Setup

Run the station worker on the Raspberry Pi attached to the instrument. From a
controller laptop or workstation on the same local network, send the protocol
bundle to that Pi over HTTP. The network can be the lab LAN, a direct Ethernet
connection, or any other local network where the controller can reach the Pi's
IP address.

Typical flow:

1. On the Raspberry Pi attached to the instrument, start `station_worker`.
2. On the controller machine, run a sender with its base URL pointing at the Pi,
   for example `http://10.210.29.17:8000`.
3. The sender posts the gantry YAML, deck YAML, and protocol YAML to the Pi.
4. The Pi runs the protocol locally through CubOS and returns the result JSON.

## Layout

- `sender/station_sender.py` — reusable station-worker HTTP client and protocol
  bundle model.
- `sender/send_protocol.py` — generic one-shot CLI for any station worker that
  accepts CubOS protocol bundles.
- `station_worker/` — Flask worker that runs on a station Raspberry Pi and
  executes received CubOS protocol bundles.

## Install

For the controller-side sender only:

```bash
python -m pip install requests
```

## Start The Station Worker

Install the worker dependencies before launching it:

```bash
python -m pip install -r station_worker/requirements-server.txt
```

Run the worker on the station Raspberry Pi from the repo root:

```bash
python -m station_worker --config station_worker/configs/stations/<station>.yaml
```

The worker listens on `0.0.0.0:8000`, exposes `GET /health`, and accepts
`POST /run-protocol` from machines that can reach the Pi over the local network
or direct Ethernet connection. Run artifacts are written under
`~/picub_protocol_runs`.

## Send A Protocol With The Generic Sender

Use `sender/send_protocol.py` when you want to send any CubOS gantry/deck/protocol
bundle to a station worker:

```bash
python sender/send_protocol.py \
  --base-url http://<station-ip-address>:8000 \
  --experiment-id protocol-test-001 \
  --gantry path/to/gantry_config.yaml \
  --deck path/to/deck_config.yaml \
  --protocol path/to/protocol.yaml
```

Validate the bundle without running hardware:

```bash
python sender/send_protocol.py \
  --base-url http://<station-ip-address>:8000 \
  --experiment-id protocol-test-001 \
  --gantry path/to/gantry_config.yaml \
  --deck path/to/deck_config.yaml \
  --protocol path/to/protocol.yaml \
  --validate-only
```

The generic sender prints the station-worker JSON response. It does not create
instrument-specific exports.

## Useful Flags

Skip the sender health check:

```bash
python sender/send_protocol.py \
  --base-url http://<station-ip-address>:8000 \
  --experiment-id protocol-test-001 \
  --gantry path/to/gantry_config.yaml \
  --deck path/to/deck_config.yaml \
  --protocol path/to/protocol.yaml \
  --no-health-check
```

Ask the worker to run CubOS in mock mode:

```bash
python sender/send_protocol.py \
  --base-url http://<station-ip-address>:8000 \
  --experiment-id protocol-test-001 \
  --gantry path/to/gantry_config.yaml \
  --deck path/to/deck_config.yaml \
  --protocol path/to/protocol.yaml \
  --mock-mode
```

## API Contract

The sender posts this JSON shape to `/run-protocol`:

```json
{
  "run_id": "protocol-test-001",
  "gantry_config": "<gantry yaml text>",
  "deck_config": "<deck yaml text>",
  "protocol_yaml": "<protocol yaml text>",
  "mock_mode": false
}
```

The station worker validates the instrument/command allow-list, writes the
received YAML bundle to the run directory, executes the CubOS protocol, and
returns the result JSON.
