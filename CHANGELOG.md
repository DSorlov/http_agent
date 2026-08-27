# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [2.1.0] - 2026-08-27

### Added
- **`http_agent.request` action.** Automations and scripts can call any endpoint
  on demand and use the answer in a later step through `response_variable`.
  - Values are extracted with the same path syntax as the sensors and returned
    under `values`, so the data is normalised the same way.
  - `config_entry_id` reuses the URL, authentication, headers and connection
    settings of a configured endpoint; `url` may be a full URL or a `/path`
    resolved against that endpoint's host.
  - `payload` and `headers` make it straightforward to POST values taken from
    other entities.
  - What is sent is always decided by the call: the endpoint's own method and
    body are never inherited.
  - Response headers that carry credentials are redacted.
- `script/validate_strings.py` now also checks that `services.yaml` and
  `strings.json` describe the same actions and fields.

### Changed
- An empty response body is no longer treated as a failure for the new action,
  so a fire-and-forget `POST` answering `204` succeeds. Polling is unchanged.

## [2.0.0] - 2026-08-27

A full rewrite against current Home Assistant integration standards. Existing
configuration entries are migrated automatically.

### Added
- **Visual value picker.** After entering the URL, method and authentication the
  endpoint is called once. The response is flattened into a searchable list of
  `path = value` pairs, and the selected values become entities.
- **Automatic guessing** of entity type, device class, unit of measurement and
  state class from the key name and the value.
- **Authentication presets**: bearer token, API key (custom header) and HTTP
  basic authentication, in addition to free-form headers.
- **Config subentries** — every entity is its own subentry with dedicated
  *Add* and *Edit* dialogs on the integration page.
- **Reconfigure flow** for changing the endpoint without recreating the entry.
- **Re-authentication flow** triggered automatically on HTTP 401/403.
- **Diagnostics** with the URL, headers and credentials redacted.
- Support for reading XML and HTML attributes (`/@name`, `::attr(name)`).
- Configurable extra state attributes per entity.
- `HEAD` request method, redirect control and a forced response format.
- Local brand assets in `brands/`, plus `script/validate_assets.py` and
  `script/validate_strings.py` to keep assets and translations valid.
- Test suite covering the flows, migration, parsing and entity behaviour.

### Changed
- **Simplified configuration.** Headers are entered as `Name: value` lines
  instead of a repeating add-one-at-a-time wizard, and advanced options are
  collapsed into a section. Setup is now two to four steps.
- Requests use Home Assistant's shared aiohttp session.
- The coordinator stores the parsed response once; entities extract their own
  value from it.
- Entities follow the `has_entity_name` convention and each get their own device
  linked to the endpoint device. **Entity IDs change.**
- Complete rewrite of `strings.json`; all 24 languages retranslated.
- Tooling moved from Black/isort/flake8 to Ruff.

### Fixed
- **XML external entity (XXE) vulnerability**: XML is now parsed with
  `defusedxml` instead of the standard library parser.
- Credentials are no longer written to logs or diagnostics.
- Sensors with a numeric device class now coerce their value, and timestamp
  sensors return a real `datetime`.
- Unsupported or removed device classes are ignored instead of breaking setup.
- Unresolvable paths leave the entity `unknown` instead of logging a warning on
  every poll.

### Removed
- The `number` platform. Read-only number entities were misleading; existing
  ones are migrated to sensors.
- The `lxml` requirement. HTML is parsed with the standard library parser.
- The `sensor_color` option, migrated to an extra state attribute named `color`.
- The device tracker `location_name` option, deprecated upstream.

### Retained from 1.2.0
- Configurable retries on error, including retrying on an empty response body.
- Response parsing runs in the executor to keep the event loop free.
- Regular-expression extraction from plain-text bodies.
- All 24 UI translations.

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
