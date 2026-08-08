# MT5 Gateway

HTTP API for MetaTrader 5 running in Wine on Linux.

Based on [slowfound's metatrader5-quant-server-python](https://github.com/slowfound/metatrader5-quant-server-python/tree/chapter-1) and his [YouTube tutorial series](https://youtube.com/playlist?list=PLotEOI0Sz3OzdSp7qR6vHs8EYnmQwqWAF).

## Requirements

- Docker and Docker Compose ([Install Docker](https://docs.docker.com/get-docker/))

## Setup

1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` with your VNC password and, at minimum, these two required values:
   - `MT5_API_KEY` — the gateway refuses to start without it. Generate one with:
     ```bash
     python -c "import secrets; print(secrets.token_urlsafe(32))"
     ```
   - `BROKER_TIMEZONE` — your broker's IANA timezone (e.g. `Europe/Athens`). The gateway refuses to start without it too — see the comment in `.env.example` for why.

3. Start the server:
   ```bash
   docker compose up
   ```

4. **Important**: Connect to VNC at `localhost:10004` using your VNC password. Login to MT5 with your broker account through the GUI. The trading/data endpoints won't work until you're logged in — but the gateway itself starts and reports healthy right away; see [Health Checks](#health-checks).

5. API is now available at `http://localhost:10003`

## Ports

- **10004** - VNC server for MT5 GUI access
- **10003** - HTTP API

## Authentication

Every endpoint except `/health`, `/health/live`, and `/health/ready` requires an
`X-API-Key` header matching `MT5_API_KEY`. Requests without it (or with the
wrong key) get a `401`.

## Health Checks

- `/health/live` — always `200` once the process is up. Doesn't touch MT5, so
  it's safe to use as a container liveness probe before you've logged into MT5.
- `/health/ready` — `200` once MT5 is connected, `503` otherwise. Use this if
  you need to gate traffic on MT5 actually being logged in.
- `/health` — full status: connection state, account login, uptime, last error.

On a cold start the gateway retries the MT5 connection a few times before
giving up and serving anyway (it never blocks the API on login) — each retry
can take up to ~60s while MT5 isn't logged in, so the container can take a
few minutes to open its port on first boot. The bundled `docker-compose.yml`
sets a generous `start_period`/`retries` on its healthcheck to cover that; if
you're wiring your own orchestrator's health probe, give it similar slack and
point it at `/health/live`, not an endpoint that requires MT5.

## Running Multiple Instances

To run more than one MT5 account, give each its own `.env` (a different
`PASSWORD`, `MT5_API_KEY`, etc.) and a distinct `MT5_GATEWAY_VNC_PORT` /
`MT5_GATEWAY_API_PORT` pair, then start each under its own compose project
name:
```bash
docker compose -p mt5-gateway-account2 --env-file .env.account2 up -d
```

## API Documentation

Full interactive API documentation available at `http://localhost:10003/apidocs` after starting the server.

The docs themselves don't require the API key. To call endpoints from the docs,
click **Authorize** (top right), paste your `MT5_API_KEY`, and "Try it out"
requests will carry the `X-API-Key` header automatically. Set `MT5_DOCS_USER` and
`MT5_DOCS_PASSWORD` to put an HTTP Basic login in front of the docs.

## Example Usage

All of these require the `X-API-Key` header from [Authentication](#authentication).

Get account info:
```bash
curl http://localhost:10003/account \
  -H "X-API-Key: $MT5_API_KEY"
```

Fetch 100 bars of data:
```bash
curl "http://localhost:10003/fetch_data_pos?symbol=EURUSD&timeframe=M1&num_bars=100" \
  -H "X-API-Key: $MT5_API_KEY"
```

Place a market order:
```bash
curl -X POST http://localhost:10003/order \
  -H "X-API-Key: $MT5_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "EURUSD",
    "volume": 0.01,
    "type": "BUY"
  }'
```

## Credits

Built on the foundation laid by [slowfound](https://github.com/slowfound) in the [metatrader5-quant-server-python](https://github.com/slowfound/metatrader5-quant-server-python) project.
