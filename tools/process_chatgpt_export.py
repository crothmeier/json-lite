#!/usr/bin/env python3
"""Memory-efficient ChatGPT export processor using ijson streaming."""

import os
import re
import sys
import ijson
import resource
from pathlib import Path
from typing import Optional, Generator, Dict, Any


class ChatGPTExportProcessor:
    """Streams ChatGPT export JSON and extracts conversations to markdown files."""
    
    def __init__(self, output_dir: Path, verbose: bool = False):
        self.output_dir = output_dir
        self.verbose = verbose
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._conversation_count = 0
        self._message_count = 0
        
    def process_stream(self, json_path: Path, limit: Optional[int] = None, 
                      progress: bool = False) -> int:
        """
        Stream process ChatGPT export JSON file.
        
        Args:
            json_path: Path to the ChatGPT export JSON file
            limit: Limit number of conversations to process
            progress: Show progress during processing
            
        Returns:
            Number of conversations processed
        """
        with open(json_path, 'rb') as f:
            parser = ijson.items(f, 'item')
            
            for conversation in parser:
                if limit and self._conversation_count >= limit:
                    break
                    
                self._process_conversation(conversation)
                self._conversation_count += 1
                
                if progress and self._conversation_count % 10 == 0:
                    self._print_progress()
                    
        if progress:
            self._print_final_stats()
            
        return self._conversation_count
    
    def _process_conversation(self, conversation: Dict[str, Any]) -> None:
        """Process a single conversation and write to markdown file."""
        conv_id = conversation.get('id', 'unknown')
        title = conversation.get('title', 'Untitled')
        create_time = conversation.get('create_time', 0)
        
        # Sanitize title for filename
        safe_title = re.sub(r'[^\w\s-]', '', title)[:100]
        safe_title = re.sub(r'[-\s]+', '-', safe_title).strip('-')
        
        filename = f"{conv_id}_{safe_title}.md" if safe_title else f"{conv_id}.md"
        output_path = self.output_dir / filename
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(f"# {title}\n\n")
            f.write(f"**ID:** {conv_id}\n")
            f.write(f"**Created:** {create_time}\n\n")
            f.write("---\n\n")
            
            # Extract messages from mapping
            mapping = conversation.get('mapping', {})
            messages = self._extract_messages(mapping)
            
            for msg in messages:
                self._message_count += 1
                role = msg.get('role', 'unknown')
                content = msg.get('content', '')
                
                if role == 'user':
                    f.write(f"## User\n\n{content}\n\n")
                elif role == 'assistant':
                    f.write(f"## Assistant\n\n{content}\n\n")
                elif role == 'system' and content:
                    f.write(f"## System\n\n{content}\n\n")
                    
    def _extract_messages(self, mapping: Dict[str, Any]) -> Generator[Dict[str, Any], None, None]:
        """Extract messages from conversation mapping in order."""
        if not mapping:
            return
            
        # Find root node and traverse
        root_id = None
        for node_id, node in mapping.items():
            if node.get('parent') is None:
                root_id = node_id
                break
                
        if not root_id:
            return
            
        # Traverse message tree
        visited = set()
        queue = [root_id]
        
        while queue:
            node_id = queue.pop(0)
            if node_id in visited:
                continue
                
            visited.add(node_id)
            node = mapping.get(node_id, {})
            
            # Extract message content
            message = node.get('message')
            if message:
                author = message.get('author', {})
                role = author.get('role', 'unknown')
                content_parts = message.get('content', {}).get('parts', [])
                content = '\n'.join(str(part) for part in content_parts if part)
                
                if content:
                    yield {'role': role, 'content': content}
                    
            # Add children to queue
            children = node.get('children', [])
            queue.extend(children)
            
    def _print_progress(self) -> None:
        """Print progress statistics."""
        rss_mb = self._get_rss_mb()
        print(f"Processed {self._conversation_count} conversations, "
              f"{self._message_count} messages, RSS: {rss_mb:.1f} MB")
        
    def _print_final_stats(self) -> None:
        """Print final processing statistics."""
        rss_mb = self._get_rss_mb()
        print(f"\nCompleted: {self._conversation_count} conversations, "
              f"{self._message_count} messages")
        print(f"Peak RSS: {rss_mb:.1f} MB")
        print(f"Output directory: {self.output_dir}")
        
    def _get_rss_mb(self) -> float:
        """Get current RSS in MB."""
        try:
            # Linux/Unix
            usage = resource.getrusage(resource.RUSAGE_SELF)
            return usage.ru_maxrss / 1024  # KB to MB on Linux
        except:
            # Fallback for other platforms
            try:
                import psutil
                process = psutil.Process()
                return process.memory_info().rss / (1024 * 1024)
            except:
                return 0.0


def process_chatgpt_export(input_json: Path, output_dir: Path, 
                          limit: Optional[int] = None,
                          progress: bool = False,
                          verbose: bool = False) -> int:
    """
    Main entry point for processing ChatGPT export.
    
    Args:
        input_json: Path to ChatGPT export JSON file
        output_dir: Directory to write markdown files
        limit: Limit number of conversations to process
        progress: Show progress during processing
        verbose: Enable verbose output
        
    Returns:
        Number of conversations processed
    """
    if not input_json.exists():
        raise FileNotFoundError(f"Input file not found: {input_json}")
        
    processor = ChatGPTExportProcessor(output_dir, verbose=verbose)
    return processor.process_stream(input_json, limit=limit, progress=progress)


if __name__ == '__main__':
    # Simple CLI for testing
    if len(sys.argv) < 3:
        print("Usage: process_chatgpt_export.py <input.json> <output_dir>")
        sys.exit(1)
        
    input_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2])
    
    count = process_chatgpt_export(input_path, output_path, progress=True)
    print(f"Successfully processed {count} conversations")