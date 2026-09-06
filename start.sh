#!/usr/bin/env bash
set -euo pipefail

python -m flask --app run.py db upgrade
python -m flask --app run.py identity bootstrap-customer-owner
exec gunicorn --bind "0.0.0.0:${PORT:-10000}" --workers 2 --threads 4 --timeout 120 run:app
