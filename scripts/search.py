#!/usr/bin/env python3
"""Search unified conversations database."""

import sqlite3
import sys
from pathlib import Path

def search(query, limit=10):
    db_path = Path.home() / "data" / "unified_conversations.db"
    conn = sqlite3.connect(db_path)
    
    results = conn.execute("""
        SELECT 
            c.conversation_id,
            m.title,
            c.sender,
            snippet(conversations, 3, '**', '**', '...', 50) as snippet,
            m.source
        FROM conversations c
        JOIN metadata m ON c.conversation_id = m.conversation_id
        WHERE conversations MATCH ?
        LIMIT ?
    """, (query, limit)).fetchall()
    
    print(f"\nFound {len(results)} results for '{query}':\n")
    
    for conv_id, title, sender, snippet, source in results:
        print(f"[{source}] {title}")
        print(f"  {sender}: {snippet}")
        print()
    
    conn.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: ./search.py <query>")
        sys.exit(1)
    
    search(' '.join(sys.argv[1:]))
