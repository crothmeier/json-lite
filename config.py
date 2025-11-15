"""
Centralized configuration management for json-lite project.

This module provides a single source of truth for all configuration values,
reading from environment variables with sensible defaults.
"""
import os
from pathlib import Path
from typing import Optional


class Config:
    """Application configuration loaded from environment variables."""

    # Base directories
    BASE_DIR = Path(__file__).parent
    DATA_DIR = Path(os.getenv('DATA_DIR', os.path.expanduser('~/data')))

    # Database configuration
    DATABASE_PATH = Path(os.getenv(
        'DATABASE_PATH',
        DATA_DIR / 'unified_conversations.db'
    ))

    # Export directories
    CHATGPT_EXPORT_DIR = Path(os.getenv(
        'CHATGPT_EXPORT_DIR',
        DATA_DIR / 'chatgpt-exports'
    ))
    CLAUDE_EXPORT_DIR = Path(os.getenv(
        'CLAUDE_EXPORT_DIR',
        DATA_DIR / 'claude-exports'
    ))

    # Flask configuration
    FLASK_DEBUG = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    FLASK_HOST = os.getenv('FLASK_HOST', '127.0.0.1')  # Changed from 0.0.0.0
    FLASK_PORT = int(os.getenv('FLASK_PORT', '5000'))

    # CORS configuration
    CORS_ORIGINS = os.getenv('CORS_ORIGINS', 'http://localhost:3000,http://localhost:5000')

    @classmethod
    def get_cors_origins(cls) -> list:
        """Parse CORS origins from comma-separated string."""
        origins = cls.CORS_ORIGINS
        if origins == '*':
            # Log warning but allow for development
            import logging
            logging.warning("CORS configured to allow all origins (*). This should not be used in production!")
            return ['*']
        return [origin.strip() for origin in origins.split(',') if origin.strip()]

    # API Authentication
    API_KEY = os.getenv('API_KEY', None)
    REQUIRE_AUTH = os.getenv('REQUIRE_AUTH', 'True').lower() == 'true'

    # File upload limits
    MAX_UPLOAD_SIZE = int(os.getenv('MAX_UPLOAD_SIZE', str(500 * 1024 * 1024)))  # 500MB default
    ALLOWED_FILE_EXTENSIONS = {'.json'}

    # Processing configuration
    CHUNK_SIZE = int(os.getenv('CHUNK_SIZE', str(8 * 1024 * 1024)))  # 8MB default

    # Monitoring configuration
    ENABLE_METRICS = os.getenv('ENABLE_METRICS', 'True').lower() == 'true'
    METRICS_PORT = int(os.getenv('METRICS_PORT', '9090'))

    @classmethod
    def ensure_directories(cls):
        """Create necessary directories if they don't exist."""
        cls.DATA_DIR.mkdir(parents=True, exist_ok=True)
        cls.CHATGPT_EXPORT_DIR.mkdir(parents=True, exist_ok=True)
        cls.CLAUDE_EXPORT_DIR.mkdir(parents=True, exist_ok=True)

    @classmethod
    def validate(cls) -> list:
        """Validate configuration and return list of warnings/errors."""
        issues = []

        if cls.FLASK_DEBUG and cls.FLASK_HOST == '0.0.0.0':
            issues.append("WARNING: Flask debug mode enabled with 0.0.0.0 host - security risk!")

        if not cls.REQUIRE_AUTH and cls.FLASK_HOST != '127.0.0.1':
            issues.append("WARNING: API authentication disabled on non-localhost - security risk!")

        if cls.REQUIRE_AUTH and not cls.API_KEY:
            issues.append("ERROR: REQUIRE_AUTH=True but no API_KEY set!")

        if cls.CORS_ORIGINS == '*':
            issues.append("WARNING: CORS allows all origins - should restrict in production!")

        return issues


# Convenience instance for importing
config = Config()


if __name__ == '__main__':
    # Print current configuration when run directly
    print("Current Configuration:")
    print(f"  DATA_DIR: {Config.DATA_DIR}")
    print(f"  DATABASE_PATH: {Config.DATABASE_PATH}")
    print(f"  CHATGPT_EXPORT_DIR: {Config.CHATGPT_EXPORT_DIR}")
    print(f"  CLAUDE_EXPORT_DIR: {Config.CLAUDE_EXPORT_DIR}")
    print(f"  FLASK_DEBUG: {Config.FLASK_DEBUG}")
    print(f"  FLASK_HOST: {Config.FLASK_HOST}")
    print(f"  FLASK_PORT: {Config.FLASK_PORT}")
    print(f"  CORS_ORIGINS: {Config.get_cors_origins()}")
    print(f"  REQUIRE_AUTH: {Config.REQUIRE_AUTH}")
    print(f"  API_KEY: {'<set>' if Config.API_KEY else '<not set>'}")
    print(f"  MAX_UPLOAD_SIZE: {Config.MAX_UPLOAD_SIZE / (1024*1024):.0f}MB")
    print()

    issues = Config.validate()
    if issues:
        print("Configuration Issues:")
        for issue in issues:
            print(f"  - {issue}")
    else:
        print("✓ Configuration valid")
