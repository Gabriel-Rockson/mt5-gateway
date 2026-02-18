#!/bin/bash

source /scripts/02-common.sh

/scripts/03-install-mono.sh
/scripts/04-install-mt5.sh
/scripts/05-install-python.sh
/scripts/06-install-libraries.sh

log_message "INFO" "Starting Flask API with waitress..."
cd /app
exec wine python -m waitress --host=0.0.0.0 --port=${MT5_API_PORT:-5001} --threads=4 app:app