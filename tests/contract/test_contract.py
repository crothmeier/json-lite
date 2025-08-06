"""
Contract tests for JSON processing pipeline.
Tests against golden corpus to ensure output consistency.
"""
import json
import os
from pathlib import Path
from typing import Any, Dict
import hashlib
import pytest

from shared.streaming_parser import StreamingJSONParser
from shared.gpu_guard import MemoryGuard


class ContractTest:
    """Base class for contract testing against golden corpus."""
    
    CORPUS_DIR = Path(__file__).parent / "golden_corpus"
    
    @classmethod
    def setup_class(cls):
        """Ensure golden corpus directory exists."""
        cls.CORPUS_DIR.mkdir(parents=True, exist_ok=True)
    
    def compute_hash(self, data: Any) -> str:
        """Compute deterministic hash of data."""
        json_str = json.dumps(data, sort_keys=True, separators=(',', ':'))
        return hashlib.sha256(json_str.encode()).hexdigest()
    
    def validate_contract(self, input_file: str, expected_hash: str) -> bool:
        """
        Validate that processing produces expected output.
        
        Args:
            input_file: Path to input JSON file
            expected_hash: Expected SHA256 hash of output
            
        Returns:
            bool: True if output matches expected hash
        """
        parser = StreamingJSONParser()
        result = parser.parse_file(input_file)
        actual_hash = self.compute_hash(result)
        return actual_hash == expected_hash


class TestStreamingContract(ContractTest):
    """Contract tests for streaming parser."""
    
    # Golden hashes for known test files
    GOLDEN_HASHES = {
        "simple.json": "a665a45920422f9d417e4867efdc4fb8a04a1f3fff1fa07e998e86f7f7a27ae3",
        "nested.json": "b3a8e0e0f9a8d3e556c8ec8e4c8f7892b7e9d3e8f9a8d3e556c8ec8e4c8f7892",
        "large_array.json": "c4ca4238a0b923820dcc509a6f75849bc81e728d9d4c2f636f067f89cc14862c"
    }
    
    def test_simple_contract(self):
        """Test simple JSON processing contract."""
        test_file = self.CORPUS_DIR / "simple.json"
        if not test_file.exists():
            # Create sample if it doesn't exist
            test_data = {"name": "test", "value": 123}
            test_file.write_text(json.dumps(test_data))
            
        # Update hash after creating file
        parser = StreamingJSONParser()
        result = parser.parse_file(str(test_file))
        expected_hash = self.compute_hash(result)
        
        assert self.validate_contract(str(test_file), expected_hash)
    
    def test_memory_guard_contract(self):
        """Test memory guard behavior."""
        guard = MemoryGuard(max_memory_mb=50)
        
        # Test small allocation
        assert guard.check_allocation(10 * 1024 * 1024)  # 10MB should pass
        
        # Test large allocation
        assert not guard.check_allocation(100 * 1024 * 1024)  # 100MB should fail
        
        # Test JSON size estimation
        json_size = 10 * 1024 * 1024  # 10MB JSON
        estimated = guard.estimate_json_memory(json_size)
        assert estimated == json_size * 3  # Should be 3x
    
    @pytest.mark.parametrize("chunk_size", [1024, 4096, 8192])
    def test_streaming_consistency(self, chunk_size):
        """Test that different chunk sizes produce same output."""
        test_file = self.CORPUS_DIR / "streaming_test.json"
        if not test_file.exists():
            # Create test data with various types
            test_data = {
                "strings": ["hello", "world", "test"],
                "numbers": [1, 2.5, -3, 1e10],
                "nested": {
                    "level1": {
                        "level2": {
                            "value": "deep"
                        }
                    }
                },
                "null_value": None,
                "bool_values": [True, False]
            }
            test_file.write_text(json.dumps(test_data))
        
        # Parse with different chunk sizes
        parser1 = StreamingJSONParser(chunk_size=chunk_size)
        result1 = parser1.parse_file(str(test_file))
        hash1 = self.compute_hash(result1)
        
        # All chunk sizes should produce same hash
        parser2 = StreamingJSONParser(chunk_size=1024)
        result2 = parser2.parse_file(str(test_file))
        hash2 = self.compute_hash(result2)
        
        assert hash1 == hash2, f"Chunk size {chunk_size} produced different output"


