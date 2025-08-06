#!/usr/bin/env python3
"""Unit tests for StreamingJSONParser class."""

import pytest
import json
import tempfile
import pathlib
import os
import time
from unittest.mock import patch, mock_open, MagicMock
from memory_profiler import profile
import sys

sys.path.append(str(pathlib.Path(__file__).parent.parent))
from shared.streaming_parser import StreamingJSONParser


class TestStreamingJSONParser:
    """Test suite for StreamingJSONParser functionality."""
    
    @pytest.fixture
    def parser(self):
        """Create a parser instance for testing."""
        return StreamingJSONParser()
    
    @pytest.fixture
    def temp_json_file(self):
        """Create a temporary JSON file for testing."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            data = [{"id": i, "value": f"test_{i}"} for i in range(100)]
            json.dump(data, f)
            temp_path = f.name
        yield temp_path
        os.unlink(temp_path)
    
    def test_auto_detect_array_structure(self, parser, tmp_path):
        """Test that auto_detect correctly identifies array JSON structure."""
        json_file = tmp_path / "test_array.json"
        json_file.write_text('[{"key": "value"}]')
        
        result = parser.auto_detect_json_structure(str(json_file))
        assert result == 'array'
    
    def test_auto_detect_object_structure(self, parser, tmp_path):
        """Test that auto_detect correctly identifies object JSON structure."""
        json_file = tmp_path / "test_object.json"
        json_file.write_text('{"key": "value"}')
        
        result = parser.auto_detect_json_structure(str(json_file))
        assert result == 'object'
    
    def test_auto_detect_with_whitespace(self, parser, tmp_path):
        """Test auto_detect handles leading whitespace correctly."""
        json_file = tmp_path / "test_whitespace.json"
        json_file.write_text('   \n\t  [{"key": "value"}]')
        
        result = parser.auto_detect_json_structure(str(json_file))
        assert result == 'array'
    
    def test_auto_detect_empty_file(self, parser, tmp_path):
        """Test auto_detect returns 'unknown' for empty files."""
        json_file = tmp_path / "empty.json"
        json_file.write_text('')
        
        result = parser.auto_detect_json_structure(str(json_file))
        assert result == 'unknown'
    
    def test_auto_detect_invalid_json(self, parser, tmp_path):
        """Test auto_detect returns 'unknown' for invalid JSON."""
        json_file = tmp_path / "invalid.json"
        json_file.write_text('not json at all')
        
        result = parser.auto_detect_json_structure(str(json_file))
        assert result == 'unknown'
    
    def test_auto_detect_file_not_found(self, parser):
        """Test auto_detect handles missing files gracefully."""
        result = parser.auto_detect_json_structure('/nonexistent/file.json')
        assert result == 'unknown'
    
    def test_iter_records_array(self, parser, tmp_path):
        """Test iterating over array JSON records."""
        json_file = tmp_path / "array.json"
        data = [{"id": i, "value": f"test_{i}"} for i in range(10)]
        json_file.write_text(json.dumps(data))
        
        records = list(parser.iter_records(str(json_file), pointer='item'))
        assert len(records) == 10
        assert records[0] == {"id": 0, "value": "test_0"}
        assert records[9] == {"id": 9, "value": "test_9"}
    
    def test_iter_records_object(self, parser, tmp_path):
        """Test iterating over object JSON structure."""
        json_file = tmp_path / "object.json"
        data = {"users": [{"name": "Alice"}, {"name": "Bob"}]}
        json_file.write_text(json.dumps(data))
        
        records = list(parser.iter_records(str(json_file), pointer='users.item'))
        assert len(records) == 2
        assert records[0] == {"name": "Alice"}
        assert records[1] == {"name": "Bob"}
    
    def test_iter_records_empty_file(self, parser, tmp_path):
        """Test iterating over empty JSON file."""
        json_file = tmp_path / "empty.json"
        json_file.write_text('[]')
        
        records = list(parser.iter_records(str(json_file), pointer='item'))
        assert len(records) == 0
    
    def test_iter_records_malformed_json(self, parser, tmp_path):
        """Test iter_records raises exception for malformed JSON."""
        json_file = tmp_path / "malformed.json"
        json_file.write_text('[{"key": "value"')  # Missing closing brackets
        
        with pytest.raises(Exception):
            list(parser.iter_records(str(json_file), pointer='item'))
    
    def test_iter_records_partial_recovery(self, parser, tmp_path):
        """Test that parser can process valid records before corruption."""
        json_file = tmp_path / "partial.json"
        # Create a file with valid records followed by corruption
        content = '[{"id": 1}, {"id": 2}, {"id": 3}'  # Missing closing bracket
        json_file.write_bytes(content.encode())
        
        # Should raise exception but might yield some valid records first
        with pytest.raises(Exception):
            records = list(parser.iter_records(str(json_file), pointer='item'))
    
    @pytest.mark.parametrize("size_mb,expected_min_records", [
        (1, 1000),    # 1MB file should have at least 1000 small records
        (10, 10000),  # 10MB file should have at least 10000 small records
    ])
    def test_memory_efficiency(self, parser, tmp_path, size_mb, expected_min_records):
        """Test that memory usage remains relatively constant for different file sizes."""
        json_file = tmp_path / f"large_{size_mb}mb.json"
        
        # Generate a large JSON file
        with open(json_file, 'w') as f:
            f.write('[')
            record_count = expected_min_records
            for i in range(record_count):
                record = {"id": i, "data": "x" * 100}  # ~100 bytes per record
                f.write(json.dumps(record))
                if i < record_count - 1:
                    f.write(',')
            f.write(']')
        
        # Process the file and count records
        count = 0
        for _ in parser.iter_records(str(json_file), pointer='item'):
            count += 1
        
        assert count == expected_min_records
    
    def test_deeply_nested_json(self, parser, tmp_path):
        """Test handling of deeply nested JSON structures."""
        json_file = tmp_path / "nested.json"
        
        # Create deeply nested structure
        data = {"level1": {"level2": {"level3": {"level4": {"level5": 
                {"level6": {"level7": {"level8": {"level9": {"level10": "deep_value"}}}}}}}}}}
        json_file.write_text(json.dumps([data]))
        
        records = list(parser.iter_records(str(json_file), pointer='item'))
        assert len(records) == 1
        assert records[0]["level1"]["level2"]["level3"]["level4"]["level5"]["level6"]["level7"]["level8"]["level9"]["level10"] == "deep_value"
    
    def test_mixed_data_types(self, parser, tmp_path):
        """Test handling of mixed data types in JSON."""
        json_file = tmp_path / "mixed.json"
        data = [
            {"string": "test", "number": 42, "float": 3.14, "bool": True, "null": None},
            {"array": [1, 2, 3], "nested": {"key": "value"}},
            123,  # Plain number
            "plain string",
            None
        ]
        json_file.write_text(json.dumps(data))
        
        records = list(parser.iter_records(str(json_file), pointer='item'))
        assert len(records) == 5
        assert records[0]["number"] == 42
        assert records[1]["array"] == [1, 2, 3]
        assert records[2] == 123
        assert records[3] == "plain string"
        assert records[4] is None
    
    def test_unicode_handling(self, parser, tmp_path):
        """Test proper handling of Unicode characters."""
        json_file = tmp_path / "unicode.json"
        data = [
            {"emoji": "🎉🎊", "chinese": "你好", "arabic": "مرحبا"},
            {"special": "café", "math": "∑∏∫"}
        ]
        json_file.write_text(json.dumps(data, ensure_ascii=False))
        
        records = list(parser.iter_records(str(json_file), pointer='item'))
        assert len(records) == 2
        assert records[0]["emoji"] == "🎉🎊"
        assert records[1]["math"] == "∑∏∫"
    
    @pytest.mark.benchmark(group="parser_throughput")
    def test_throughput_small_file(self, parser, tmp_path, benchmark):
        """Benchmark throughput for small files (1MB)."""
        json_file = tmp_path / "small.json"
        data = [{"id": i, "value": f"data_{i}" * 10} for i in range(1000)]
        json_file.write_text(json.dumps(data))
        
        def process_file():
            count = sum(1 for _ in parser.iter_records(str(json_file), pointer='item'))
            return count
        
        result = benchmark(process_file)
        assert result == 1000
    
    @pytest.mark.benchmark(group="parser_throughput")
    def test_throughput_medium_file(self, parser, tmp_path, benchmark):
        """Benchmark throughput for medium files (10MB)."""
        json_file = tmp_path / "medium.json"
        
        # Generate ~10MB file
        with open(json_file, 'w') as f:
            f.write('[')
            for i in range(10000):
                record = {"id": i, "data": "x" * 1000}  # ~1KB per record
                f.write(json.dumps(record))
                if i < 9999:
                    f.write(',')
            f.write(']')
        
        def process_file():
            count = sum(1 for _ in parser.iter_records(str(json_file), pointer='item'))
            return count
        
        result = benchmark(process_file)
        assert result == 10000
    
    def test_batch_processing(self, parser, tmp_path):
        """Test processing records in batches."""
        json_file = tmp_path / "batch.json"
        data = [{"id": i} for i in range(100)]
        json_file.write_text(json.dumps(data))
        
        batch_size = 10
        batches = []
        current_batch = []
        
        for record in parser.iter_records(str(json_file), pointer='item'):
            current_batch.append(record)
            if len(current_batch) >= batch_size:
                batches.append(current_batch)
                current_batch = []
        
        if current_batch:  # Add remaining records
            batches.append(current_batch)
        
        assert len(batches) == 10
        assert all(len(batch) == 10 for batch in batches)
        assert batches[0][0] == {"id": 0}
        assert batches[-1][-1] == {"id": 99}
    
    def test_single_value_json(self, parser, tmp_path):
        """Test handling of single value JSON files."""
        # Test single string
        json_file = tmp_path / "single_string.json"
        json_file.write_text('"hello world"')
        records = list(parser.iter_records(str(json_file), pointer=''))
        assert records == ["hello world"]
        
        # Test single number
        json_file = tmp_path / "single_number.json"
        json_file.write_text('42')
        records = list(parser.iter_records(str(json_file), pointer=''))
        assert records == [42]
        
        # Test single boolean
        json_file = tmp_path / "single_bool.json"
        json_file.write_text('true')
        records = list(parser.iter_records(str(json_file), pointer=''))
        assert records == [True]
    
    def test_large_individual_records(self, parser, tmp_path):
        """Test handling of individual large records."""
        json_file = tmp_path / "large_records.json"
        
        # Create records with large strings
        large_string = "x" * 100000  # 100KB string
        data = [
            {"id": 1, "large_data": large_string},
            {"id": 2, "large_data": large_string}
        ]
        json_file.write_text(json.dumps(data))
        
        records = list(parser.iter_records(str(json_file), pointer='item'))
        assert len(records) == 2
        assert len(records[0]["large_data"]) == 100000
    
    def test_concurrent_parsing(self, parser, tmp_path):
        """Test that multiple parser instances can work independently."""
        json_file1 = tmp_path / "file1.json"
        json_file2 = tmp_path / "file2.json"
        
        data1 = [{"file": 1, "id": i} for i in range(50)]
        data2 = [{"file": 2, "id": i} for i in range(50)]
        
        json_file1.write_text(json.dumps(data1))
        json_file2.write_text(json.dumps(data2))
        
        parser2 = StreamingJSONParser()
        
        records1 = list(parser.iter_records(str(json_file1), pointer='item'))
        records2 = list(parser2.iter_records(str(json_file2), pointer='item'))
        
        assert len(records1) == 50
        assert len(records2) == 50
        assert all(r["file"] == 1 for r in records1)
        assert all(r["file"] == 2 for r in records2)