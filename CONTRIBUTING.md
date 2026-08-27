# Contributing to HTTP Agent

Thank you for your interest in contributing to HTTP Agent! We welcome contributions from the community.

## How to Contribute

### Reporting Bugs

If you find a bug, please create an issue on GitHub with the following information:

- **Description**: A clear description of the bug
- **Steps to Reproduce**: Detailed steps to reproduce the issue
- **Expected Behavior**: What you expected to happen
- **Actual Behavior**: What actually happened
- **Environment**:
  - Home Assistant version
  - HTTP Agent version
  - Browser (if UI-related)
- **Logs**: Relevant error messages or logs from Home Assistant

### Suggesting Enhancements

We welcome feature requests! Please create an issue with:

- **Description**: A clear description of the enhancement
- **Use Case**: Why this feature would be useful
- **Proposed Solution**: If you have ideas on how to implement it

### Pull Requests

We actively welcome pull requests!

#### Before You Start

1. Check existing issues and PRs to avoid duplicates
2. For major changes, please open an issue first to discuss
3. Fork the repository and create a branch from `main`

#### Development environment

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
```

The project targets the Python version shipped with the current Home Assistant
release and supports Home Assistant 2025.12 and newer.

#### Code Guidelines

- **Code Style**: Follow the Home Assistant conventions; [Ruff](https://docs.astral.sh/ruff/)
  enforces them.
- **Linting**:
  ```bash
  .venv/bin/ruff check custom_components tests script
  ```
- **Formatting**:
  ```bash
  .venv/bin/ruff format custom_components tests script
  ```

#### Testing

Before submitting a PR, ensure all of these pass:

1. **Lint and format**:
   ```bash
   .venv/bin/ruff check custom_components tests script
   .venv/bin/ruff format --check custom_components tests script
   ```

2. **Tests** (coverage must not regress):
   ```bash
   .venv/bin/pytest
   ```

3. **Translations and brand assets**:
   ```bash
   .venv/bin/python script/validate_strings.py
   python3 script/validate_assets.py
   ```

4. **Integration works**: test in Home Assistant using the Docker environment

#### Translation Guidelines

If adding or modifying translations:

1. Always update `custom_components/http_agent/strings.json` first
2. Update all language files in `custom_components/http_agent/translations/`:
   - `en.json` (English)
   - `sv.json` (Swedish)
   - `da.json` (Danish)
   - `de.json` (German)
   - `fi.json` (Finnish)
   - `no.json` (Norwegian)
3. Every file must have exactly the same keys as `strings.json`
4. Translated values must not contain URLs, HTML-like tags, or placeholders
   wrapped in single quotes — Home Assistant rejects those
5. Validate:
   ```bash
   .venv/bin/python script/validate_strings.py
   python3 script/validate_assets.py
   ```

#### Brand assets

See [`brands/README.md`](brands/README.md). `script/validate_assets.py` checks
the required dimensions.

#### Commit Messages

- Use clear, descriptive commit messages
- Start with a verb in present tense (e.g., "Add", "Fix", "Update")
- Reference issue numbers when applicable

Example:
```
Add support for custom authentication headers (#123)

- Add new config flow step for auth configuration
- Update coordinator to handle auth headers
- Add tests for authentication
```

#### Pull Request Process

1. Update documentation if needed
2. Update CHANGELOG.md with your changes
3. Ensure all CI checks pass
4. Request review from maintainers
5. Address any feedback

### Documentation

- Update README.md if you change functionality
- Add code comments for complex logic
- Update configuration examples if needed

## Code of Conduct

### Our Pledge

We are committed to providing a welcoming and inclusive environment for everyone.

### Our Standards

Examples of behavior that contributes to a positive environment:

- Using welcoming and inclusive language
- Being respectful of differing viewpoints
- Gracefully accepting constructive criticism
- Focusing on what is best for the community
- Showing empathy towards others

Examples of unacceptable behavior:

- Harassment or discriminatory language
- Trolling or insulting comments
- Personal or political attacks
- Publishing others' private information
- Other conduct which could reasonably be considered inappropriate

### Enforcement

Instances of abusive, harassing, or otherwise unacceptable behavior may be reported by contacting the project maintainers. All complaints will be reviewed and investigated promptly and fairly.

## Questions?

If you have questions, feel free to:

- Open an issue for discussion
- Check existing documentation
- Review closed issues and PRs

## License

By contributing, you agree that your contributions will be licensed under the same license as the project (see LICENSE file).

---

Thank you for contributing to HTTP Agent! 🎉
