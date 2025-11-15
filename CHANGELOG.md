# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Centralized configuration system (`config.py`) for managing all environment variables
- API key authentication for web API endpoints (`web/auth.py`)
- Comprehensive input validation for file upload endpoints
- File type, size, and content validation for uploaded JSON files
- GitHub Actions workflow for automated testing and security scanning
- Security scanning with bandit, safety, and pip-audit in CI/CD
- Type checking with mypy in CI/CD pipeline
- Code quality checks with ruff, flake8, and pylint
- Test coverage reporting to Codecov
- Integration and contract test suites in CI/CD
- Docker build validation in CI/CD
- CONTRIBUTING.md with detailed contribution guidelines
- CHANGELOG.md to track project changes
- `requirements-gpu.txt` for optional GPU support dependencies
- `shared/__init__.py` to make shared utilities a proper Python package
- Proper cleanup of temporary files in OP2 file processing
- Configuration validation on startup
- CORS configuration via environment variables

### Changed
- **BREAKING**: Flask debug mode now defaults to `False` (configure via `FLASK_DEBUG` env var)
- **BREAKING**: Flask host now defaults to `127.0.0.1` instead of `0.0.0.0` for security
- **BREAKING**: API endpoints now require authentication by default (configure via `REQUIRE_AUTH` and `API_KEY`)
- Updated all hardcoded paths to use centralized configuration
- Improved error handling and logging throughout codebase
- Enhanced temp file cleanup with try/finally blocks
- Updated `.env.example` with new configuration options
- Systemd service file now uses placeholders instead of hardcoded paths
- Backup script now uses environment variables for configuration
- Test import pipeline now accepts command line arguments
- CORS origins can be configured via `CORS_ORIGINS` environment variable
- Consistent dependency version pinning across all requirements files
- Better file size limit enforcement during upload (streaming validation)

### Fixed
- Removed junk files (`=` and `self.peak_memory:`) from repository root
- Fixed missing dependencies (`psutil`) in root requirements.txt
- Fixed potential race conditions in temporary file handling
- Fixed security vulnerability: Flask debug mode exposed in production code
- Fixed security vulnerability: Hardcoded database paths revealing internal structure
- Fixed security vulnerability: Unvalidated file uploads
- Fixed security vulnerability: Permissive CORS policy
- Proper temporary file cleanup even when exceptions occur
- Import path hacks replaced with proper package structure

### Security
- Added API key authentication to protect API endpoints
- Added input validation for file uploads (type, size, content)
- Disabled Flask debug mode by default
- Changed default Flask host to localhost only
- Added configurable CORS policy (no longer allows all origins by default)
- Added security scanning to CI/CD pipeline
- Fixed information disclosure in error messages
- Improved file upload security with validation and limits

### Removed
- Hardcoded username references in configuration files
- Hardcoded paths throughout the codebase

## [1.1.0-alpha] - 2024-11-15

### Added
- Unified import pipeline for ChatGPT and Claude exports
- Web UI for conversation search with Flask
- Full-text search using SQLite FTS5
- Automated import monitoring with systemd
- Docker support with multi-stage builds
- Comprehensive test suite with pytest
- Performance benchmarking tests
- GPU memory monitoring and guards
- Streaming JSON parser for memory efficiency
- Manual processor for large files (OP1)
- FastAPI service for file processing (OP2)
- Prometheus metrics support
- Pipeline documentation

### Changed
- Improved memory efficiency with streaming approach
- Enhanced error handling and logging

### Fixed
- Memory leaks in large file processing
- JSON parsing edge cases

## [1.0.0] - Initial Release

### Added
- ChatGPT conversation extractor
- Basic JSON processing utilities
- Initial documentation

---

## Version History Summary

- **1.1.0-alpha** - Added web UI, unified pipeline, Docker support
- **1.0.0** - Initial release with basic ChatGPT extraction

## Migration Guides

### Upgrading to Unreleased Version

**Configuration Changes:**

1. Create `.env` file from `.env.example`:
   ```bash
   cp .env.example .env
   ```

2. Configure required settings:
   ```bash
   # Required if using authentication
   API_KEY=your-secret-key-here

   # Data directories
   DATA_DIR=/path/to/your/data
   DATABASE_PATH=/path/to/unified_conversations.db
   CHATGPT_EXPORT_DIR=/path/to/chatgpt-exports
   CLAUDE_EXPORT_DIR=/path/to/claude-exports
   ```

3. Security settings:
   ```bash
   # Production settings
   FLASK_DEBUG=false
   FLASK_HOST=127.0.0.1
   REQUIRE_AUTH=true
   CORS_ORIGINS=http://localhost:3000
   ```

**Breaking Changes:**

- **Authentication**: API endpoints now require authentication by default. To disable for development:
  ```bash
  REQUIRE_AUTH=false
  ```

- **Flask Host**: Now binds to localhost by default. To allow external connections:
  ```bash
  FLASK_HOST=0.0.0.0  # Use with caution!
  ```

- **Hardcoded Paths**: Update any scripts or tools that relied on hardcoded paths like `/home/crathmene/`. Use environment variables instead.

**Systemd Service Updates:**

If using the systemd service:

1. Edit `web/deployment/conversation-search.service`
2. Replace all placeholders (USER, GROUP, /path/to/...)
3. Add `EnvironmentFile=/path/to/json-lite/.env`
4. Reload: `sudo systemctl daemon-reload`
5. Restart: `sudo systemctl restart conversation-search`

**Docker Updates:**

No breaking changes. Environment variables can be passed via:
- `.env` file
- `docker-compose.yml` environment section
- Command line: `docker run -e API_KEY=xxx ...`

---

## Support

For questions about changes or upgrading:
- Check documentation in `/docs`
- Review CONTRIBUTING.md
- Open an issue on GitHub
