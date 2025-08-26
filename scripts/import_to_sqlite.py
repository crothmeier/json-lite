#!/usr/bin/env python3
"""Import ChatGPT-format JSON files into SQLite FTS5 database."""

import json
import sqlite3
import sys
from pathlib import Path
from datetime import datetime
from tqdm import tqdm

def create_database(db_path):
    """Create SQLite database with FTS5 tables."""
    conn = sqlite3.connect(db_path)
    
    # Create FTS5 virtual table for searching
    conn.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS conversations USING fts5(
            conversation_id,
            timestamp,
            sender,
            content,
            tokenize='porter unicode61'
        )
    """)
    
    # Create metadata table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS metadata (
            conversation_id TEXT PRIMARY KEY,
            title TEXT,
            message_count INTEGER,
            created_at TEXT,
            updated_at TEXT,
            source TEXT
        )
    """)
    
    conn.commit()
    return conn

def import_file(json_path, conn, source_name):
    """Import a ChatGPT-format JSON file."""
    print(f"\nImporting {source_name}: {json_path}")
    
    with open(json_path, 'r') as f:
        data = json.load(f)
    
    total_messages = 0
    
    for conv in tqdm(data, desc=f"Processing {source_name}"):
        conv_id = conv.get('id', '')
        title = conv.get('title', 'Untitled')
        
        # Convert timestamps
        created = datetime.fromtimestamp(conv.get('create_time', 0)).isoformat()
        updated = datetime.fromtimestamp(conv.get('update_time', 0)).isoformat()
        
        # Extract messages from mapping
        mapping = conv.get('mapping', {})
        message_count = 0
        
        for node_id, node in mapping.items():
            if 'message' in node and node['message']:
                msg = node['message']
                author = msg.get('author', {}).get('role', 'unknown')
                
                # Extract content
                content_parts = msg.get('content', {}).get('parts', [])
                content = ' '.join(str(p) for p in content_parts if p)
                
                if content:
                    # Insert into FTS table
                    timestamp = datetime.fromtimestamp(msg.get('create_time', 0)).isoformat()
                    conn.execute("""
                        INSERT INTO conversations (conversation_id, timestamp, sender, content)
                        VALUES (?, ?, ?, ?)
                    """, (conv_id, timestamp, author, content))
                    message_count += 1
                    total_messages += 1
        
        # Insert metadata
        conn.execute("""
            INSERT OR REPLACE INTO metadata (conversation_id, title, message_count, created_at, updated_at, source)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (conv_id, title, message_count, created, updated, source_name))
    
    conn.commit()
    print(f"Imported {len(data)} conversations with {total_messages} messages")
    return len(data), total_messages

def main():
    # Database path
    db_path = Path.home() / "data" / "unified_conversations.db"
    
    # Create/connect to database
    conn = create_database(db_path)
    
    # Import ChatGPT data
    chatgpt_path = Path.home() / "data" / "chatgpt-exports" / "conversations.json"
    if chatgpt_path.exists():
        import_file(chatgpt_path, conn, "ChatGPT")
    
    # Import converted Claude data
    claude_path = Path.home() / "data" / "claude-exports" / "extracted_claude" / "conversations_chatgpt_format.json"
    if claude_path.exists():
        import_file(claude_path, conn, "Claude")
    
    # Optimize database
    print("\nOptimizing database...")
    conn.execute("INSERT INTO conversations(conversations) VALUES('optimize')")
    conn.commit()  # Add this line - commit before VACUUM
    conn.execute("VACUUM")
    conn.execute("ANALYZE")
    
    # Show statistics
    total_convs = conn.execute("SELECT COUNT(*) FROM metadata").fetchone()[0]
    total_msgs = conn.execute("SELECT COUNT(*) FROM conversations").fetchone()[0]
    
    print(f"\nDatabase created: {db_path}")
    print(f"Total conversations: {total_convs}")
    print(f"Total messages: {total_msgs}")
    print(f"Database size: {db_path.stat().st_size / 1024 / 1024:.2f} MB")
    
    # Test search
    print("\nTest search for 'python':")
    results = conn.execute("""
        SELECT conversation_id, sender, snippet(conversations, 3, '...', '...', '...', 20)
        FROM conversations
        WHERE conversations MATCH 'python'
        LIMIT 5
    """).fetchall()
    
    for r in results:
        print(f"  [{r[1]}] {r[2]}")
    
    conn.close()

if __name__ == "__main__":
    main()
