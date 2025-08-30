"""
Backward compatibility shim for legacy imports.
TO BE REMOVED after migration completion.
"""
import sys
import warnings

# Issue deprecation warning
warnings.warn(
    "Importing from 'shared' is deprecated. Use 'json_lite.shared' instead.",
    DeprecationWarning,
    stacklevel=2
)

# Import new package modules
from json_lite.shared import streaming_parser as _sp
from json_lite.shared import gpu_guard as _gg

# Re-export all public symbols
from json_lite.shared.streaming_parser import *
from json_lite.shared.gpu_guard import *

# CRITICAL: Register modules for dotted imports
sys.modules['shared.streaming_parser'] = _sp
sys.modules['shared.gpu_guard'] = _gg