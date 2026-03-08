# Changelog

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
