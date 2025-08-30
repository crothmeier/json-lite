"""
Compatibility shim for legacy imports.
This module maintains backward compatibility for code using 'from shared import ...'
"""

import warnings
import sys
from pathlib import Path

# Add json_lite to path if not already there
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Show deprecation warning
warnings.warn(
    "Importing from 'shared' is deprecated. Use 'json_lite.shared' instead.",
    DeprecationWarning,
    stacklevel=2
)

# Re-export everything from the new location
from json_lite.shared import *
from json_lite.shared import streaming_parser
from json_lite.shared import gpu_guard
from json_lite.shared import middleware

# Ensure all modules are available
__all__ = ['streaming_parser', 'gpu_guard', 'middleware']