#!/usr/bin/env python3
"""Shared pytest fixtures for json-lite test suite."""

import pytest
import json
import tempfile
import pathlib
import os
import sys
from typing import Generator, Dict, Any, List
from unittest.mock import MagicMock, patch

# Add parent directory to path for imports
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

# Import test data generator
from tests.fixtures.generate_test_data import (
    generate_flat_json,
    generate_nested_json,
    generate_corrupted_json,
    generate_mixed_json,
    generate_wide_json,
    generate_unicode_json,
    generate_streaming_json
)


# ============================================================================
# File Fixtures
# ============================================================================

@pytest.fixture
def temp_json_file() -> Generator[pathlib.Path, None, None]:
    """Create a temporary JSON file that is automatically cleaned up."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        data = [{"id": i, "value": f"test_{i}"} for i in range(10)]
        json.dump(data, f)
        temp_path = pathlib.Path(f.name)
    
    yield temp_path
    
    # Cleanup
    if temp_path.exists():
        temp_path.unlink()


@pytest.fixture
def small_json_file(tmp_path) -> pathlib.Path:
    """Create a small JSON file (< 1MB)."""
    json_file = tmp_path / "small.json"
    generate_flat_json(1, 100, str(json_file))
    return json_file


@pytest.fixture
def medium_json_file(tmp_path) -> pathlib.Path:
    """Create a medium JSON file (5MB)."""
    json_file = tmp_path / "medium.json"
    generate_flat_json(5, 5000, str(json_file))
    return json_file


@pytest.fixture
def large_json_file(tmp_path) -> pathlib.Path:
    """Create a large JSON file (50MB)."""
    json_file = tmp_path / "large.json"
    generate_flat_json(50, 50000, str(json_file))
    return json_file


@pytest.fixture
def nested_json_file(tmp_path) -> pathlib.Path:
    """Create a deeply nested JSON file."""
    json_file = tmp_path / "nested.json"
    generate_nested_json(10, 3, str(json_file))
    return json_file


@pytest.fixture
def corrupted_json_file(tmp_path) -> pathlib.Path:
    """Create a corrupted JSON file."""
    json_file = tmp_path / "corrupted.json"
    generate_corrupted_json(50, 2000, str(json_file))
    return json_file


@pytest.fixture
def unicode_json_file(tmp_path) -> pathlib.Path:
    """Create a JSON file with Unicode characters."""
    json_file = tmp_path / "unicode.json"
    generate_unicode_json(100, str(json_file))
    return json_file


# ============================================================================
# Mock Fixtures
# ============================================================================

@pytest.fixture
def mock_gpu_available():
    """Mock GPU being available with normal memory usage."""
    with patch('shared.gpu_guard.pynvml') as mock_pynvml:
        # Setup mock behaviors
        mock_pynvml.nvmlInit.return_value = None
        mock_pynvml.nvmlShutdown.return_value = None
        mock_pynvml.nvmlDeviceGetCount.return_value = 1
        mock_pynvml.NVMLError = Exception
        
        # Mock memory info (50% usage)
        mem_info = MagicMock()
        mem_info.total = 8 * 1024 * 1024 * 1024  # 8GB
        mem_info.used = 4 * 1024 * 1024 * 1024   # 4GB
        
        handle = MagicMock()
        mock_pynvml.nvmlDeviceGetHandleByIndex.return_value = handle
        mock_pynvml.nvmlDeviceGetMemoryInfo.return_value = mem_info
        
        yield mock_pynvml


@pytest.fixture
def mock_gpu_high_memory():
    """Mock GPU with high memory usage (85%)."""
    with patch('shared.gpu_guard.pynvml') as mock_pynvml:
        # Setup mock behaviors
        mock_pynvml.nvmlInit.return_value = None
        mock_pynvml.nvmlShutdown.return_value = None
        mock_pynvml.nvmlDeviceGetCount.return_value = 1
        mock_pynvml.NVMLError = Exception
        
        # Mock memory info (85% usage)
        mem_info = MagicMock()
        mem_info.total = 8 * 1024 * 1024 * 1024  # 8GB
        mem_info.used = int(6.8 * 1024 * 1024 * 1024)  # 6.8GB
        
        handle = MagicMock()
        mock_pynvml.nvmlDeviceGetHandleByIndex.return_value = handle
        mock_pynvml.nvmlDeviceGetMemoryInfo.return_value = mem_info
        
        yield mock_pynvml


@pytest.fixture
def mock_gpu_not_available():
    """Mock GPU not being available."""
    with patch('shared.gpu_guard.pynvml.nvmlInit', side_effect=Exception("No GPU")):
        yield


# ============================================================================
# FastAPI Test Client
# ============================================================================

@pytest.fixture
def fastapi_client():
    """Create a FastAPI test client for OP2."""
    from fastapi.testclient import TestClient
    from op2_lite.app.simple_main import app
    
    return TestClient(app)


# ============================================================================
# Parser Fixtures
# ============================================================================

@pytest.fixture
def streaming_parser():
    """Create a StreamingJSONParser instance."""
    from shared.streaming_parser import StreamingJSONParser
    return StreamingJSONParser()


@pytest.fixture
def gpu_guard(mock_gpu_available):
    """Create a GPUMemoryGuard instance with mocked GPU."""
    from shared.gpu_guard import GPUMemoryGuard
    return GPUMemoryGuard(threshold_percent=80)


# ============================================================================
# Benchmark Fixtures
# ============================================================================

@pytest.fixture
def benchmark_data() -> Dict[str, Any]:
    """Generate data for benchmark tests."""
    return {
        "small": [{"id": i, "data": "x" * 100} for i in range(100)],
        "medium": [{"id": i, "data": "x" * 1000} for i in range(1000)],
        "large": [{"id": i, "data": "x" * 1000} for i in range(10000)]
    }


@pytest.fixture(params=[100, 1000, 10000])
def record_counts(request):
    """Parametrized fixture for different record counts."""
    return request.param


@pytest.fixture(params=[1, 5, 10, 20])
def nesting_depths(request):
    """Parametrized fixture for different nesting depths."""
    return request.param


# ============================================================================
# Test Data Fixtures
# ============================================================================

@pytest.fixture
def sample_json_records() -> List[Dict[str, Any]]:
    """Generate sample JSON records for testing."""
    return [
        {"id": i, "name": f"Record {i}", "value": i * 10}
        for i in range(100)
    ]


@pytest.fixture
def complex_json_structure() -> Dict[str, Any]:
    """Generate a complex JSON structure for testing."""
    return {
        "metadata": {
            "version": "1.0",
            "timestamp": "2024-01-01T00:00:00Z"
        },
        "data": {
            "users": [
                {
                    "id": i,
                    "profile": {
                        "name": f"User {i}",
                        "settings": {
                            "notifications": True,
                            "theme": "dark"
                        }
                    },
                    "activity": [
                        {"action": f"action_{j}", "timestamp": j}
                        for j in range(5)
                    ]
                }
                for i in range(10)
            ]
        }
    }


# ============================================================================
# Environment Fixtures
# ============================================================================

@pytest.fixture
def clean_environment(monkeypatch):
    """Ensure a clean environment for tests."""
    # Remove any existing environment variables that might affect tests
    env_vars_to_remove = ['GPU_MEMORY_THRESHOLD', 'JSON_CHUNK_SIZE', 'DEBUG']
    for var in env_vars_to_remove:
        monkeypatch.delenv(var, raising=False)
    
    yield
    
    # Environment is automatically restored by monkeypatch


@pytest.fixture
def mock_logger():
    """Create a mock logger for testing."""
    with patch('logging.getLogger') as mock_get_logger:
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        yield mock_logger


# ============================================================================
# Async Fixtures
# ============================================================================

@pytest.fixture
async def async_temp_file():
    """Create an async temporary file."""
    import aiofiles
    import asyncio
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        temp_path = pathlib.Path(f.name)
    
    # Write some test data asynchronously
    async with aiofiles.open(temp_path, 'w') as f:
        await f.write(json.dumps([{"test": "data"}]))
    
    yield temp_path
    
    # Cleanup
    if temp_path.exists():
        temp_path.unlink()


# ============================================================================
# Performance Testing Fixtures
# ============================================================================

@pytest.fixture
def memory_profiler():
    """Setup memory profiling for tests."""
    try:
        from memory_profiler import memory_usage
        
        def profile_memory(func, *args, **kwargs):
            """Profile memory usage of a function."""
            mem_usage = memory_usage((func, args, kwargs))
            return {
                "min": min(mem_usage),
                "max": max(mem_usage),
                "avg": sum(mem_usage) / len(mem_usage)
            }
        
        return profile_memory
    except ImportError:
        pytest.skip("memory_profiler not installed")


@pytest.fixture
def time_profiler():
    """Setup time profiling for tests."""
    import time
    
    def profile_time(func, *args, **kwargs):
        """Profile execution time of a function."""
        start = time.perf_counter()
        result = func(*args, **kwargs)
        end = time.perf_counter()
        return {
            "result": result,
            "duration": end - start
        }
    
    return profile_time


# ============================================================================
# Cleanup Fixtures
# ============================================================================

@pytest.fixture(autouse=True)
def cleanup_temp_files():
    """Automatically cleanup any leftover temp files after tests."""
    yield
    
    # Cleanup any test files in /tmp
    import glob
    temp_patterns = [
        '/tmp/test_*.json',
        '/tmp/tmp*.json',
        '/tmp/json_test_*'
    ]
    
    for pattern in temp_patterns:
        for file_path in glob.glob(pattern):
            try:
                os.unlink(file_path)
            except:
                pass  # Ignore errors during cleanup


# ============================================================================
# Test Markers
# ============================================================================

def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line("markers", "slow: marks tests as slow")
    config.addinivalue_line("markers", "gpu: marks tests that require GPU")
    config.addinivalue_line("markers", "integration: marks integration tests")
    config.addinivalue_line("markers", "benchmark: marks benchmark tests")
    config.addinivalue_line("markers", "docker: marks tests requiring Docker")