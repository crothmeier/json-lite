"""
Shared utilities for json-lite project.

This package contains reusable components used across different json-lite tools:
- streaming_parser: Memory-efficient JSON parsing with ijson
- gpu_guard: GPU memory monitoring and guards
- middleware: HTTP middleware components
"""

from .streaming_parser import StreamingJSONParser
from .gpu_guard import GPUMemoryGuard

__all__ = ['StreamingJSONParser', 'GPUMemoryGuard']
__version__ = '1.1.0'
