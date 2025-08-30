import logging
import psutil

import pynvml

logger = logging.getLogger(__name__)


class GPUMemoryGuard:
    """Monitor GPU memory usage and prevent out-of-memory errors."""

    def __init__(self, threshold_percent=80):
        self.threshold_percent = threshold_percent
        self.gpu_available = False

        try:
            pynvml.nvmlInit()
            self.device_count = pynvml.nvmlDeviceGetCount()
            self.gpu_available = self.device_count > 0
            if self.gpu_available:
                logger.info(f"GPU memory guard initialized. Found {self.device_count} GPU(s)")
        except Exception as e:
            logger.warning(f"GPU initialization failed: {e}. GPU monitoring disabled.")
            self.gpu_available = False

    def get_memory_usage(self, device_id=0):
        """Get current GPU memory usage percentage for specified device."""
        if not self.gpu_available or device_id >= self.device_count:
            return 0.0

        try:
            handle = pynvml.nvmlDeviceGetHandleByIndex(device_id)
            mem_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
            usage_percent = (mem_info.used / mem_info.total) * 100
            return usage_percent
        except pynvml.NVMLError as e:
            logger.error(f"Error reading GPU memory: {e}")
            return 100.0  # Assume full if we can't read

    def should_use_gpu(self, device_id=0):
        """Check if GPU should be used based on current memory usage."""
        if not self.gpu_available:
            return False

        usage = self.get_memory_usage(device_id)
        safe_to_use = usage < self.threshold_percent

        if not safe_to_use:
            logger.warning(
                f"GPU memory usage ({usage:.1f}%) exceeds threshold ({self.threshold_percent}%). Falling back to CPU."
            )

        return safe_to_use

    def __del__(self):
        """Cleanup NVML on deletion."""
        if self.gpu_available:
            try:
                pynvml.nvmlShutdown()
            except Exception:
                pass


class MemoryGuard:
    """
    System memory guard for pre-flight allocation checks.
    Prevents OOM by checking available memory before large allocations.
    """
    
    def __init__(self, max_memory_mb: int = 100):
        """
        Initialize memory guard.
        
        Args:
            max_memory_mb: Maximum memory allocation limit in MB
        """
        self.limit = max_memory_mb * 1024 * 1024
        self._warning_threshold = 0.8  # Warn at 80% of limit
        
    def check_allocation(self, size: int) -> bool:
        """
        Pre-flight check before large allocations.
        
        Args:
            size: Size of intended allocation in bytes
            
        Returns:
            bool: True if allocation is safe, False otherwise
        """
        try:
            memory = psutil.virtual_memory()
            available = memory.available
            
            # Check against system memory
            if size > available * 0.8:
                logger.warning(
                    f"Allocation of {size / 1024 / 1024:.1f}MB would exceed "
                    f"80% of available memory ({available / 1024 / 1024:.1f}MB)"
                )
                return False
            
            # Check against configured limit
            if size > self.limit:
                logger.warning(
                    f"Allocation of {size / 1024 / 1024:.1f}MB exceeds "
                    f"configured limit of {self.limit / 1024 / 1024:.1f}MB"
                )
                return False
            
            # Warn if approaching limit
            if size > self.limit * self._warning_threshold:
                logger.info(
                    f"Allocation of {size / 1024 / 1024:.1f}MB approaching "
                    f"limit ({self.limit / 1024 / 1024:.1f}MB)"
                )
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking memory allocation: {e}")
            # Be conservative on error
            return False
    
    def get_memory_info(self) -> dict:
        """
        Get current memory statistics.
        
        Returns:
            dict: Memory statistics including total, available, used, and percent
        """
        try:
            memory = psutil.virtual_memory()
            return {
                'total_mb': memory.total / 1024 / 1024,
                'available_mb': memory.available / 1024 / 1024,
                'used_mb': memory.used / 1024 / 1024,
                'percent': memory.percent,
                'limit_mb': self.limit / 1024 / 1024
            }
        except Exception as e:
            logger.error(f"Error getting memory info: {e}")
            return {}
    
    def estimate_json_memory(self, json_size_bytes: int) -> int:
        """
        Estimate memory needed for JSON processing.
        
        Rule of thumb: JSON parsing typically needs 2-4x the file size
        in memory due to object overhead and intermediate structures.
        
        Args:
            json_size_bytes: Size of JSON file in bytes
            
        Returns:
            int: Estimated memory requirement in bytes
        """
        # Conservative 3x multiplier for safety
        return json_size_bytes * 3
    
    def can_process_json(self, json_size_bytes: int) -> bool:
        """
        Check if JSON file can be safely processed.
        
        Args:
            json_size_bytes: Size of JSON file in bytes
            
        Returns:
            bool: True if file can be processed safely
        """
        estimated = self.estimate_json_memory(json_size_bytes)
        return self.check_allocation(estimated)
