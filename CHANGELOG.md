# Changelog

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
