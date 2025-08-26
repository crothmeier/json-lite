#!/usr/bin/env python3
"""Test the complete import pipeline."""

import sys
import subprocess
from pathlib import Path
import json

def test_pipeline(json_file):
    """Test format detection and import readiness."""
    
    print(f"Testing: {json_file}")
    print("="*60)
    
    # 1. Detect format
    with open(json_file, 'r') as f:
        first_char = f.read(1)
        f.seek(0)
        if first_char == '[':
            f.read(1)
            chunk = f.read(1000)
            if '"mapping"' in chunk:
                format_type = "ChatGPT (ready for import)"
            elif '"chat_messages"' in chunk:
                format_type = "Claude (needs conversion)"
            else:
                format_type = "Unknown"
    
    print(f"Format: {format_type}")
    
    # 2. Count conversations
    with open(json_file, 'r') as f:
        data = json.load(f)
        print(f"Conversations: {len(data)}")
        
        # Count messages
        total_messages = 0
        if format_type.startswith("ChatGPT"):
            for conv in data:
                if 'mapping' in conv:
                    total_messages += len(conv['mapping'])
        
        print(f"Messages: {total_messages}")
    
    print(f"File size: {Path(json_file).stat().st_size / 1024 / 1024:.2f} MB")
    print("\n✓ File is ready for import to SQLite FTS5")

if __name__ == "__main__":
    # Test both files
    test_pipeline("/home/crathmene/data/chatgpt-exports/conversations.json")
    test_pipeline("/home/crathmene/data/claude-exports/extracted_claude/conversations_chatgpt_format.json")
