# Contributing to HTTP Agent

Thank you for your interest in contributing to HTTP Agent! We welcome contributions of all kinds.

## How to Contribute

### Reporting Bugs
- Use the GitHub issue tracker
- Follow the bug report template
- Include logs with debug logging enabled
- Provide clear reproduction steps

### Requesting Features
- Use the GitHub issue tracker
- Follow the feature request template
- Explain the use case clearly
- Consider backward compatibility

### Code Contributions

#### Development Setup
1. Fork the repository
2. Clone your fork
3. Install development dependencies:
   ```bash
   pip install -r requirements-dev.txt
   ```

#### Code Standards
- Follow PEP 8 style guidelines
- Use Black for code formatting: `black custom_components/http_agent`
- Sort imports with isort: `isort custom_components/http_agent`
- Run flake8 for linting: `flake8 custom_components/http_agent`

#### Testing
- Ensure all GitHub Actions pass
- Test with different Home Assistant versions if possible
- Add tests for new features when applicable

#### Pull Requests
1. Create a feature branch from `main`
2. Make your changes
3. Ensure all tests pass
4. Update documentation if needed
5. Submit a pull request with a clear description

#### Commit Messages
- Use clear, descriptive commit messages
- Start with a verb (Add, Fix, Update, etc.)
- Keep the first line under 50 characters
- Add details in the body if needed

## Development Guidelines

### Code Structure
- Follow Home Assistant integration patterns
- Use async/await for I/O operations
- Handle errors gracefully
- Add proper logging

### Documentation
- Update README.md for user-facing changes
- Update docstrings for code changes
- Add examples for new features

### Internationalization
- Add translation keys to all language files
- Use descriptive translation keys
- Test with different languages

## Getting Help

- Check existing issues and pull requests
- Ask questions in GitHub Discussions
- Join the Home Assistant community forums

## License

By contributing, you agree that your contributions will be licensed under the MIT License.