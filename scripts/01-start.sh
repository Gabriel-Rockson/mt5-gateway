#!/bin/bash

source /scripts/02-common.sh

/scripts/03-install-mono.sh
/scripts/04-install-mt5.sh
/scripts/05-install-python.sh
/scripts/06-install-libraries.sh

log_message "INFO" "Starting Flask API with waitress..."
cd /app
# --threads=1 because the MetaTrader5 Python module maintains a single connection
# per process and is NOT thread-safe — concurrent mt5.* calls corrupt the response
# buffer, mt5.last_error() returns the wrong thread's error, and mt5.initialize()
# during a reconnect can race with an in-flight order_send. The Wine-bridged MT5
# API is the request bottleneck regardless, so parallelism here is illusory.
# Do not raise this without first wrapping every mt5.* call in MT5Connection.api_lock.
exec wine python -m waitress --host=0.0.0.0 --port=${MT5_API_PORT:-5001} --threads=1 app:app