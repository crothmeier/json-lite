#!/usr/bin/env python3
"""Test streaming parser on ChatGPT export to verify memory efficiency."""

import sys
import json
import psutil
import traceback
from pathlib import Path
from datetime import datetime
from shared.streaming_parser import StreamingJSONParser
import ijson

def get_memory_usage():
    """Get current memory usage in MB."""
    process = psutil.Process()
    return process.memory_info().rss / 1024 / 1024

def test_streaming_parser(file_path):
    """Test the streaming parser with memory monitoring."""
    print(f"\n{'='*60}")
    print(f"Testing Streaming Parser on: {file_path}")
    print(f"File size: {Path(file_path).stat().st_size / 1024 / 1024:.2f} MB")
    print(f"{'='*60}\n")
    
    # Memory before
    mem_start = get_memory_usage()
    print(f"Memory usage before parsing: {mem_start:.2f} MB")
    
    parser = StreamingJSONParser()
    
    # Test structure detection
    print("\n1. Testing structure detection...")
    structure = parser.auto_detect_json_structure(file_path)
    print(f"   Detected structure: {structure}")
    
    # Count conversations and sample structure
    print("\n2. Counting conversations and analyzing structure...")
    conversations = []
    total_messages = 0
    
    try:
        # Use appropriate pointer based on structure
        pointer = 'item' if structure == 'array' else ''
        
        for idx, record in enumerate(parser.iter_records(file_path, pointer=pointer)):
            if idx < 3:  # Store first 3 for analysis
                conversations.append(record)
            
            # Count messages
            if 'mapping' in record:
                # ChatGPT format with mapping
                total_messages += len(record.get('mapping', {}))
            elif 'messages' in record:
                # Direct messages array (potential Claude format)
                total_messages += len(record.get('messages', []))
            
            if idx % 100 == 0:
                current_mem = get_memory_usage()
                print(f"   Processed {idx} conversations, Memory: {current_mem:.2f} MB")
        
        total_conversations = idx + 1
        
    except Exception as e:
        print(f"   Error during parsing: {e}")
        traceback.print_exc()
        return
    
    # Memory after
    mem_end = get_memory_usage()
    print(f"\n   Total conversations found: {total_conversations}")
    print(f"   Total message nodes: {total_messages}")
    print(f"   Memory usage after parsing: {mem_end:.2f} MB")
    print(f"   Memory increase: {mem_end - mem_start:.2f} MB")
    
    # Analyze first 3 conversation structures
    print("\n3. Analyzing conversation structure...")
    for i, conv in enumerate(conversations[:3], 1):
        print(f"\n   Conversation {i}:")
        print(f"   - ID: {conv.get('id', 'NO_ID')}")
        print(f"   - Title: {conv.get('title', 'NO_TITLE')}")
        print(f"   - Has 'mapping': {'mapping' in conv}")
        print(f"   - Has 'messages': {'messages' in conv}")
        
        if 'mapping' in conv:
            mapping = conv['mapping']
            print(f"   - Mapping nodes: {len(mapping)}")
            # Show first node structure
            first_key = list(mapping.keys())[0] if mapping else None
            if first_key:
                node = mapping[first_key]
                print(f"   - Sample node structure: {list(node.keys())}")
                if 'message' in node and node['message']:
                    msg = node['message']
                    print(f"     - Message keys: {list(msg.keys())}")
                    if 'author' in msg:
                        print(f"     - Author role: {msg['author'].get('role', 'NO_ROLE')}")
                        
        elif 'messages' in conv:
            messages = conv['messages']
            print(f"   - Direct messages: {len(messages)}")
            if messages:
                print(f"   - First message keys: {list(messages[0].keys())}")
    
    # Test extraction of actual messages
    print("\n4. Testing message extraction...")
    if conversations:
        conv = conversations[0]
        messages_extracted = []
        
        if 'mapping' in conv:
            # Extract from mapping (ChatGPT format)
            mapping = conv['mapping']
            for node_id, node in mapping.items():
                if 'message' in node and node['message']:
                    msg = node['message']
                    if 'author' in msg and 'content' in msg:
                        role = msg['author'].get('role', 'unknown')
                        content = msg.get('content', {})
                        
                        # Extract text from content
                        text = ""
                        if isinstance(content, dict):
                            parts = content.get('parts', [])
                            if parts:
                                text = ' '.join(str(p) for p in parts if p)
                        elif isinstance(content, str):
                            text = content
                        
                        if text:
                            messages_extracted.append({
                                'role': role,
                                'text': text[:100] + '...' if len(text) > 100 else text
                            })
        
        elif 'messages' in conv:
            # Direct messages (Claude format)
            for msg in conv['messages'][:5]:
                messages_extracted.append({
                    'role': msg.get('role', msg.get('author', 'unknown')),
                    'text': msg.get('text', msg.get('content', ''))[:100] + '...'
                })
        
        print(f"   Extracted {len(messages_extracted)} messages from first conversation")
        for i, msg in enumerate(messages_extracted[:5], 1):
            print(f"   Message {i}: [{msg['role']}] {msg['text']}")
    
    print(f"\n{'='*60}")
    print("TEST COMPLETE")
    print(f"{'='*60}\n")
    
    return {
        'total_conversations': total_conversations,
        'total_messages': total_messages,
        'memory_used': mem_end - mem_start,
        'structure': structure
    }

def main():
    # Default path - adjust as needed
    default_path = '/data/exports/conversations.json'
    
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
    else:
        file_path = input(f"Enter path to ChatGPT export JSON [{default_path}]: ").strip()
        if not file_path:
            file_path = default_path
    
    if not Path(file_path).exists():
        print(f"Error: File not found: {file_path}")
        sys.exit(1)
    
    # Run test
    results = test_streaming_parser(file_path)
    
    if results:
        print("\nSummary:")
        print(f"- Structure: {results['structure']}")
        print(f"- Conversations: {results['total_conversations']}")
        print(f"- Messages: {results['total_messages']}")
        print(f"- Memory overhead: {results['memory_used']:.2f} MB")
        
        if results['memory_used'] > 100:
            print("\n⚠️  Warning: High memory usage detected!")
            print("   The streaming parser may not be working correctly.")
        else:
            print("\n✓ Memory usage is efficient - streaming is working!")

if __name__ == "__main__":
    # Install psutil if needed
    try:
        import psutil
    except ImportError:
        print("Installing psutil for memory monitoring...")
        import subprocess
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'psutil'])
        import psutil
    
    main()
