#!/bin/bash

source /scripts/02-common.sh

/scripts/03-install-mono.sh
/scripts/04-install-mt5.sh
/scripts/05-install-python.sh
/scripts/06-install-libraries.sh

log_message "INFO" "Starting Flask API with waitress..."
cd /app
# The MetaTrader5 Python module is process-singleton and NOT thread-safe —
# concurrent mt5.* calls corrupt the response buffer, mt5.last_error() returns the
# wrong thread's error, and mt5.initialize() during a reconnect can race an
# in-flight order_send. MT5SerializeMiddleware holds MT5Connection.api_lock for the
# whole request (the require_mt5_connection ensure_connection probe included), so
# every mt5.* call is serialized regardless of thread count. With that lock in
# place multiple threads are safe: MT5 work stays serialized while lock-free paths
# (401 auth rejections, /health*) stop queueing behind in-flight MT5 calls. The MT5
# IPC round-trip remains the hot-path bottleneck — threads do not parallelize it.
exec wine python -m waitress --host=0.0.0.0 --port=${MT5_API_PORT:-5001} --threads=4 app:app