# Changelog

## [1.7.0](https://github.com/Gabriel-Rockson/axiom/compare/mt5-gateway-v1.6.3...mt5-gateway-v1.7.0) (2026-06-01)


### Features

* **mt5-gateway:** add /state snapshot endpoint and cut per-request IPC ([0d795f3](https://github.com/Gabriel-Rockson/axiom/commit/0d795f3869d8335eeae72969778ddb8dc2ba56a0))

## [1.6.3](https://github.com/Gabriel-Rockson/axiom/compare/mt5-gateway-v1.6.2...mt5-gateway-v1.6.3) (2026-06-01)


### Bug Fixes

* **mt5-gateway:** stop /health from calling MT5 outside the api_lock ([497db4a](https://github.com/Gabriel-Rockson/axiom/commit/497db4a288bd8e47ce2c94e8a9d03529529bcee1))

## [1.6.2](https://github.com/Gabriel-Rockson/axiom/compare/mt5-gateway-v1.6.1...mt5-gateway-v1.6.2) (2026-06-01)


### Performance Improvements

* **mt5-gateway:** cache terminal_info, throttle liveness probe, memoize broker clock symbol ([49e2a9b](https://github.com/Gabriel-Rockson/axiom/commit/49e2a9b5460c8e0f335bba583873d81f380118ef))

## [1.6.1](https://github.com/Gabriel-Rockson/axiom/compare/mt5-gateway-v1.6.0...mt5-gateway-v1.6.1) (2026-05-31)


### Bug Fixes

* **mt5-gateway:** force deploy gateway ([b796bfe](https://github.com/Gabriel-Rockson/axiom/commit/b796bfe3a552c546c9f6f4940749915bb0e59525))

## [1.6.0](https://github.com/Gabriel-Rockson/axiom/compare/mt5-gateway-v1.5.0...mt5-gateway-v1.6.0) (2026-05-26)


### Features

* **mt5-gateway:** require X-API-Key header on non-health endpoints (CR-1) ([d2e278a](https://github.com/Gabriel-Rockson/axiom/commit/d2e278a912f4471ae88e46e6f6690f31268a4759))


### Bug Fixes

* **mt5-gateway:** drop full request body and str(exception) from logs/responses (AW-32, AW-33) ([540e7d4](https://github.com/Gabriel-Rockson/axiom/commit/540e7d416617596a32ac7761c225621261155dcf))
* **mt5-gateway:** preserve existing SL/TP in modify_sl_tp; include symbol (CR-3) ([5966be4](https://github.com/Gabriel-Rockson/axiom/commit/5966be41a6838559288d906c0586364658992270))
* **mt5-gateway:** require BROKER_TIMEZONE; remove UTC fallback (CR-20) ([59465b6](https://github.com/Gabriel-Rockson/axiom/commit/59465b62403bc74ee5bc4ca7c3aa4251262e10c4))
* **mt5-gateway:** serialize MT5 API calls; drop waitress to single thread (CR-2) ([547659c](https://github.com/Gabriel-Rockson/axiom/commit/547659cba6c28c1244c2ce1be1e0eb6cd1ebb6f9))
* use RFC3339 UTC for fetch_data_range; reject naive timestamps (CR-18) ([e513fb0](https://github.com/Gabriel-Rockson/axiom/commit/e513fb067861e8eb6338078e33ba8234e9fe0e4a))

## [1.5.0](https://github.com/Gabriel-Rockson/axiom/compare/mt5-gateway-v1.4.0...mt5-gateway-v1.5.0) (2026-05-14)


### Features

* **axiom:** expose broker timezone via /broker_clock endpoint ([14aac8e](https://github.com/Gabriel-Rockson/axiom/commit/14aac8e1de9d8e45b1651a695aa53f0a8efd739d))

## [1.4.0](https://github.com/Gabriel-Rockson/axiom/compare/mt5-gateway-v1.3.0...mt5-gateway-v1.4.0) (2026-05-13)


### Features

* **mt5-gateway:** auto-discover broker_clock probe symbol from catalog ([d78a7a5](https://github.com/Gabriel-Rockson/axiom/commit/d78a7a50d196deec2c953fa10f26872e10203b0a))
* **mt5-gateway:** cover remaining endpoints in UTC translation sweep ([b6d89f2](https://github.com/Gabriel-Rockson/axiom/commit/b6d89f2d97df1645f9e374677240c799383c4e36))
* **mt5-gateway:** env-pinned broker timezone + background probe ([132d1d7](https://github.com/Gabriel-Rockson/axiom/commit/132d1d7d43df9a5e70a65a3aef63b6c23f83b65a))
* **mt5-gateway:** translate broker-local timestamps to real UTC at boundary ([caf715e](https://github.com/Gabriel-Rockson/axiom/commit/caf715e2db908c1f30c9e1ca40d129df85aa2fba))


### Bug Fixes

* **mt5-gateway:** make broker clock work on Python 3.9 + pandas 1.4 ([27b7bad](https://github.com/Gabriel-Rockson/axiom/commit/27b7bad1a40a007a66042bb050a27d7d431e483a))

## [1.3.0](https://github.com/Gabriel-Rockson/axiom/compare/mt5-gateway-v1.2.1...mt5-gateway-v1.3.0) (2026-04-10)


### Features

* **mt5-gateway:** ensure that the mt5-gateway can take expiry for orders ([d269abb](https://github.com/Gabriel-Rockson/axiom/commit/d269abbf6d1b4e3b16e4111b4ba78b03c6467e4f))

## [1.2.1](https://github.com/Gabriel-Rockson/axiom/compare/mt5-gateway-v1.2.0...mt5-gateway-v1.2.1) (2026-03-10)


### Bug Fixes

* **mt5-gateway:** ensure that position 0 is not used in fetching deals ([61d2cfd](https://github.com/Gabriel-Rockson/axiom/commit/61d2cfdf572623a8ea9e90a6ce8d736427cda73b))

## [1.2.0](https://github.com/Gabriel-Rockson/axiom/compare/mt5-gateway-v1.1.0...mt5-gateway-v1.2.0) (2026-03-08)


### Features

* **mt5-gateway:** add new field for checking terminal algo trading status ([942cd73](https://github.com/Gabriel-Rockson/axiom/commit/942cd73cd4340a78e94090676816449357acb133))

## [1.1.0](https://github.com/Gabriel-Rockson/axiom/compare/mt5-gateway-v1.0.0...mt5-gateway-v1.1.0) (2026-03-08)


### Features

* **mt5-gateway:** prevent thread exhaustion on MT5 symbols_get hang ([059a01f](https://github.com/Gabriel-Rockson/axiom/commit/059a01f2362948997f1a3a72b0076e5f1f49c1ee))

## 1.0.0 (2026-02-28)


### Features

* add per strategy metrics tracking ([f5df87d](https://github.com/Gabriel-Rockson/axiom/commit/f5df87d0a9115c66336869cf54ae2398daf826c6))
* **gateway:** auto enable algo trading on mt5 ([#131](https://github.com/Gabriel-Rockson/axiom/issues/131)) ([4e9de49](https://github.com/Gabriel-Rockson/axiom/commit/4e9de495356e09029ad8cbae6148a66af1fdd272))
* **mt5-gateway:** add partial fill detection and SL/TP confirmation in order response ([dca1b53](https://github.com/Gabriel-Rockson/axiom/commit/dca1b537b2877cf6afc396da7b4d41380d062548))
* **mt5-gateway:** improve observability in orders route ([ce63911](https://github.com/Gabriel-Rockson/axiom/commit/ce639111ac356d77144398a64d080846459e0e43))
* **mt5-gateway:** make datetime be in RFC3339 ([9546a77](https://github.com/Gabriel-Rockson/axiom/commit/9546a778c8cc8a2a9400d9e7a3d280034959d431))
* **mt5-gateway:** rename from mt5-quant-server to mt5-gateway ([c76722e](https://github.com/Gabriel-Rockson/axiom/commit/c76722eba16d65151613a5d55f16b2562ae2c2e2))


### Bug Fixes

* **mt5-gateway:** add mapping of filling type strings to mt5 filling type codes ([fa3f97a](https://github.com/Gabriel-Rockson/axiom/commit/fa3f97a96c65df19f47d7c006391b142be94866f))
* **mt5-gateway:** return proper type ([1077a83](https://github.com/Gabriel-Rockson/axiom/commit/1077a83089eaabd65c2995b53dbc5bbf62a7e814))
