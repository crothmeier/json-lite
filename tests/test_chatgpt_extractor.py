#!/usr/bin/env python3
"""Tests for ChatGPT export extractor."""

import os
import sys
import json
import tempfile
import resource
from pathlib import Path
from unittest import mock

import pytest

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.process_chatgpt_export import (
    ChatGPTExportProcessor,
    process_chatgpt_export
)


class TestChatGPTExtractor:
    """Contract and performance tests for ChatGPT extractor."""
    
    @pytest.fixture
    def sample_json_path(self):
        """Path to sample ChatGPT export fixture."""
        return Path(__file__).parent / "fixtures" / "chatgpt_sample.json"
    
    @pytest.fixture
    def temp_output_dir(self):
        """Create temporary output directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)
    
    def test_processor_creates_markdown_files(self, sample_json_path, temp_output_dir):
        """Test that processor creates markdown files for each conversation."""
        processor = ChatGPTExportProcessor(temp_output_dir)
        count = processor.process_stream(sample_json_path)
        
        assert count == 2
        
        # Check files were created
        files = list(temp_output_dir.glob("*.md"))
        assert len(files) == 2
        
        # Check file naming
        filenames = [f.name for f in files]
        assert any("conv-123abc" in name for name in filenames)
        assert any("conv-456def" in name for name in filenames)
    
    def test_markdown_content_format(self, sample_json_path, temp_output_dir):
        """Test that markdown files have correct content structure."""
        processor = ChatGPTExportProcessor(temp_output_dir)
        processor.process_stream(sample_json_path)
        
        # Read first conversation file
        conv_file = next(temp_output_dir.glob("*conv-123abc*.md"))
        content = conv_file.read_text()
        
        # Check content structure
        assert "# Sample Conversation about Python" in content
        assert "**ID:** conv-123abc" in content
        assert "## User" in content
        assert "## Assistant" in content
        assert "How do I read a JSON file in Python?" in content
        assert "json.load(file)" in content
    
    def test_memory_efficiency(self, sample_json_path, temp_output_dir):
        """Test that processor stays within memory limits."""
        # Get initial RSS
        initial_rss = self._get_rss_mb()
        
        processor = ChatGPTExportProcessor(temp_output_dir)
        processor.process_stream(sample_json_path)
        
        # Get peak RSS
        peak_rss = self._get_rss_mb()
        memory_used = peak_rss - initial_rss
        
        # Assert memory usage is reasonable (for small test file should be < 50MB)
        assert memory_used < 50, f"Memory usage {memory_used:.1f} MB exceeds limit"
    
    def test_large_file_memory_constraint(self, temp_output_dir):
        """Test memory constraint with simulated large file."""
        # Create a large test file with many conversations
        large_file = temp_output_dir / "large_test.json"
        conversations = []
        
        for i in range(100):  # Create 100 conversations
            conv = {
                "id": f"conv-{i:06d}",
                "title": f"Conversation {i}",
                "create_time": 1704067200 + i * 3600,
                "mapping": {
                    f"msg-{i}-1": {
                        "parent": None,
                        "children": [f"msg-{i}-2"],
                        "message": {
                            "author": {"role": "user"},
                            "content": {"parts": [f"Question {i}" * 100]}  # Repeat to make larger
                        }
                    },
                    f"msg-{i}-2": {
                        "parent": f"msg-{i}-1",
                        "children": [],
                        "message": {
                            "author": {"role": "assistant"},
                            "content": {"parts": [f"Answer {i}" * 200]}  # Large response
                        }
                    }
                }
            }
            conversations.append(conv)
        
        # Write as JSON
        with open(large_file, 'w') as f:
            json.dump(conversations, f)
        
        # Process with memory tracking
        initial_rss = self._get_rss_mb()
        
        processor = ChatGPTExportProcessor(temp_output_dir / "output")
        count = processor.process_stream(large_file, limit=50)  # Process first 50
        
        peak_rss = self._get_rss_mb()
        memory_used = peak_rss - initial_rss
        
        assert count == 50
        assert memory_used < 120, f"Memory usage {memory_used:.1f} MB exceeds 120 MB limit"
    
    def test_cli_integration(self, sample_json_path, temp_output_dir):
        """Test CLI function integration."""
        count = process_chatgpt_export(
            input_json=sample_json_path,
            output_dir=temp_output_dir,
            progress=False,
            verbose=False
        )
        
        assert count == 2
        assert len(list(temp_output_dir.glob("*.md"))) == 2
    
    def test_limit_parameter(self, sample_json_path, temp_output_dir):
        """Test limiting number of conversations processed."""
        processor = ChatGPTExportProcessor(temp_output_dir)
        count = processor.process_stream(sample_json_path, limit=1)
        
        assert count == 1
        assert len(list(temp_output_dir.glob("*.md"))) == 1
    
    def test_progress_output(self, sample_json_path, temp_output_dir, capsys):
        """Test progress output during processing."""
        processor = ChatGPTExportProcessor(temp_output_dir, verbose=True)
        processor.process_stream(sample_json_path, progress=True)
        
        captured = capsys.readouterr()
        assert "Completed:" in captured.out
        assert "conversations" in captured.out
    
    def test_handles_missing_fields(self, temp_output_dir):
        """Test handling of conversations with missing fields."""
        # Create test data with missing fields
        test_data = [{
            "id": "test-1",
            # Missing title
            "mapping": {
                "msg-1": {
                    "message": {
                        "author": {"role": "user"},
                        "content": {"parts": ["Test"]}
                    }
                }
            }
        }]
        
        test_file = temp_output_dir / "test.json"
        with open(test_file, 'w') as f:
            json.dump(test_data, f)
        
        processor = ChatGPTExportProcessor(temp_output_dir / "output")
        count = processor.process_stream(test_file)
        
        assert count == 1
        files = list((temp_output_dir / "output").glob("*.md"))
        assert len(files) == 1
        
        # Check content has default title
        content = files[0].read_text()
        assert "Untitled" in content
    
    def test_sanitizes_filenames(self, temp_output_dir):
        """Test that special characters in titles are sanitized."""
        test_data = [{
            "id": "test-special",
            "title": "Test: File/Name? <With> |Special| *Chars*",
            "mapping": {}
        }]
        
        test_file = temp_output_dir / "test.json"
        with open(test_file, 'w') as f:
            json.dump(test_data, f)
        
        processor = ChatGPTExportProcessor(temp_output_dir / "output")
        processor.process_stream(test_file)
        
        files = list((temp_output_dir / "output").glob("*.md"))
        assert len(files) == 1
        
        # Check filename doesn't contain special chars
        filename = files[0].name
        assert ":" not in filename
        assert "/" not in filename
        assert "?" not in filename
        assert "<" not in filename
        assert ">" not in filename
        assert "|" not in filename
        assert "*" not in filename
    
    def _get_rss_mb(self) -> float:
        """Get current RSS in MB."""
        try:
            # Linux/Unix
            usage = resource.getrusage(resource.RUSAGE_SELF)
            return usage.ru_maxrss / 1024  # KB to MB on Linux
        except:
            # Fallback
            try:
                import psutil
                process = psutil.Process()
                return process.memory_info().rss / (1024 * 1024)
            except:
                return 0.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])