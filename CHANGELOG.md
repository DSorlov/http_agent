# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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