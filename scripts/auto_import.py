#!/usr/bin/env python3
"""
Auto-import watcher for ChatGPT and Claude conversation exports.
Monitors directories for new files and automatically imports them to SQLite.
"""

import os
import sys
import time
import json
import shutil
import logging
import hashlib
import zipfile
import sqlite3
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import config
from src.chatgpt_to_sqlite import ChatGPTImporter
from src.claude_to_chatgpt import ClaudeConverter

# Configuration from centralized config
CHATGPT_EXPORT_DIR = str(config.CHATGPT_EXPORT_DIR)
CLAUDE_EXPORT_DIR = str(config.CLAUDE_EXPORT_DIR)
DATABASE_PATH = str(config.DATABASE_PATH)
SCRIPT_DIR = Path(__file__).parent
LOG_FILE = str(SCRIPT_DIR / "auto_import.log")
CHECK_INTERVAL = 300  # 5 minutes in seconds
STATE_FILE = str(SCRIPT_DIR / ".auto_import_state.json")

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class FileWatcher:
    """Watches directories for new files and processes them."""
    
    def __init__(self):
        self.processed_files = self.load_state()
        self.ensure_directories()
        
    def ensure_directories(self):
        """Create necessary directories if they don't exist."""
        dirs = [
            CHATGPT_EXPORT_DIR,
            CLAUDE_EXPORT_DIR,
            os.path.join(CHATGPT_EXPORT_DIR, "processed"),
            os.path.join(CLAUDE_EXPORT_DIR, "processed"),
        ]
        for dir_path in dirs:
            Path(dir_path).mkdir(parents=True, exist_ok=True)
            logger.debug(f"Ensured directory exists: {dir_path}")
    
    def load_state(self) -> Set[str]:
        """Load the set of already processed files."""
        if os.path.exists(STATE_FILE):
            try:
                with open(STATE_FILE, 'r') as f:
                    data = json.load(f)
                    return set(data.get('processed_files', []))
            except Exception as e:
                logger.warning(f"Could not load state file: {e}")
        return set()
    
    def save_state(self):
        """Save the current state of processed files."""
        try:
            with open(STATE_FILE, 'w') as f:
                json.dump({
                    'processed_files': list(self.processed_files),
                    'last_updated': datetime.now().isoformat()
                }, f, indent=2)
        except Exception as e:
            logger.error(f"Could not save state file: {e}")
    
    def get_file_hash(self, filepath: str) -> str:
        """Calculate MD5 hash of a file for duplicate detection."""
        hash_md5 = hashlib.md5()
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    
    def move_to_processed(self, filepath: str) -> str:
        """Move a file to the processed subdirectory with timestamp."""
        dirname = os.path.dirname(filepath)
        basename = os.path.basename(filepath)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Add timestamp to filename
        name, ext = os.path.splitext(basename)
        new_name = f"{name}_{timestamp}{ext}"
        
        processed_dir = os.path.join(dirname, "processed")
        new_path = os.path.join(processed_dir, new_name)
        
        shutil.move(filepath, new_path)
        logger.info(f"Moved processed file to: {new_path}")
        return new_path
    
    def process_chatgpt_export(self, filepath: str) -> bool:
        """Process a ChatGPT JSON export file."""
        logger.info(f"Processing ChatGPT export: {filepath}")
        
        try:
            # Import to SQLite
            importer = ChatGPTImporter(DATABASE_PATH)
            
            # Read the JSON file
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Import conversations
            imported_count = 0
            if isinstance(data, list):
                conversations = data
            else:
                conversations = data.get('conversations', [])
            
            for conversation in conversations:
                try:
                    importer.import_conversation(conversation)
                    imported_count += 1
                except Exception as e:
                    logger.error(f"Failed to import conversation: {e}")
            
            logger.info(f"Successfully imported {imported_count} conversations from ChatGPT export")
            
            # Mark as processed
            file_hash = self.get_file_hash(filepath)
            self.processed_files.add(file_hash)
            
            # Move to processed directory
            self.move_to_processed(filepath)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to process ChatGPT export {filepath}: {e}")
            return False
    
    def process_claude_export(self, filepath: str) -> bool:
        """Process a Claude ZIP export file."""
        logger.info(f"Processing Claude export: {filepath}")
        
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                # Extract ZIP file
                logger.debug(f"Extracting ZIP to temp directory: {temp_dir}")
                with zipfile.ZipFile(filepath, 'r') as zip_ref:
                    zip_ref.extractall(temp_dir)
                
                # Find JSON files in extracted content
                json_files = []
                for root, dirs, files in os.walk(temp_dir):
                    for file in files:
                        if file.endswith('.json'):
                            json_files.append(os.path.join(root, file))
                
                if not json_files:
                    logger.warning(f"No JSON files found in Claude export: {filepath}")
                    return False
                
                # Convert Claude format to ChatGPT format
                converter = ClaudeConverter()
                all_converted = []
                
                for json_file in json_files:
                    logger.debug(f"Converting Claude file: {json_file}")
                    with open(json_file, 'r', encoding='utf-8') as f:
                        claude_data = json.load(f)
                    
                    # Convert to ChatGPT format
                    if isinstance(claude_data, dict):
                        claude_conversations = [claude_data]
                    elif isinstance(claude_data, list):
                        claude_conversations = claude_data
                    else:
                        logger.warning(f"Unexpected data format in {json_file}")
                        continue
                    
                    for conv in claude_conversations:
                        try:
                            converted = converter.convert_conversation(conv)
                            if converted:
                                all_converted.append(converted)
                        except Exception as e:
                            logger.error(f"Failed to convert Claude conversation: {e}")
                
                # Import converted conversations to SQLite
                if all_converted:
                    importer = ChatGPTImporter(DATABASE_PATH)
                    imported_count = 0
                    
                    for conversation in all_converted:
                        try:
                            # Add source field to indicate it came from Claude
                            conversation['source'] = 'Claude'
                            importer.import_conversation(conversation)
                            imported_count += 1
                        except Exception as e:
                            logger.error(f"Failed to import converted conversation: {e}")
                    
                    logger.info(f"Successfully imported {imported_count} conversations from Claude export")
                else:
                    logger.warning("No conversations were successfully converted")
                
                # Mark as processed
                file_hash = self.get_file_hash(filepath)
                self.processed_files.add(file_hash)
                
                # Move to processed directory
                self.move_to_processed(filepath)
                
                return True
                
        except Exception as e:
            logger.error(f"Failed to process Claude export {filepath}: {e}")
            return False
    
    def scan_directory(self, directory: str, extension: str) -> List[str]:
        """Scan directory for new files with given extension."""
        new_files = []
        
        try:
            for file in os.listdir(directory):
                if file.endswith(extension):
                    filepath = os.path.join(directory, file)
                    
                    # Skip if in processed directory
                    if "processed" in filepath:
                        continue
                    
                    # Check if already processed
                    file_hash = self.get_file_hash(filepath)
                    if file_hash not in self.processed_files:
                        new_files.append(filepath)
                        logger.debug(f"Found new file: {filepath}")
                    
        except Exception as e:
            logger.error(f"Error scanning directory {directory}: {e}")
        
        return new_files
    
    def process_new_files(self):
        """Check for and process new files in watched directories."""
        logger.debug("Scanning for new files...")
        
        # Check for new ChatGPT exports
        chatgpt_files = self.scan_directory(CHATGPT_EXPORT_DIR, ".json")
        for filepath in chatgpt_files:
            logger.info(f"Found new ChatGPT export: {filepath}")
            self.process_chatgpt_export(filepath)
            self.save_state()
        
        # Check for new Claude exports
        claude_files = self.scan_directory(CLAUDE_EXPORT_DIR, ".zip")
        for filepath in claude_files:
            logger.info(f"Found new Claude export: {filepath}")
            self.process_claude_export(filepath)
            self.save_state()
        
        if not chatgpt_files and not claude_files:
            logger.debug("No new files found")
    
    def run(self):
        """Main loop to continuously watch for new files."""
        logger.info("Starting auto-import watcher...")
        logger.info(f"Watching ChatGPT exports: {CHATGPT_EXPORT_DIR}")
        logger.info(f"Watching Claude exports: {CLAUDE_EXPORT_DIR}")
        logger.info(f"Check interval: {CHECK_INTERVAL} seconds")
        logger.info(f"Database: {DATABASE_PATH}")
        
        try:
            while True:
                self.process_new_files()
                time.sleep(CHECK_INTERVAL)
                
        except KeyboardInterrupt:
            logger.info("Shutting down auto-import watcher...")
            self.save_state()
        except Exception as e:
            logger.error(f"Unexpected error in main loop: {e}")
            self.save_state()
            raise


def main():
    """Main entry point."""
    try:
        # Check if database exists
        if not os.path.exists(DATABASE_PATH):
            logger.error(f"Database not found: {DATABASE_PATH}")
            logger.info("Please ensure the database is created first")
            sys.exit(1)
        
        # Create and run watcher
        watcher = FileWatcher()
        watcher.run()
        
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()