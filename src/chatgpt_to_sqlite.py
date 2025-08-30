#!/usr/bin/env python3
"""
ChatGPT conversation importer for SQLite FTS5 database.
"""

import json
import sqlite3
import logging
from datetime import datetime
from typing import Dict, List, Optional
import uuid

logger = logging.getLogger(__name__)


class ChatGPTImporter:
    """Imports ChatGPT conversations into SQLite FTS5 database."""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.ensure_database()
    
    def ensure_database(self):
        """Ensure database tables exist."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create FTS5 table for searchable content
        cursor.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS conversations USING fts5(
                conversation_id,
                timestamp,
                sender,
                content,
                tokenize='porter unicode61'
            )
        """)
        
        # Create metadata table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS metadata (
                conversation_id TEXT PRIMARY KEY,
                title TEXT,
                message_count INTEGER,
                created_at TEXT,
                updated_at TEXT,
                source TEXT DEFAULT 'ChatGPT'
            )
        """)
        
        conn.commit()
        conn.close()
    
    def import_conversation(self, conversation: Dict) -> bool:
        """Import a single ChatGPT conversation."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Extract conversation metadata
            conv_id = conversation.get('id') or str(uuid.uuid4())
            title = conversation.get('title', 'Untitled Conversation')
            created_at = conversation.get('create_time')
            updated_at = conversation.get('update_time')
            
            # Convert timestamps if needed
            if created_at and isinstance(created_at, (int, float)):
                created_at = datetime.fromtimestamp(created_at).isoformat()
            if updated_at and isinstance(updated_at, (int, float)):
                updated_at = datetime.fromtimestamp(updated_at).isoformat()
            
            # Check if conversation already exists
            cursor.execute(
                "SELECT conversation_id FROM metadata WHERE conversation_id = ?",
                (conv_id,)
            )
            if cursor.fetchone():
                logger.debug(f"Conversation {conv_id} already exists, skipping")
                conn.close()
                return False
            
            # Extract messages
            messages = []
            mapping = conversation.get('mapping', {})
            
            # Build message tree from mapping
            for node_id, node in mapping.items():
                message = node.get('message')
                if message and message.get('content'):
                    content = message.get('content', {})
                    
                    # Extract text content
                    text = None
                    if isinstance(content, dict):
                        parts = content.get('parts', [])
                        if parts and isinstance(parts[0], str):
                            text = parts[0]
                    elif isinstance(content, str):
                        text = content
                    
                    if text:
                        author = message.get('author', {})
                        role = author.get('role') if isinstance(author, dict) else str(author)
                        
                        # Get timestamp
                        timestamp = message.get('create_time')
                        if timestamp and isinstance(timestamp, (int, float)):
                            timestamp = datetime.fromtimestamp(timestamp).isoformat()
                        
                        messages.append({
                            'sender': role or 'unknown',
                            'content': text,
                            'timestamp': timestamp or datetime.now().isoformat()
                        })
            
            # If no messages found in mapping, try alternative structure
            if not messages and 'messages' in conversation:
                for msg in conversation['messages']:
                    if isinstance(msg, dict) and msg.get('content'):
                        messages.append({
                            'sender': msg.get('role', 'unknown'),
                            'content': msg.get('content'),
                            'timestamp': msg.get('timestamp', datetime.now().isoformat())
                        })
            
            # Insert metadata
            cursor.execute("""
                INSERT INTO metadata (conversation_id, title, message_count, created_at, updated_at, source)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (conv_id, title, len(messages), created_at, updated_at, 
                  conversation.get('source', 'ChatGPT')))
            
            # Insert messages into FTS5 table
            for msg in messages:
                cursor.execute("""
                    INSERT INTO conversations (conversation_id, timestamp, sender, content)
                    VALUES (?, ?, ?, ?)
                """, (conv_id, msg['timestamp'], msg['sender'], msg['content']))
            
            conn.commit()
            conn.close()
            
            logger.debug(f"Imported conversation {conv_id} with {len(messages)} messages")
            return True
            
        except Exception as e:
            logger.error(f"Failed to import conversation: {e}")
            if conn:
                conn.rollback()
                conn.close()
            return False