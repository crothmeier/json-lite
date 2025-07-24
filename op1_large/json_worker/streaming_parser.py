#!/usr/bin/env python3
"""Constant‑memory streaming JSON parser."""
import ijson, logging, pathlib
from typing import Iterator, Any

logger = logging.getLogger(__name__)

class StreamingJSONParser:
    def auto_detect_json_structure(self, path: str) -> str:
        """Return 'array', 'object', or 'unknown'."""
        try:
            with open(path, 'rb') as f:
                while True:
                    ch = f.read(1)
                    if not ch:
                        return 'unknown'
                    if not ch.isspace():
                        if ch == b'[':
                            return 'array'
                        if ch == b'{':
                            return 'object'
                        return 'unknown'
        except Exception as e:
            logger.error(f"detect structure failed: {e}")
            return 'unknown'

    def iter_records(self, path: str, pointer: str='item') -> Iterator[Any]:
        """Yield parsed objects without loading full file."""
        try:
            with open(path, 'rb') as f:
                for obj in ijson.items(f, pointer):
                    yield obj
        except Exception as e:
            logger.error(f"stream parse failed: {e}")
            raise