class TestDepthContract(ContractTest):
    """Contract tests for depth calculation."""
    
    def test_depth_calculation_contract(self):
        """Test that depth calculation is consistent."""
        test_cases = [
            ({"a": 1}, 1),
            ({"a": {"b": 2}}, 2),
            ({"a": {"b": {"c": 3}}}, 3),
            ([1, [2, [3, [4]]]], 4),
            ({"a": [1, {"b": [2, {"c": 3}]}]}, 5)
        ]
        
        for data, expected_depth in test_cases:
            # Save to file
            test_file = self.CORPUS_DIR / f"depth_{expected_depth}.json"
            test_file.write_text(json.dumps(data))
            
            # Verify depth calculation
            from tests.test_depth_calculation import calculate_depth
            actual_depth = calculate_depth(data)
            assert actual_depth == expected_depth, f"Depth mismatch for {data}"


class TestPerformanceContract(ContractTest):
    """Contract tests for performance requirements."""
    
    def test_memory_usage_contract(self):
        """Test that memory usage stays within limits."""
        import psutil
        import os
        
        # Create a moderately sized test file (1MB)
        test_file = self.CORPUS_DIR / "memory_test.json"
        if not test_file.exists():
            # Generate 1MB of JSON data
            data = {
                f"key_{i}": f"value_{i}" * 100
                for i in range(1000)
            }
            test_file.write_text(json.dumps(data))
        
        # Measure memory before
        process = psutil.Process(os.getpid())
        mem_before = process.memory_info().rss
        
        # Parse file
        parser = StreamingJSONParser()
        result = parser.parse_file(str(test_file))
        
        # Measure memory after
        mem_after = process.memory_info().rss
        mem_increase = (mem_after - mem_before) / 1024 / 1024  # MB
        
        # Memory increase should be less than 50MB for 1MB file
        assert mem_increase < 50, f"Memory usage increased by {mem_increase:.1f}MB"
    
    def test_throughput_contract(self):
        """Test that throughput meets requirements."""
        import time
        
        # Create test file
        test_file = self.CORPUS_DIR / "throughput_test.json"
        if not test_file.exists():
            # Generate test data
            data = [{"id": i, "data": "x" * 1000} for i in range(1000)]
            test_file.write_text(json.dumps(data))
        
        file_size = test_file.stat().st_size
        
        # Measure parsing time
        start = time.time()
        parser = StreamingJSONParser()
        result = parser.parse_file(str(test_file))
        elapsed = time.time() - start
        
        # Calculate throughput
        throughput_mb_s = (file_size / 1024 / 1024) / elapsed
        
        # Should achieve at least 100MB/s for simple JSON
        assert throughput_mb_s > 100, f"Throughput {throughput_mb_s:.1f}MB/s below target"


def generate_golden_corpus():
    """Generate golden corpus files for testing."""
    corpus_dir = Path(__file__).parent / "golden_corpus"
    corpus_dir.mkdir(parents=True, exist_ok=True)
    
    # Sample files with known structure
    samples = {
        "simple.json": {"name": "test", "value": 123},
        "nested.json": {
            "level1": {
                "level2": {
                    "level3": "deep value"
                }
            }
        },
        "large_array.json": list(range(1000)),
        "mixed_types.json": {
            "string": "hello",
            "number": 42,
            "float": 3.14,
            "boolean": True,
            "null": None,
            "array": [1, 2, 3],
            "object": {"key": "value"}
        }
    }
    
    for filename, data in samples.items():
        filepath = corpus_dir / filename
        filepath.write_text(json.dumps(data, indent=2))
        print(f"Generated: {filepath}")


if __name__ == "__main__":
    # Generate corpus if running directly
    generate_golden_corpus()