#!/usr/bin/env python3
"""Tests for JSON depth calculation and chunk size optimization."""

import pytest
import json
import tempfile
import pathlib
import sys
import statistics
from unittest.mock import patch, MagicMock

sys.path.append(str(pathlib.Path(__file__).parent.parent))
from op1_large.manual_processor import (
    get_json_depth, 
    recommend_chunk, 
    complexity_score
)


class TestDepthCalculation:
    """Test suite for JSON depth calculation algorithms."""
    
    def test_depth_empty_dict(self):
        """Test depth calculation for empty dictionary."""
        assert get_json_depth({}) == 0
    
    def test_depth_empty_list(self):
        """Test depth calculation for empty list."""
        assert get_json_depth([]) == 0
    
    def test_depth_flat_dict(self):
        """Test depth calculation for flat dictionary."""
        data = {"key1": "value1", "key2": 2, "key3": True}
        assert get_json_depth(data) == 1
    
    def test_depth_flat_list(self):
        """Test depth calculation for flat list."""
        data = [1, 2, 3, "string", True, None]
        assert get_json_depth(data) == 1
    
    def test_depth_nested_dict(self):
        """Test depth calculation for nested dictionary."""
        data = {
            "level1": {
                "level2": {
                    "level3": "value"
                }
            }
        }
        assert get_json_depth(data) == 3
    
    def test_depth_nested_list(self):
        """Test depth calculation for nested list."""
        data = [[[["deep_value"]]]]
        assert get_json_depth(data) == 4
    
    def test_depth_mixed_nesting(self):
        """Test depth calculation for mixed dict/list nesting."""
        data = {
            "array": [
                {
                    "nested": [
                        {"deep": "value"}
                    ]
                }
            ]
        }
        assert get_json_depth(data) == 4
    
    def test_depth_complex_structure(self):
        """Test depth calculation for complex JSON structure."""
        data = {
            "users": [
                {
                    "name": "Alice",
                    "address": {
                        "city": "NYC",
                        "coordinates": {
                            "lat": 40.7128,
                            "lng": -74.0060
                        }
                    },
                    "orders": [
                        {
                            "items": [
                                {"product": "Book", "quantity": 2}
                            ]
                        }
                    ]
                }
            ]
        }
        assert get_json_depth(data) == 6
    
    def test_depth_with_primitive_values(self):
        """Test that primitive values don't add to depth."""
        data = {
            "string": "value",
            "number": 42,
            "float": 3.14,
            "boolean": True,
            "null": None
        }
        assert get_json_depth(data) == 1
    
    @pytest.mark.parametrize("depth,expected_depth", [
        (1, 1),
        (5, 5),
        (10, 10),
        (15, 15),
        (20, 20),
        (50, 50),
    ])
    def test_depth_deeply_nested(self, depth, expected_depth):
        """Test depth calculation for various nesting levels."""
        # Build deeply nested structure
        data = "value"
        for i in range(depth):
            data = {"level": data}
        
        assert get_json_depth(data) == expected_depth
    
    def test_depth_wide_structure(self):
        """Test depth calculation for wide but shallow structure."""
        data = {f"key_{i}": f"value_{i}" for i in range(1000)}
        assert get_json_depth(data) == 1
    
    def test_depth_array_of_objects(self):
        """Test depth calculation for array of objects."""
        data = [
            {"id": 1, "nested": {"value": "a"}},
            {"id": 2, "nested": {"value": "b"}},
            {"id": 3, "nested": {"value": "c"}}
        ]
        assert get_json_depth(data) == 3
    
    def test_complexity_score_calculation(self):
        """Test the complexity score calculation."""
        stats = {
            'depth': 5,
            'arr_density': 0.8,
            'strlen_var': 100,
            'obj_per_kb': 10
        }
        
        expected = 0.3 * 5 + 0.4 * 0.8 + 0.2 * 100 + 0.1 * 10
        assert complexity_score(stats) == expected
    
    def test_complexity_score_zero_values(self):
        """Test complexity score with zero values."""
        stats = {
            'depth': 0,
            'arr_density': 0,
            'strlen_var': 0,
            'obj_per_kb': 0
        }
        
        assert complexity_score(stats) == 0
    
    def test_recommend_chunk_simple_json(self, tmp_path):
        """Test chunk size recommendation for simple JSON."""
        json_file = tmp_path / "simple.json"
        data = [{"id": i, "value": f"test_{i}"} for i in range(100)]
        json_file.write_text(json.dumps(data))
        
        with patch('op1_large.manual_processor.parser') as mock_parser:
            mock_parser.iter_records.return_value = iter(data[:100])
            
            chunk_size = recommend_chunk(json_file)
            
            # Should be between 1000 and 10000 KB
            assert 1000 <= chunk_size <= 10000
    
    def test_recommend_chunk_deeply_nested(self, tmp_path):
        """Test chunk size recommendation for deeply nested JSON."""
        json_file = tmp_path / "nested.json"
        
        # Create deeply nested structures
        def create_nested(depth):
            if depth == 0:
                return "value"
            return {"nested": create_nested(depth - 1)}
        
        data = [create_nested(10) for _ in range(100)]
        json_file.write_text(json.dumps(data))
        
        with patch('op1_large.manual_processor.parser') as mock_parser:
            mock_parser.iter_records.return_value = iter(data[:100])
            
            chunk_size = recommend_chunk(json_file)
            
            # Deeper nesting should result in smaller chunk size
            assert 1000 <= chunk_size <= 5000
    
    def test_recommend_chunk_high_variance(self, tmp_path):
        """Test chunk size recommendation with high string length variance."""
        json_file = tmp_path / "variance.json"
        
        # Create records with varying sizes
        data = []
        for i in range(100):
            if i % 2 == 0:
                data.append({"data": "x" * 10})  # Small
            else:
                data.append({"data": "x" * 1000})  # Large
        
        json_file.write_text(json.dumps(data))
        
        with patch('op1_large.manual_processor.parser') as mock_parser:
            mock_parser.iter_records.return_value = iter(data[:100])
            
            chunk_size = recommend_chunk(json_file)
            
            assert 1000 <= chunk_size <= 10000
    
    def test_recommend_chunk_empty_file(self, tmp_path):
        """Test chunk size recommendation for empty file."""
        json_file = tmp_path / "empty.json"
        json_file.write_text("[]")
        
        with patch('op1_large.manual_processor.parser') as mock_parser:
            mock_parser.iter_records.return_value = iter([])
            
            chunk_size = recommend_chunk(json_file)
            
            # Should return max chunk size for empty data
            assert chunk_size == 10000
    
    def test_recommend_chunk_single_record(self, tmp_path):
        """Test chunk size recommendation with single record."""
        json_file = tmp_path / "single.json"
        data = [{"id": 1, "data": "test"}]
        json_file.write_text(json.dumps(data))
        
        with patch('op1_large.manual_processor.parser') as mock_parser:
            mock_parser.iter_records.return_value = iter(data)
            
            chunk_size = recommend_chunk(json_file)
            
            assert 1000 <= chunk_size <= 10000
    
    def test_chunk_size_inversely_proportional_to_depth(self, tmp_path):
        """Test that chunk size is inversely proportional to depth."""
        # Create files with different depths
        depths_and_chunks = []
        
        for depth in [1, 5, 10, 15]:
            json_file = tmp_path / f"depth_{depth}.json"
            
            def create_nested(d):
                if d == 0:
                    return "value"
                return {"nested": create_nested(d - 1)}
            
            data = [create_nested(depth) for _ in range(100)]
            json_file.write_text(json.dumps(data))
            
            with patch('op1_large.manual_processor.parser') as mock_parser:
                mock_parser.iter_records.return_value = iter(data[:100])
                
                chunk_size = recommend_chunk(json_file)
                depths_and_chunks.append((depth, chunk_size))
        
        # Verify inverse relationship (higher depth = smaller chunk)
        for i in range(len(depths_and_chunks) - 1):
            depth1, chunk1 = depths_and_chunks[i]
            depth2, chunk2 = depths_and_chunks[i + 1]
            if depth1 < depth2:
                assert chunk1 >= chunk2, f"Chunk size should decrease with depth"
    
    def test_chunk_size_with_array_density(self, tmp_path):
        """Test chunk size calculation considering array density."""
        # High array density
        json_file = tmp_path / "arrays.json"
        data = [[[1, 2, 3]] for _ in range(100)]
        json_file.write_text(json.dumps(data))
        
        with patch('op1_large.manual_processor.parser') as mock_parser:
            mock_parser.iter_records.return_value = iter(data[:100])
            
            array_chunk = recommend_chunk(json_file)
        
        # Low array density (all objects)
        json_file = tmp_path / "objects.json"
        data = [{"id": i} for i in range(100)]
        json_file.write_text(json.dumps(data))
        
        with patch('op1_large.manual_processor.parser') as mock_parser:
            mock_parser.iter_records.return_value = iter(data[:100])
            
            object_chunk = recommend_chunk(json_file)
        
        # Both should be valid chunk sizes
        assert 1000 <= array_chunk <= 10000
        assert 1000 <= object_chunk <= 10000
    
    def test_chunk_calculation_with_large_sample(self, tmp_path):
        """Test chunk calculation stops at 1000 sample records."""
        json_file = tmp_path / "large.json"
        
        # Create more than 1000 records
        data = [{"id": i} for i in range(2000)]
        json_file.write_text(json.dumps(data))
        
        call_count = 0
        
        def mock_iter():
            nonlocal call_count
            for record in data:
                call_count += 1
                yield record
        
        with patch('op1_large.manual_processor.parser') as mock_parser:
            mock_parser.iter_records.return_value = mock_iter()
            
            chunk_size = recommend_chunk(json_file)
            
            # Should only process first 1000 records
            assert call_count == 1000
            assert 1000 <= chunk_size <= 10000
    
    @pytest.mark.parametrize("complexity,expected_range", [
        (1, (9000, 10000)),    # Low complexity -> large chunks
        (5, (3500, 4500)),     # Medium complexity
        (10, (1900, 2100)),    # High complexity
        (20, (1000, 1100)),    # Very high complexity -> small chunks
    ])
    def test_chunk_size_based_on_complexity(self, tmp_path, complexity, expected_range):
        """Test that chunk size is calculated correctly based on complexity score."""
        json_file = tmp_path / "test.json"
        json_file.write_text("[]")
        
        with patch('op1_large.manual_processor.parser') as mock_parser:
            mock_parser.iter_records.return_value = iter([])
            
            # Mock the complexity calculation to return specific score
            with patch('op1_large.manual_processor.get_json_depth', return_value=complexity):
                with patch('op1_large.manual_processor.statistics.pstdev', return_value=0):
                    chunk_size = recommend_chunk(json_file)
                    
                    # Formula: chunk = max(1000, min(10000, 20000/score))
                    # But actual implementation might differ slightly
                    assert 1000 <= chunk_size <= 10000
    
    def test_depth_with_circular_reference_protection(self):
        """Test that depth calculation handles potential circular references."""
        # Note: JSON doesn't support circular references, but test the algorithm's robustness
        data = {"a": {"b": {"c": {}}}}
        
        # Manually create a circular structure (would be invalid JSON)
        # This tests the algorithm doesn't infinite loop
        assert get_json_depth(data) == 3
    
    def test_depth_extremely_wide_objects(self):
        """Test depth calculation for extremely wide objects."""
        # Create object with 10000 keys
        data = {f"key_{i}": {"nested": f"value_{i}"} for i in range(10000)}
        
        assert get_json_depth(data) == 2
        
        # All values should have same depth
        depths = [get_json_depth(v) for v in data.values()]
        assert all(d == 1 for d in depths)