# ASMI Protocol Sender

Barebones script for sending the local ASMI protocol YAML directly to the
station worker.

## Run

From the repo root:

```bash
python asmi_protocol_sender/send_asmi_protocol.py --run-id asmi-test-001
```

This prints the station-worker JSON response and also writes:

```text
asmi_protocol_sender/asmi_result.csv
```

Or from this directory:

```bash
python send_asmi_protocol.py --run-id asmi-test-001
```

By default it talks to:

```text
http://10.210.29.17:8000
```

## Files

- `protocol.yaml` is the protocol sent as `protocol_yaml`
- `gantry_config.yaml` is sent as `gantry_config`
- `deck_config.yaml` is sent as `deck_config`
- `send_asmi_protocol.py` sends the request

The script reads the YAML files as raw text. It does not parse, render, or
modify the protocol.

## Useful flags

```bash
python asmi_protocol_sender/send_asmi_protocol.py \
  --run-id asmi-a1-test \
  --asmi-base-url http://10.210.29.17:8000 \
  --output-csv asmi_protocol_sender/asmi-a1-test.csv
```

Skip the health check:

```bash
python asmi_protocol_sender/send_asmi_protocol.py --run-id asmi-a1-test --no-health-check
```

Send mock mode:

```bash
python asmi_protocol_sender/send_asmi_protocol.py --run-id asmi-a1-test --mock-mode
```

## Dependency

Requires `requests`:

```bash
python -m pip install requests
```
