# PiCub Protocol Sender

Reusable CubOS protocol sender for relaying protocol bundles from a controller
machine to a Raspberry Pi station worker. The current ASMI workflow is kept as a
concrete example on top of the generic sender.

## Intended Setup

Run the station worker on the Raspberry Pi attached to the ASMI gantry. From a
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
- `sender/asmi_example/send_asmi_protocol.py` — ASMI example CLI with ASMI defaults and
  force-sample CSV output.
- `sender/asmi_example/protocol.yaml`, `sender/asmi_example/gantry_config.yaml`,
  `sender/asmi_example/deck_config.yaml` — the current ASMI example bundle.
- `station_worker/` — Flask worker that runs on the ASMI Raspberry Pi and
  executes the received CubOS protocol bundle.

## Install

For the controller-side sender only:

```bash
python -m pip install requests
```

The station worker has a bootstrap script that creates `.venv-station`,
installs Flask, PyYAML, and CubOS, then starts the worker.

## Start The ASMI Worker

Run this on the ASMI Raspberry Pi from the repo root:

```bash
./station_worker/start_asmi_worker.sh
```

The script installs from `station_worker/requirements-server.txt`, including:

```text
cubos[asmi] @ git+https://github.com/ursa-laboratories/CubOS.git@main
```

To pass worker flags, append them after the script:

```bash
./station_worker/start_asmi_worker.sh --port 8000
```

The worker listens on `0.0.0.0:8000`, exposes `GET /health`, and accepts
`POST /run-protocol` from machines that can reach the Pi over the local network
or direct Ethernet connection. Run artifacts are written under
`~/picub_protocol_runs`.

If you already have an environment prepared and only want to launch the worker:

```bash
python -m station_worker --config station_worker/configs/stations/asmi.yaml
```

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

## Send The ASMI Example Protocol

From the controller machine, send the bundled ASMI protocol to the default ASMI
Pi (`http://10.210.29.17:8000`):

```bash
python sender/asmi_example/send_asmi_protocol.py --experiment-id asmi-test-001
```

If the Pi has a different local-network or Ethernet IP address, pass it
explicitly:

```bash
python sender/asmi_example/send_asmi_protocol.py \
  --base-url http://<pi-ip-address>:8000 \
  --experiment-id asmi-test-001
```

If running the sender on the same Pi as the worker:

```bash
python sender/asmi_example/send_asmi_protocol.py \
  --base-url http://127.0.0.1:8000 \
  --experiment-id asmi-test-001
```

The ASMI example is a thin wrapper around the generic station client. It prints
the station-worker JSON response and writes:

```text
sender/asmi_example/asmi_result.csv
```

## CSV Output

The CSV is one row per ASMI force sample, with a `well` column. Wells are read
from `position: plate.<well>` entries in `sender/asmi_example/protocol.yaml` and
matched to ASMI result payloads in protocol order.

Custom output path:

```bash
python sender/asmi_example/send_asmi_protocol.py \
  --experiment-id asmi-test-001 \
  --output-csv sender/asmi_example/asmi-test-001.csv
```

## Useful Flags

Skip the sender health check:

```bash
python sender/asmi_example/send_asmi_protocol.py --experiment-id asmi-test-001 --no-health-check
```

Ask the worker to run CubOS in mock mode:

```bash
python sender/asmi_example/send_asmi_protocol.py --experiment-id asmi-test-001 --mock-mode
```

The generic sender has the same health-check and mock-mode flags.

## API Contract

The sender posts this JSON shape to `/run-protocol`:

```json
{
  "run_id": "asmi-test-001",
  "gantry_config": "<gantry yaml text>",
  "deck_config": "<deck yaml text>",
  "protocol_yaml": "<protocol yaml text>",
  "mock_mode": false
}
```

The station worker validates the instrument/command allow-list, writes the
received YAML bundle to the run directory, executes the CubOS protocol, and
returns the result JSON.
