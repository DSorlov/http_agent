# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
