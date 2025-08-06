#!/usr/bin/env python3
"""Constant‑memory streaming JSON parser."""
import json
import logging
from typing import Any, Iterator, Optional

import ijson

logger = logging.getLogger(__name__)


class StreamingJSONParser:
    def __init__(self, chunk_size: int = 4096):
        """Initialize streaming parser with configurable chunk size."""
        self.chunk_size = chunk_size
    
    def auto_detect_json_structure(self, path: str) -> str:
        """Return 'array', 'object', or 'unknown'."""
        try:
            with open(path, "rb") as f:
                while True:
                    ch = f.read(1)
                    if not ch:
                        return "unknown"
                    if not ch.isspace():
                        if ch == b"[":
                            return "array"
                        if ch == b"{":
                            return "object"
                        return "unknown"
        except Exception as e:
            logger.error(f"detect structure failed: {e}")
            return "unknown"

    def iter_records(self, path: str, pointer: str = "item") -> Iterator[Any]:
        """Yield parsed objects without loading full file."""
        try:
            with open(path, "rb") as f:
                for obj in ijson.items(f, pointer):
                    yield obj
        except Exception as e:
            logger.error(f"stream parse failed: {e}")
            raise
    
    def parse_file(self, path: str) -> Any:
        """
        Parse entire JSON file (for compatibility with tests).
        Note: This loads entire file into memory - use iter_records for streaming.
        """
        try:
            with open(path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"parse file failed: {e}")
            raise
