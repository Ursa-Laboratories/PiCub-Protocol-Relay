#!/usr/bin/env sh
set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
VENV_DIR=${PICUB_STATION_VENV:-"$ROOT_DIR/.venv-station"}
PYTHON_BIN=${PYTHON:-python3}
CONFIG=${PICUB_STATION_CONFIG:-"$ROOT_DIR/station_worker/configs/stations/asmi.yaml"}

if [ ! -x "$VENV_DIR/bin/python" ]; then
  "$PYTHON_BIN" -m venv "$VENV_DIR"
fi

"$VENV_DIR/bin/python" -m pip install --upgrade pip
"$VENV_DIR/bin/python" -m pip install -r "$ROOT_DIR/station_worker/requirements-server.txt"

exec "$VENV_DIR/bin/python" -m station_worker --config "$CONFIG" "$@"
