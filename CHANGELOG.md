# Changelog

## [2.1.0](https://github.com/roquerodrigo/ha-xiaomi-vacuum/compare/v2.0.1...v2.1.0) (2026-08-07)


### Features

* add config entry diagnostics with credential redaction ([34d72bb](https://github.com/roquerodrigo/ha-xiaomi-vacuum/commit/34d72bb12bf0ca36c1258e79389d8c51b76c59b1))


### Bug Fixes

* drop the finished QR task before requesting a fresh login ([d7856f1](https://github.com/roquerodrigo/ha-xiaomi-vacuum/commit/d7856f10841cbb8768bd427fec9d6433f32417fb))


### Code Refactoring

* expose a public session API on the cloud connector ([33cec18](https://github.com/roquerodrigo/ha-xiaomi-vacuum/commit/33cec1894516c4812fa4670c2c8a69d4deb2738c))
* make icons.json the single source of entity icons ([f9a280a](https://github.com/roquerodrigo/ha-xiaomi-vacuum/commit/f9a280a7423f8d1eb3f70eb4580f3cfcf19e5edf))
* name binary sensor classes after their platform ([27ee7c0](https://github.com/roquerodrigo/ha-xiaomi-vacuum/commit/27ee7c02fe18c616cf9975874ec71ec6a8d5f49e))
* replace bare type and object annotations with precise types ([70398b8](https://github.com/roquerodrigo/ha-xiaomi-vacuum/commit/70398b8fef7d9c9811db47e5a380927d726288e0))


### Documentation

* describe the reauth flow and the uv-based pre-commit hooks ([d9539fa](https://github.com/roquerodrigo/ha-xiaomi-vacuum/commit/d9539fa9492bc5e9c1be6a0083c0a585e503f00c))


### Continuous Integration

* run checks on pull requests targeting any branch ([aa813d9](https://github.com/roquerodrigo/ha-xiaomi-vacuum/commit/aa813d96fe818f7db3cb5517aabb46f32bb62602))
* run code scanning on pull requests targeting any branch ([68256c0](https://github.com/roquerodrigo/ha-xiaomi-vacuum/commit/68256c0035aff94a87de723bfa5bf3e61c012da9))


### Tests

* enforce translation parity across locales and entities ([c0e9bc7](https://github.com/roquerodrigo/ha-xiaomi-vacuum/commit/c0e9bc704fc02913e0a2c721776e6fa0a53dd1e8))
* use English fixture and entity names ([ba367d2](https://github.com/roquerodrigo/ha-xiaomi-vacuum/commit/ba367d285014c594cc6f204533c684de25236119))


### Miscellaneous Chores

* run pre-commit through uv and refresh the lock file ([1f3cd72](https://github.com/roquerodrigo/ha-xiaomi-vacuum/commit/1f3cd7227a21c63c066ee33790a5e1c899a71492))

## [2.0.1](https://github.com/roquerodrigo/ha-xiaomi-vacuum/compare/v2.0.0...v2.0.1) (2026-08-04)


### Bug Fixes

* clear repair issues when the config entry is removed ([1096940](https://github.com/roquerodrigo/ha-xiaomi-vacuum/commit/1096940177617b46cab675890e98f23b75545a13))
* derive the charging state from the model spec ([0ec7dd8](https://github.com/roquerodrigo/ha-xiaomi-vacuum/commit/0ec7dd8818474d240e81942a855db82e77594b85))
* drop quotes around translation placeholders ([09951c3](https://github.com/roquerodrigo/ha-xiaomi-vacuum/commit/09951c3d3522d71719df5472fea8072eea3ce045))
* drop stale QR state before refreshing the login code ([d4b0108](https://github.com/roquerodrigo/ha-xiaomi-vacuum/commit/d4b01086a551bfbf8eeb007ced2920ff30fd0d65))
* expose the X20 Max off mop-water level ([38e8bb7](https://github.com/roquerodrigo/ha-xiaomi-vacuum/commit/38e8bb7efe3529e747431810003f1718ce51d8a9))
* fall back to local transport when the cloud rejects the session mid-action ([475c77a](https://github.com/roquerodrigo/ha-xiaomi-vacuum/commit/475c77ac08ccc6af4e9526bd202aa32ffa5356e9))
* isolate the QR login cookies in a dedicated client session ([32bdbed](https://github.com/roquerodrigo/ha-xiaomi-vacuum/commit/32bdbed713862b63dc0f028a8f51e4e5f6ef03ee))
* prompt reauth when the fault-text feed rejects the session ([bff738a](https://github.com/roquerodrigo/ha-xiaomi-vacuum/commit/bff738a34d8619e187429efb1502215dce4afe76))
* raise the cannot_connect repair only for communication errors ([3d3fb1d](https://github.com/roquerodrigo/ha-xiaomi-vacuum/commit/3d3fb1d67eb4352e40f391da4343873eddf3f4df))
* redact the signed query string from cloud connection errors ([308c5ea](https://github.com/roquerodrigo/ha-xiaomi-vacuum/commit/308c5ea746a5ee1ce3e68fe970c7d8b65f9f96c0))
* reject send_command parameters instead of silently dropping them ([8da150a](https://github.com/roquerodrigo/ha-xiaomi-vacuum/commit/8da150a534fa2c38ba3578159acacff4f2c118f4))
* rename the pt-BR mop pad sensor to "Mop" ([61ea9b8](https://github.com/roquerodrigo/ha-xiaomi-vacuum/commit/61ea9b8f561a4d5d5b20ed5ed67fd5d0e6a0a3a9))
* request a fresh login when the cloud session is rejected during discovery ([6759f00](https://github.com/roquerodrigo/ha-xiaomi-vacuum/commit/6759f00be7dd297374dac9f0f03d3edc0cd10cfc))
* retry map parsing when rendering a new blob fails ([197c6d2](https://github.com/roquerodrigo/ha-xiaomi-vacuum/commit/197c6d2666774358a8032b60a5a469443d20ed20))
* retry setup when the Xiaomi cloud is unreachable ([60c09fd](https://github.com/roquerodrigo/ha-xiaomi-vacuum/commit/60c09fd0a7011cfcadc07aee09e2be7118e8eab6))
* return no segments while the vacuum has been offline since startup ([c7c3eb0](https://github.com/roquerodrigo/ha-xiaomi-vacuum/commit/c7c3eb0e2f6f7fae027a6953e3d7ba0eb5a1e408))
* route fan speed writes through the guarded property setter ([2d7bb55](https://github.com/roquerodrigo/ha-xiaomi-vacuum/commit/2d7bb55949a25e5b47c012388bc7a936b39d8271))
* separate transient Xiaomi cloud failures from session errors ([e61fd18](https://github.com/roquerodrigo/ha-xiaomi-vacuum/commit/e61fd18c0c18a2bcfcad46cdcedfe5b4a4181f2b))
* tie the optimistic refresh task to the config entry ([e2899f0](https://github.com/roquerodrigo/ha-xiaomi-vacuum/commit/e2899f0ca5b0d611df6d42554195a503a473422b))
* translate the unknown send_command error ([faa4553](https://github.com/roquerodrigo/ha-xiaomi-vacuum/commit/faa455378a34282df616ef7a9ee1e8593b806712))
* wrap malformed cloud responses in the cloud error hierarchy ([b49b410](https://github.com/roquerodrigo/ha-xiaomi-vacuum/commit/b49b41069fac5ef512068417d52dbd3fe269d4cf))


### Code Refactoring

* compute fan speed list and device info as properties ([8d68ece](https://github.com/roquerodrigo/ha-xiaomi-vacuum/commit/8d68ece770e1bd4174ec400eb718351fd71d9666))
* drop the redundant entry reload listener ([0a7c87e](https://github.com/roquerodrigo/ha-xiaomi-vacuum/commit/0a7c87e74b03178f12e9f38c36f7ef410768d335))
* expose the resolved cloud device through a public property ([76a81cd](https://github.com/roquerodrigo/ha-xiaomi-vacuum/commit/76a81cda4675a249f0ce96eefdddb53c3ceb66c8))


### Documentation

* document the region selector, reconfigure and reauth flows ([ba72c30](https://github.com/roquerodrigo/ha-xiaomi-vacuum/commit/ba72c30dc46cb70e131523f7d24f0097c1d0aaa8))
* document the status sensor, binary sensors and the mop-pad guard ([9702fbe](https://github.com/roquerodrigo/ha-xiaomi-vacuum/commit/9702fbe6a0cf86dd0510314fd370de3086e3b345))
* drop the dead spec JSON reference ([36233a4](https://github.com/roquerodrigo/ha-xiaomi-vacuum/commit/36233a40194ff69ac159bfebf37c04f302ad816e))
* point the CI notes at the shared workflows repository ([5ea8f2e](https://github.com/roquerodrigo/ha-xiaomi-vacuum/commit/5ea8f2eebadbc22db02a11f8f716269f56570c89))
* point the mapped fault property at Fault Ids ([d7a910c](https://github.com/roquerodrigo/ha-xiaomi-vacuum/commit/d7a910ca9942bfc24e27c661ed8aafd1f00801a9))
* replace the broken scripts/setup instruction with uv sync ([8be5c18](https://github.com/roquerodrigo/ha-xiaomi-vacuum/commit/8be5c1879ffda745e2ff1542a58356d464bebc5f))
* state the enforced 90% coverage gate in CODE_STYLE.md ([870dac0](https://github.com/roquerodrigo/ha-xiaomi-vacuum/commit/870dac02c7a708001c448e775aa8b4b2dbfd0ca1))


### Miscellaneous Chores

* align the map parser upper bound with the manifest ([edd8c56](https://github.com/roquerodrigo/ha-xiaomi-vacuum/commit/edd8c56045ca472c5fec777ac047f35ff525e719))
* sync uv.lock project version with the 2.0.0 release ([4848b88](https://github.com/roquerodrigo/ha-xiaomi-vacuum/commit/4848b88e79913dad34cdc7daa552c134454e7e5b))

## [2.0.0](https://github.com/roquerodrigo/ha-xiaomi-vacuum/compare/v1.6.0...v2.0.0) (2026-08-03)


### ⚠ BREAKING CHANGES

* ModelSpec constructor signature changed. Use a single `status: dict[int, StatusDef]` instead of separate `status_to_activity` / `status_slugs` / `idle_statuses` arguments; drop `has_dust_arrest` / `has_sweep_route` / `has_obstacle_avoidance` (now derived from `actions.*` and `property_mapping`). Read access via the legacy names still works (computed properties).

### Features

* expose mop-pad status, refuse mop modes without it ([181b586](https://github.com/roquerodrigo/ha-xiaomi-vacuum/commit/181b5868c56151caeaa7c521a16369c98f156e6d))
* support more vacuum models ([0aeccb4](https://github.com/roquerodrigo/ha-xiaomi-vacuum/commit/0aeccb4fb0ad42343bfda1668b759bfd88a12bde))


### Bug Fixes

* address PR [#61](https://github.com/roquerodrigo/ha-xiaomi-vacuum/issues/61) review blockers ([33bf4f8](https://github.com/roquerodrigo/ha-xiaomi-vacuum/commit/33bf4f8c8f87a2ee1eacf406eab8f6ba4c3ba635))
* refuse mop modes when the pad is reported as 0 ([8a6a3cc](https://github.com/roquerodrigo/ha-xiaomi-vacuum/commit/8a6a3cc6867d71060efd3018dd0afa1f306fa5eb))


### Code Refactoring

* address PR [#61](https://github.com/roquerodrigo/ha-xiaomi-vacuum/issues/61) review follow-ups ([#4](https://github.com/roquerodrigo/ha-xiaomi-vacuum/issues/4)-[#10](https://github.com/roquerodrigo/ha-xiaomi-vacuum/issues/10)) ([3cf0c65](https://github.com/roquerodrigo/ha-xiaomi-vacuum/commit/3cf0c6597a65c917b608240d2cf2370503d547e4))
* self-review fixes for mop-pad feature ([#1](https://github.com/roquerodrigo/ha-xiaomi-vacuum/issues/1)-4, 6) ([77ed781](https://github.com/roquerodrigo/ha-xiaomi-vacuum/commit/77ed781ee3e5fde54e9dd6656b42e8f2f71ac630))
* split the model spec into a package ([5cf7001](https://github.com/roquerodrigo/ha-xiaomi-vacuum/commit/5cf70017b93a8fd4a9f021432c8a262388599cb4))


### Development Dependencies

* **deps-dev:** bump pre-commit ([4e24b8c](https://github.com/roquerodrigo/ha-xiaomi-vacuum/commit/4e24b8c432d3de194cb2c6e29e8ae6d55df0724d))
* **deps-dev:** bump ruff ([251e72e](https://github.com/roquerodrigo/ha-xiaomi-vacuum/commit/251e72e3e2f4daf2aabd5205f5234607865f9f31))
* **deps-dev:** bump ruff in the python-development group ([ddb7cb7](https://github.com/roquerodrigo/ha-xiaomi-vacuum/commit/ddb7cb71e57dfe95f236da75760769cf7a074cbe))
* **deps-dev:** bump the python-development group with 2 updates ([3f7444f](https://github.com/roquerodrigo/ha-xiaomi-vacuum/commit/3f7444f0cf3ec5f9a957f3847d863f50e6c2d22c))


### Documentation

* add CLAUDE.md ([6b3e04d](https://github.com/roquerodrigo/ha-xiaomi-vacuum/commit/6b3e04d05bc99a449c3a6eed339d62a6b6c18d3f))
* correct the CI and repairs sections ([b3effba](https://github.com/roquerodrigo/ha-xiaomi-vacuum/commit/b3effba49eb8c7ac8b9db335ffec063b00fdaaaa))
* **test:** address self-review items [#1](https://github.com/roquerodrigo/ha-xiaomi-vacuum/issues/1)-[#3](https://github.com/roquerodrigo/ha-xiaomi-vacuum/issues/3) ([414f5d6](https://github.com/roquerodrigo/ha-xiaomi-vacuum/commit/414f5d671013eb71045d9d1759c170ea4350f175))


### Continuous Integration

* assign open issues and pull requests to the repository owner ([9b0e132](https://github.com/roquerodrigo/ha-xiaomi-vacuum/commit/9b0e132ce6cf8bb0852227a32ddec03184351a0f))
* call the shared auto-assign workflow instead of duplicating it ([234798f](https://github.com/roquerodrigo/ha-xiaomi-vacuum/commit/234798fae3fc947b4725779e2bf0afc7663381cf))
* drop the auto-assign job now handled by its own workflow ([6539271](https://github.com/roquerodrigo/ha-xiaomi-vacuum/commit/65392715326f9c9cc82075f6a4f1974dadceeb59))
* drop the blank line left by the removed job ([b3dcdad](https://github.com/roquerodrigo/ha-xiaomi-vacuum/commit/b3dcdade893be91bf77ad9815040c432356ba042))
* split the CI workflow into one file per concern ([112cff6](https://github.com/roquerodrigo/ha-xiaomi-vacuum/commit/112cff6945b6b3f91bd0b4a9b6d97712138e9bd9))


### Miscellaneous Chores

* **deps-dev:** bump ruff to 0.16.0 ([db15001](https://github.com/roquerodrigo/ha-xiaomi-vacuum/commit/db150019deeb6e7d8790fdfe00cd4e9267866448))
* move CI to the shared workflows repository ([5f3ac5f](https://github.com/roquerodrigo/ha-xiaomi-vacuum/commit/5f3ac5f3e2fa5e786c3acfb593e80727e674ed31))
* release on every conventional commit type ([521d174](https://github.com/roquerodrigo/ha-xiaomi-vacuum/commit/521d174acc1f93cd4366a1af612d8016a9083b31))

## [1.6.0](https://github.com/roquerodrigo/ha-xiaomi-vacuum/compare/v1.5.0...v1.6.0) (2026-07-10)


### Features

* **config:** add a reconfigure flow to change the cloud region ([85554e4](https://github.com/roquerodrigo/ha-xiaomi-vacuum/commit/85554e4fc84ebf49d06c4d74d2091d2a5e6d7b52))
* **config:** let the user pick the Xiaomi cloud region ([7ff14b1](https://github.com/roquerodrigo/ha-xiaomi-vacuum/commit/7ff14b1437796ac576eb3a4003655a491ee25604)), closes [#50](https://github.com/roquerodrigo/ha-xiaomi-vacuum/issues/50)
* **map:** recover cleaning map via reauth when the cloud session expires ([6920da2](https://github.com/roquerodrigo/ha-xiaomi-vacuum/commit/6920da2d62b7de4178446e01bba53e8812ca1e53))

## [1.5.0](https://github.com/roquerodrigo/ha-xiaomi-vacuum/compare/v1.4.0...v1.5.0) (2026-07-03)


### Features

* add battery_charging binary sensor ([2b7401c](https://github.com/roquerodrigo/ha-xiaomi-vacuum/commit/2b7401c5b836f0e85b918f1a3248639568fbb04b))
* expose battery charging state on the battery sensor ([97fa1a1](https://github.com/roquerodrigo/ha-xiaomi-vacuum/commit/97fa1a1a4897f63a13b25fe94e0e4ea5efda9033))

## [1.4.0](https://github.com/roquerodrigo/ha-xiaomi-vacuum/compare/v1.3.1...v1.4.0) (2026-06-07)


### Features

* tolerate offline vacuum at setup, keep map served and raise repair issue ([d8b2740](https://github.com/roquerodrigo/ha-xiaomi-vacuum/commit/d8b2740fc72bde668ce97fb708099e7f726233b3))
* tolerate offline vacuum at setup, keep map served and raise repair issue ([2548ac7](https://github.com/roquerodrigo/ha-xiaomi-vacuum/commit/2548ac7542dcf93f8eab86cc7fcf4ba81d789e52))

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
