# PiCub Protocol Sender

Unified ASMI protocol sender + ASMI station worker repo.

## Layout

- `sender/` — one-shot client that sends `protocol.yaml`, `gantry_config.yaml`,
  and `deck_config.yaml` to a station worker.
- `station_worker/` — Flask worker that runs on the ASMI Pi and executes the
  received CubOS protocol bundle.

## Install

For the sender only:

```bash
python -m pip install requests
```

The station worker has a bootstrap script that creates `.venv-station`,
installs Flask, PyYAML, and CubOS, then starts the worker.

## Start The ASMI Worker

Run this on the ASMI Pi from the repo root:

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
`POST /run-protocol`. Run artifacts are written under `~/picub_protocol_runs`.

If you already have an environment prepared and only want to launch the worker:

```bash
python -m station_worker --config station_worker/configs/stations/asmi.yaml
```

## Send The Protocol

From this repo, send the bundled ASMI protocol to the default ASMI Pi
(`http://10.210.29.17:8000`):

```bash
python sender/send_asmi_protocol.py --run-id asmi-test-001
```

If running the sender on the same Pi as the worker:

```bash
python sender/send_asmi_protocol.py \
  --asmi-base-url http://127.0.0.1:8000 \
  --run-id asmi-test-001
```

The sender prints the station-worker JSON response and writes:

```text
sender/asmi_result.csv
```

## CSV Output

The CSV is one row per ASMI force sample, with a `well` column. Wells are read
from `position: plate.<well>` entries in `sender/protocol.yaml` and matched to
ASMI result payloads in protocol order.

Custom output path:

```bash
python sender/send_asmi_protocol.py \
  --run-id asmi-test-001 \
  --output-csv sender/asmi-test-001.csv
```

## Useful Flags

Skip the sender health check:

```bash
python sender/send_asmi_protocol.py --run-id asmi-test-001 --no-health-check
```

Ask the worker to run CubOS in mock mode:

```bash
python sender/send_asmi_protocol.py --run-id asmi-test-001 --mock-mode
```

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
