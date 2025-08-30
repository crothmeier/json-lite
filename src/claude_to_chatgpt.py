#!/usr/bin/env python3
"""
Claude to ChatGPT format converter.
"""

import json
import logging
from datetime import datetime
from typing import Dict, List, Optional
import uuid

logger = logging.getLogger(__name__)


class ClaudeConverter:
    """Converts Claude conversation format to ChatGPT format."""
    
    def convert_conversation(self, claude_conv: Dict) -> Optional[Dict]:
        """Convert a Claude conversation to ChatGPT format."""
        try:
            # Extract basic info
            conv_id = claude_conv.get('uuid') or str(uuid.uuid4())
            title = claude_conv.get('name') or claude_conv.get('title') or 'Untitled'
            created_at = claude_conv.get('created_at') or datetime.now().isoformat()
            updated_at = claude_conv.get('updated_at') or created_at
            
            # Build ChatGPT-style conversation
            chatgpt_conv = {
                'id': conv_id,
                'title': title,
                'create_time': created_at,
                'update_time': updated_at,
                'source': 'Claude',
                'mapping': {}
            }
            
            # Convert messages
            messages = []
            chat_messages = claude_conv.get('chat_messages', [])
            
            for idx, msg in enumerate(chat_messages):
                node_id = f"node_{idx}"
                
                # Extract message content
                text = msg.get('text', '')
                sender = msg.get('sender', 'unknown')
                
                # Map Claude sender to ChatGPT role
                if sender.lower() == 'human':
                    role = 'user'
                elif sender.lower() == 'assistant':
                    role = 'assistant'
                else:
                    role = sender.lower()
                
                # Get timestamp
                timestamp = msg.get('created_at')
                if not timestamp:
                    timestamp = datetime.now().isoformat()
                
                # Add to mapping (ChatGPT structure)
                chatgpt_conv['mapping'][node_id] = {
                    'id': node_id,
                    'message': {
                        'id': f"msg_{idx}",
                        'author': {'role': role},
                        'content': {'parts': [text]},
                        'create_time': timestamp
                    }
                }
                
                messages.append({
                    'role': role,
                    'content': text,
                    'timestamp': timestamp
                })
            
            # Add messages array as fallback
            chatgpt_conv['messages'] = messages
            
            return chatgpt_conv
            
        except Exception as e:
            logger.error(f"Failed to convert Claude conversation: {e}")
            return None