# Changelog

## [1.3.1](https://github.com/roquerodrigo/ha-xiaomi-vacuum/compare/v1.3.0...v1.3.1) (2026-06-01)


### Bug Fixes

* **cloud:** harden fault-text fetch against decode errors and re-polling ([2ffeb54](https://github.com/roquerodrigo/ha-xiaomi-vacuum/commit/2ffeb5421259baaa82e572cefef91e4a686746ee))
* **coordinator:** pass config_entry and surface offline device as not-ready ([2c5249e](https://github.com/roquerodrigo/ha-xiaomi-vacuum/commit/2c5249eb16d6e5feba9c3f7353d5111e4f55b6ae))
* harden cloud, setup and entity robustness from full code review ([ded0b04](https://github.com/roquerodrigo/ha-xiaomi-vacuum/commit/ded0b04d0078575e0e5d81c59b5d3fe100fed3a9))
* **vacuum:** use None-aware status/charging slug lookup ([78ad672](https://github.com/roquerodrigo/ha-xiaomi-vacuum/commit/78ad6720822f3809455b1b544d70a0070a19208b))

## [1.3.0](https://github.com/roquerodrigo/ha-xiaomi-vacuum/compare/v1.2.2...v1.3.0) (2026-05-27)


### Features

* error & consumable sensors, send_command, strict-mypy typing ([cc7de8f](https://github.com/roquerodrigo/ha-xiaomi-vacuum/commit/cc7de8f813a97d671b848e2acbb10bc112f5b386))
* **sensor:** add consumable life sensors (mop, side brush, filter, dust bag) ([e67ee73](https://github.com/roquerodrigo/ha-xiaomi-vacuum/commit/e67ee73c141b2be86ab7bb1db5f746e1d1f367fb))
* **sensor:** add error and error-code sensors with cloud-resolved fault text ([7384720](https://github.com/roquerodrigo/ha-xiaomi-vacuum/commit/7384720739023e6011ffde84af0dc853b40be13b))
* **sensor:** add real device-status sensor ([7316a9f](https://github.com/roquerodrigo/ha-xiaomi-vacuum/commit/7316a9f316b9bec7421390279544d3bf4a4cc85f))
* **sensor:** add real device-status sensor ([3e540bd](https://github.com/roquerodrigo/ha-xiaomi-vacuum/commit/3e540bd2153e11b8dc08d8c5c05916218f555ee9))
* **vacuum:** resume in-progress clean on start instead of restarting ([ccdeec8](https://github.com/roquerodrigo/ha-xiaomi-vacuum/commit/ccdeec8b4a13ff6654bd5419c204673db286c6a5))
* **vacuum:** resume in-progress clean on start instead of restarting ([67dec3b](https://github.com/roquerodrigo/ha-xiaomi-vacuum/commit/67dec3b9edd2f43261190b92fea98dcb7b6c9333))
* **vacuum:** support send_command for extra MIoT actions ([ada1e70](https://github.com/roquerodrigo/ha-xiaomi-vacuum/commit/ada1e70218616a15b89f40818d9b4b61e3d58bfc))


### Bug Fixes

* derive live fault from Fault Ids and reflect it in state ([756ada3](https://github.com/roquerodrigo/ha-xiaomi-vacuum/commit/756ada3750bb31ae3354c49c29122d412084dc4c))
* drive vacuum error state from the active fault, not status ([c83eeea](https://github.com/roquerodrigo/ha-xiaomi-vacuum/commit/c83eeea703dcf1c31d0958ebc1c94654b6137d10))
* **sensor:** track main brush instead of dust bag to match the app ([155df6d](https://github.com/roquerodrigo/ha-xiaomi-vacuum/commit/155df6d940874b41e7c343f3a5e37e5d2c9e9a4e))


### Documentation

* add Xiaomi cloud API and d109gl miot-spec reference ([28704aa](https://github.com/roquerodrigo/ha-xiaomi-vacuum/commit/28704aa1dd20300e7954a702db868635581e7b14))
* **readme:** add separators around the HACS badge ([a4bd660](https://github.com/roquerodrigo/ha-xiaomi-vacuum/commit/a4bd660aba0941907f3a2a19e7e83c9974a4a62e))
* **readme:** reflect cloud-assisted setup, map and error sensors ([57c71d9](https://github.com/roquerodrigo/ha-xiaomi-vacuum/commit/57c71d9c6213913e5db5b0ac25b3a6bee063fa4b))
* **readme:** reflect cloud-assisted setup, map and error sensors ([447a4c1](https://github.com/roquerodrigo/ha-xiaomi-vacuum/commit/447a4c13ea1ded0816698aface857cdc3aab9cba))

## [1.2.2](https://github.com/roquerodrigo/ha-xiaomi-vacuum/compare/v1.2.1...v1.2.2) (2026-05-25)


### Documentation

* add CI and HACS badges ([17d4a52](https://github.com/roquerodrigo/ha-xiaomi-vacuum/commit/17d4a5225c76b75eb94ecaa21c3dc8020afbedc8))
* add CI and HACS badges ([c53c3ab](https://github.com/roquerodrigo/ha-xiaomi-vacuum/commit/c53c3abeefb7dd88c91d84465162236c8552cb63))

## [1.2.1](https://github.com/roquerodrigo/ha-xiaomi-vacuum/compare/v1.2.0...v1.2.1) (2026-05-22)


### Dependencies

* **deps:** bump the python-production group across 1 directory with 2 updates ([023f2ee](https://github.com/roquerodrigo/ha-xiaomi-vacuum/commit/023f2ee0d68c1f6536c499c5195e3033e18b88fb))

## [1.2.0](https://github.com/roquerodrigo/ha-xiaomi-vacuum/compare/v1.1.1...v1.2.0) (2026-05-17)


### Features

* apply Forest Canopy theme colors to vacuum map ([c937d91](https://github.com/roquerodrigo/ha-xiaomi-vacuum/commit/c937d9123c6b621de87cf7d7a9ae72297ede5628))


### Dependencies

* bump types-requests ([bb03315](https://github.com/roquerodrigo/ha-xiaomi-vacuum/commit/bb033152255c8bdcfcb53b22a8f2e43931207336))
* **deps:** bump ruff in the python-production group ([5d7349f](https://github.com/roquerodrigo/ha-xiaomi-vacuum/commit/5d7349f9f21262a4d68531e850722c4d0fdbc7be))
* **deps:** bump the python-production group across 1 directory with 2 updates ([78e4403](https://github.com/roquerodrigo/ha-xiaomi-vacuum/commit/78e4403c50589fa348b5a98645ded00808e91a6d))


### Documentation

* standardize CODE_STYLE.md template ([e6dec4c](https://github.com/roquerodrigo/ha-xiaomi-vacuum/commit/e6dec4c8f24987aedac83d89caeb18166875eb4c))
* standardize CODE_STYLE.md template ([bd18a44](https://github.com/roquerodrigo/ha-xiaomi-vacuum/commit/bd18a446e855b9d8141c44bba9e8eaa183cdb590))

## [1.1.1](https://github.com/roquerodrigo/ha-xiaomi-vacuum/compare/v1.1.0...v1.1.1) (2026-05-07)


### Bug Fixes

* migrate battery from vacuum to dedicated sensor ([58009ed](https://github.com/roquerodrigo/ha-xiaomi-vacuum/commit/58009edd47c9b670a188e1f17208217a72dec65f))
* resolve type errors and align HA pinning with metro-sp pipeline ([192997c](https://github.com/roquerodrigo/ha-xiaomi-vacuum/commit/192997c3a01514c9f33c0bf12bd84524dba75029))
* **tests:** install integration runtime deps in CI ([f401306](https://github.com/roquerodrigo/ha-xiaomi-vacuum/commit/f4013068b9d239c2275fa41476fca3b6656a9e74))


### Dependencies

* **deps:** bump mypy from 1.18.2 to 2.0.0 ([1aff58c](https://github.com/roquerodrigo/ha-xiaomi-vacuum/commit/1aff58cabec7e2881eb1caa4cbf1970339c3da01))
* **deps:** update pip requirement from &gt;=26.1 to &gt;=26.1.1 ([c3e901c](https://github.com/roquerodrigo/ha-xiaomi-vacuum/commit/c3e901c59da3c063c287ba796c4a76e679e0a97a))
* **deps:** update pycryptodome requirement from &gt;=3.20 to &gt;=3.23.0 ([ec8b01e](https://github.com/roquerodrigo/ha-xiaomi-vacuum/commit/ec8b01e2c4b6a2f74242907b0ec0c9e2b622b134))
