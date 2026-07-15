# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.2.0] - 2026-07-15

### Added
- Redesigned graphical configuration experience using native Home Assistant selectors
  (dropdowns, number steppers, boolean toggles, URL field and template editor)
- Menu-based navigation (`async_show_menu`) for headers, sensors and options instead of
  action dropdowns
- 18 additional UI translations (cs, el, es, fr, hu, it, ja, ko, nl, pl, pt, pt-BR, ro,
  ru, tr, uk, zh-cn, zh-tw) (#41)

### Changed
- Minimum supported Home Assistant version is now 2026.4.4
- Migrated to the typed `ConfigEntry.runtime_data` storage pattern
- HTTP requests now use Home Assistant's managed client session
  (`async_create_clientsession`) for proper lifecycle handling
- Response parsing (JSON/HTML/XML) is offloaded to the executor to avoid blocking the
  event loop
- Entities now use the typed `DeviceInfo` helper and shared device information
- Removed the redundant `aiohttp` requirement (provided by Home Assistant core)

### Fixed
- Fixed an invalid `device_class` being stored when "none" was selected, which caused
  Home Assistant warnings

### Dependencies
- Bump `actions/checkout` from 6 to 7 (#53)
- Bump `black` from 26.3.0 to 26.3.1 (#43)
- Bump `mypy` from 1.19.1 to 1.20.2 (#52)
- Bump `pytest` from 9.0.2 to 9.0.3 (#48)
- Bump `pytest-homeassistant-custom-component` from 0.13.317 to 0.13.325 (#50)
- Update `homeassistant` dev requirement to >=2026.4.4 (#51)

## [1.1.0] - 2026-03-08

### Fixed
- Fixed device class registration (#16)
- Numerous other small fixes and version bumps

## [1.0.1] - 2025-10-14

### Fixed
- Fixed issue where multiple HTTP endpoints from the same domain could not be configured (#13)
  - Updated unique_id generation to include query parameters, allowing configurations like different METAR station IDs from the same API
- Fixed sensors becoming unavailable after editing configuration (#12)
  - Improved platform unloading logic to only unload platforms that were actually set up for the entry
  - Prevents "Config entry was never loaded!" errors during configuration changes

## [1.0.0] - 2025-10-08

### Added
- Initial release of HTTP Agent integration
- Multi-step configuration wizard (URL → Headers → Payload → Sensors)
- Support for multiple extraction methods (JSON, XML, CSS)

### Features
- HTTP methods: GET, POST, PUT, DELETE, PATCH
- Content types: JSON, XML, form-data, plain text
- Template rendering for URLs, headers, and payloads
- Dynamic sensor configuration
- Error handling and logging
- Configurable timeout and update intervals
- Authentication support via headers
