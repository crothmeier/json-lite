#!/usr/bin/env python3
"""Setup script for json-lite package."""

from setuptools import setup, find_packages

setup(
    name="json-lite",
    version="1.1.0-alpha",
    packages=find_packages(),
    python_requires=">=3.8",
    install_requires=[
        "ijson>=3.2",
    ],
    extras_require={
        "test": [
            "pytest>=7.0",
            "pytest-cov>=4.0",
            "psutil>=5.9",
        ],
        "dev": [
            "pytest>=7.0",
            "pytest-cov>=4.0",
            "psutil>=5.9",
            "black>=22.0",
            "isort>=5.0",
            "flake8>=5.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "jsonlite-extract=json_lite.cli:main",
        ],
    },
)