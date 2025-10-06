# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] (2025-10-03)

### Initial Release
A Home Assistant integration for HTTP operations with template support and automatic sensor polling.

### Added
- **HTTP Services**: Complete HTTP request service with support for all major methods (GET, POST, PUT, DELETE, PATCH, HEAD)
- **Template Engine**: Full Home Assistant template support for URLs, payloads, query parameters, and headers
- **HTTP Sensors**: Automatic polling sensors with configurable intervals and response extraction
- **GUI Configuration**: Complete web-based configuration flow for easy setup and management
- **Sensor Management**: Add, edit, and delete HTTP sensors through the GUI
- **SSL Options**: Configurable SSL verification settings for secure connections
- **Multi-language Support**: Translations for 8 languages (English, Swedish, Danish, Finnish, Norwegian, German, Spanish, French)
- **Error Handling**: Comprehensive error handling with proper logging and user feedback
- **Status Indicators**: Dynamic icons based on HTTP response status codes
- **Session Management**: Efficient HTTP session handling with proper cleanup
- **Response Validation**: Built-in response validation and error reporting
- **Development Tools**: Complete development environment with linting, formatting, and testing

### Technical Details
- **Integration Type**: Hub with local polling
- **Minimum HA Version**: 2024.10+
- **Python Dependencies**: aiohttp>=3.8.0
- **Code Quality**: Black formatting, isort import sorting, flake8 linting, mypy type checking
- **Testing**: Comprehensive GitHub Actions workflows for CI/CD
- **Validation**: HACS and Hassfest validation for Home Assistant compliance

This marks the first stable release of HTTP Agent, providing a robust foundation for HTTP operations in Home Assistant with enterprise-grade features and Home Assistant best practices.

[keep-a-changelog]: http://keepachangelog.com/en/1.0.0/
[1.0.0]: https://github.com/dsorlov/http_agent