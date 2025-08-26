#!/usr/bin/env python3
"""Convert Claude JSON exports to ChatGPT mapping format."""

import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any
import uuid
try:
    from tqdm import tqdm  # progress bar
except Exception:
    def tqdm(iterable=None, **kwargs):
        return iterable if iterable is not None else range(0)

def detect_format(file_path: str) -> str:
    """
    Detect if JSON is ChatGPT or Claude format.
    Returns: 'chatgpt', 'claude', or 'unknown'
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        # Read first conversation to detect format
        first_char = f.read(1)
        f.seek(0)
        if first_char == '[':
            # Array format - read first item
            f.read(1)  # skip [
            chunk = f.read(10000)  # Read enough to see structure
            if '"mapping"' in chunk:
                return 'chatgpt'
            elif '"chat_messages"' in chunk:  # Claude uses chat_messages
                return 'claude'
    return 'unknown'

def parse_claude_timestamp(timestamp_str: str) -> float:
    """Convert Claude ISO timestamp to Unix timestamp."""
    try:
        # Handle format: "2025-04-24T09:47:01.469400Z"
        dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        return dt.timestamp()
    except:
        return 0

def convert_claude_message_to_node(message: Dict, index: int, conv_id: str, sender: str = None) -> tuple:
    """Convert a Claude message to ChatGPT mapping node format."""
    node_id = message.get('uuid', f"{conv_id}-msg-{index}")
    # Determine sender (alternate between user and assistant if not specified)
    if sender:
        role = sender
    elif 'sender' in message:
        role = message['sender']
    else:
        # Alternate between user and assistant based on index
        role = 'user' if index % 2 == 0 else 'assistant'
    # Extract message content
    content_text = message.get('text', '')
    # Build ChatGPT-style message
    chatgpt_message = {
        'id': node_id,
        'author': {
            'role': role,
            'metadata': {}
        },
        'content': {
            'content_type': 'text',
            'parts': [content_text] if content_text else []
        },
        'metadata': {},
        'create_time': parse_claude_timestamp(message.get('created_at', '')) if 'created_at' in message else 0
    }
    return node_id, chatgpt_message

def convert_claude_to_chatgpt(claude_conversation: Dict) -> Dict:
    """
    Convert a single Claude conversation to ChatGPT format.

    Claude format from actual export:
    {
        "uuid": "...",
        "name": "...",
        "created_at": "2025-04-24T09:47:01.469400Z",
        "updated_at": "2025-04-24T09:49:51.375155Z",
        "chat_messages": [
            {"uuid": "...", "text": "...", ...},
            ...
        ]
    }

    Returns ChatGPT format with mapping structure.
    """
    conv_id = claude_conversation.get('uuid', str(uuid.uuid4()))
    # Initialize ChatGPT format
    chatgpt_format = {
        'id': conv_id,
        'title': claude_conversation.get('name', 'Untitled'),
        'create_time': parse_claude_timestamp(claude_conversation.get('created_at', '')),
        'update_time': parse_claude_timestamp(claude_conversation.get('updated_at', '')),
        'mapping': {},
        'moderation_results': [],
        'current_node': None,
        'conversation_id': conv_id
    }
    # Get messages
    messages = claude_conversation.get('chat_messages', [])
    if messages:
        # Create mapping structure
        parent_id = None
        for idx, message in enumerate(messages):
            # Determine sender - alternate if not specified
            sender = 'user' if idx % 2 == 0 else 'assistant'
            node_id, chatgpt_message = convert_claude_message_to_node(message, idx, conv_id, sender)
            # Create node in mapping
            node = {
                'id': node_id,
                'message': chatgpt_message,
                'parent': parent_id,
                'children': []
            }
            # Link to parent
            if parent_id and parent_id in chatgpt_format['mapping']:
                chatgpt_format['mapping'][parent_id]['children'].append(node_id)
            chatgpt_format['mapping'][node_id] = node
            parent_id = node_id
            # Update conversation timestamps if needed
            if chatgpt_message['create_time'] > 0:
                if idx == 0 and chatgpt_format['create_time'] == 0:
                    chatgpt_format['create_time'] = chatgpt_message['create_time']
                chatgpt_format['update_time'] = chatgpt_message['create_time']
        # Set current_node to last message
        chatgpt_format['current_node'] = parent_id
    # Ensure we have timestamps
    if chatgpt_format['create_time'] == 0:
        chatgpt_format['create_time'] = datetime.now().timestamp()
    if chatgpt_format['update_time'] == 0:
        chatgpt_format['update_time'] = chatgpt_format['create_time']
    return chatgpt_format

def convert_file(input_path: str, output_path: str = None):
    """Convert Claude export file to ChatGPT format."""
    input_path = Path(input_path)
    if not input_path.exists():
        print(f"Error: File not found: {input_path}")
        return False
    # Auto-generate output path if not provided
    if not output_path:
        output_path = input_path.parent / f"{input_path.stem}_chatgpt_format.json"
    print(f"Converting: {input_path}")
    print(f"Output: {output_path}")
    # Load Claude export
    print("Loading Claude export...")
    with open(input_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    # Handle different structures
    if isinstance(data, list):
        conversations = data
    elif isinstance(data, dict) and 'conversations' in data:
        conversations = data['conversations']
    else:
        print("Error: Unexpected Claude export structure")
        return False
    print(f"Found {len(conversations)} conversations to convert")
    # Convert each conversation
    converted = []
    errors = 0
    for conv in tqdm(conversations, desc="Converting"):
        try:
            converted_conv = convert_claude_to_chatgpt(conv)
            converted.append(converted_conv)
        except Exception as e:
            errors += 1
            if errors <= 5:  # Show first 5 errors
                print(f"\nError converting conversation '{conv.get('name', 'unknown')}': {e}")
            continue
    if errors > 5:
        print(f"... and {errors - 5} more errors")
    # Save converted data
    print(f"Saving converted data...")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(converted, f, indent=2)
    print(f"\nSuccessfully converted {len(converted)} conversations")
    if errors:
        print(f"Failed to convert {errors} conversations")
    # Show statistics
    total_messages = sum(len(c['mapping']) for c in converted)
    print(f"Total messages: {total_messages}")
    print(f"Output file size: {output_path.stat().st_size / 1024 / 1024:.2f} MB")
    return True

def main():
    if len(sys.argv) < 2:
        print("Usage: python claude_to_chatgpt.py <claude_export.json> [output.json]")
        sys.exit(1)
    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None
    # Detect format
    format_type = detect_format(input_file)
    print(f"Detected format: {format_type}")
    if format_type == 'chatgpt':
        print("File is already in ChatGPT format!")
        return
    elif format_type == 'claude':
        print("Converting Claude format to ChatGPT format...")
        success = convert_file(input_file, output_file)
        if success:
            print("\n✅ Conversion complete!")
        else:
            print("\n❌ Conversion failed!")
            sys.exit(1)
    else:
        print("Unknown format. Check file structure.")
        sys.exit(1)

if __name__ == "__main__":
    main()
