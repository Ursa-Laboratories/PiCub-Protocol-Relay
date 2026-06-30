# PiCub Protocol Sender

Barebones script for sending `protocol.yaml` directly to the ASMI station worker.

## Run

From this directory:

```bash
python send_asmi_protocol.py --run-id asmi-test-001
```

The script prints the station-worker JSON response and writes:

```text
asmi_result.csv
```

## CSV

The CSV is one row per force sample, with a `well` column. Wells are read from
the `position: plate.<well>` entries in `protocol.yaml` and matched to ASMI
result payloads in protocol order.

Custom output path:

```bash
python send_asmi_protocol.py \
  --run-id asmi-test-001 \
  --output-csv asmi-test-001.csv
```

## Files

- `protocol.yaml` is sent unchanged as `protocol_yaml`
- `gantry_config.yaml` is sent as `gantry_config`
- `deck_config.yaml` is sent as `deck_config`
- `send_asmi_protocol.py` sends the request and writes the CSV

## Flags

Skip the health check:

```bash
python send_asmi_protocol.py --run-id asmi-test-001 --no-health-check
```

Use mock mode:

```bash
python send_asmi_protocol.py --run-id asmi-test-001 --mock-mode
```

## Dependency

```bash
python -m pip install requests
```
