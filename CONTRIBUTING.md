# Contributing to JSON-Lite

Thank you for considering contributing to JSON-Lite! This document provides guidelines and instructions for contributing to the project.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Making Changes](#making-changes)
- [Testing](#testing)
- [Code Style](#code-style)
- [Commit Messages](#commit-messages)
- [Pull Request Process](#pull-request-process)
- [Reporting Bugs](#reporting-bugs)
- [Suggesting Features](#suggesting-features)

## Code of Conduct

This project adheres to a code of conduct that promotes a welcoming and inclusive environment:

- Be respectful and considerate
- Welcome diverse perspectives and experiences
- Accept constructive criticism gracefully
- Focus on what's best for the community
- Show empathy towards others

## Getting Started

1. Fork the repository on GitHub
2. Clone your fork locally:
   ```bash
   git clone https://github.com/YOUR_USERNAME/json-lite.git
   cd json-lite
   ```

3. Add the upstream repository:
   ```bash
   git remote add upstream https://github.com/crothmeier/json-lite.git
   ```

## Development Setup

### Prerequisites

- Python 3.9 or higher
- Git
- (Optional) Docker for containerized testing
- (Optional) NVIDIA GPU with drivers for GPU features

### Installation

1. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. Install dependencies:
   ```bash
   # Core dependencies
   pip install -r requirements.txt

   # Development and testing dependencies
   pip install -r requirements-test.txt

   # Web application dependencies
   pip install -r web/requirements.txt

   # Optional: GPU support
   pip install -r requirements-gpu.txt
   ```

3. Configure environment:
   ```bash
   cp .env.example .env
   # Edit .env with your settings
   ```

4. Verify installation:
   ```bash
   python -m pytest tests/
   ```

## Making Changes

### Branch Naming

Use descriptive branch names:
- `feature/your-feature-name` - New features
- `bugfix/issue-description` - Bug fixes
- `docs/what-you-document` - Documentation updates
- `refactor/what-you-refactor` - Code refactoring
- `test/what-you-test` - Test additions/modifications

### Workflow

1. Create a new branch:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. Make your changes
3. Add tests for your changes
4. Ensure all tests pass
5. Commit your changes
6. Push to your fork
7. Open a Pull Request

## Testing

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=. --cov-report=html

# Run specific test file
pytest tests/test_streaming_parser.py

# Run specific test
pytest tests/test_streaming_parser.py::test_parse_array

# Run tests by marker
pytest -m integration  # Integration tests only
pytest -m "not slow"   # Skip slow tests
```

### Test Markers

- `@pytest.mark.slow` - Long-running tests
- `@pytest.mark.gpu` - Requires GPU
- `@pytest.mark.integration` - Integration tests
- `@pytest.mark.benchmark` - Performance benchmarks

### Writing Tests

- Place tests in the `tests/` directory
- Name test files `test_*.py`
- Name test functions `test_*`
- Use fixtures from `tests/conftest.py`
- Aim for 80%+ code coverage
- Include both positive and negative test cases

Example:
```python
def test_streaming_parser_valid_json(temp_json_file):
    """Test that StreamingJSONParser handles valid JSON correctly."""
    parser = StreamingJSONParser()
    records = list(parser.iter_records(temp_json_file))
    assert len(records) > 0
```

## Code Style

This project follows PEP 8 with some modifications defined in `pyproject.toml`.

### Formatting Tools

```bash
# Format code with black
black .

# Sort imports with isort
isort .

# Run linters
ruff check .
flake8 .
pylint **/*.py

# Type checking
mypy .
```

### Style Guidelines

- Maximum line length: 100 characters (Black default)
- Use type hints where possible
- Write docstrings for public functions/classes
- Use meaningful variable names
- Keep functions focused and small
- Avoid deep nesting (max 3-4 levels)

### Docstring Format

Use Google-style docstrings:

```python
def process_json(path: str, limit: Optional[int] = None) -> int:
    """
    Process a JSON file and return the number of records.

    Args:
        path: Path to the JSON file
        limit: Optional limit on number of records to process

    Returns:
        Number of records processed

    Raises:
        FileNotFoundError: If the file doesn't exist
        ValueError: If the JSON is invalid
    """
    pass
```

## Commit Messages

### Format

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Types

- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, no logic change)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks
- `perf`: Performance improvements
- `ci`: CI/CD changes

### Examples

```
feat(api): add authentication to API endpoints

Implemented API key authentication for /api/search endpoint
to prevent unauthorized access.

Closes #123
```

```
fix(parser): handle empty JSON arrays correctly

Previously crashed on empty arrays, now returns empty iterator.

Fixes #456
```

## Pull Request Process

### Before Submitting

1. **Update tests**: Add/update tests for your changes
2. **Run test suite**: Ensure all tests pass
3. **Check code style**: Run linters and formatters
4. **Update documentation**: Update README, docstrings, etc.
5. **Update CHANGELOG.md**: Add your changes under "Unreleased"
6. **Rebase on main**: Ensure your branch is up to date

### PR Checklist

- [ ] Tests pass locally
- [ ] Code follows style guidelines
- [ ] Documentation updated
- [ ] CHANGELOG.md updated
- [ ] No merge conflicts
- [ ] Commit messages follow guidelines
- [ ] Branch is up to date with main

### PR Description Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
How has this been tested?

## Checklist
- [ ] Tests added/updated
- [ ] Documentation updated
- [ ] CHANGELOG.md updated
```

### Review Process

1. Maintainers will review your PR
2. Address any requested changes
3. Once approved, a maintainer will merge your PR
4. Your contribution will be included in the next release!

## Reporting Bugs

### Before Reporting

1. Check existing issues to avoid duplicates
2. Verify the bug on the latest version
3. Collect necessary information

### Bug Report Template

```markdown
**Describe the bug**
Clear description of the bug

**To Reproduce**
Steps to reproduce:
1.
2.
3.

**Expected behavior**
What you expected to happen

**Actual behavior**
What actually happened

**Environment**
- OS: [e.g., Ubuntu 22.04]
- Python version: [e.g., 3.11.5]
- JSON-Lite version: [e.g., 1.1.0]

**Additional context**
Any other relevant information
```

## Suggesting Features

### Before Suggesting

1. Check existing feature requests
2. Ensure it aligns with project goals
3. Consider implementation complexity

### Feature Request Template

```markdown
**Is your feature request related to a problem?**
Description of the problem

**Describe the solution you'd like**
Clear description of desired functionality

**Describe alternatives you've considered**
Other approaches you've thought about

**Additional context**
Any other relevant information
```

## Development Tips

### Running Components Locally

```bash
# Web UI
cd web
python app.py

# OP1 Large processor
cd op1_large
python -m op1_large.manual_processor <input_file>

# OP2 Lite API
cd op2_lite/app
uvicorn simple_main:app --reload
```

### Docker Development

```bash
# Build and run with docker-compose
docker-compose up --build

# Run tests in Docker
docker-compose -f docker-compose.test.yml up
```

### Debugging

- Use `pytest -v -s` to see print statements
- Use `pytest --pdb` to drop into debugger on failure
- Set `PYTHONBREAKPOINT=ipdb.set_trace` for better debugging
- Enable verbose logging in code: `logging.basicConfig(level=logging.DEBUG)`

## Questions?

If you have questions about contributing:

1. Check the documentation in `/docs`
2. Search existing issues
3. Open a discussion on GitHub
4. Contact the maintainers

## Recognition

Contributors are recognized in:
- CHANGELOG.md for each release
- GitHub contributors page
- Special thanks in release notes

Thank you for contributing to JSON-Lite! 🎉
