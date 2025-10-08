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

#### Code Guidelines

- **Code Style**: Follow PEP 8 guidelines
- **Formatting**: Use `black` for code formatting:
  ```bash
  black custom_components/
  ```
- **Import Sorting**: Use `isort` for import organization:
  ```bash
  isort custom_components/
  ```
- **Linting**: Run `flake8` to check for issues:
  ```bash
  flake8 custom_components/ --count --select=E9,F63,F7,F82 --show-source --statistics
  ```

#### Testing

Before submitting a PR, ensure:

1. **Code Quality Checks Pass**:
   ```bash
   black --check custom_components/
   isort --check-only custom_components/
   flake8 custom_components/ --count --select=E9,F63,F7,F82 --show-source --statistics
   ```

2. **Python Syntax Validation**:
   ```bash
   python -m py_compile custom_components/http_agent/*.py
   ```

3. **API Tests Pass**:
   ```bash
   python3 test_api.py
   ```

4. **Integration Works**: Test in Home Assistant using the Docker environment

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
3. Ensure all files maintain the same key structure (203 keys)
4. Validate JSON syntax:
   ```bash
   python3 -m json.tool custom_components/http_agent/translations/LANGUAGE.json
   ```

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
