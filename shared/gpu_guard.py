import logging
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
        except pynvml.NVMLError:
            logger.warning("NVIDIA Management Library not available. GPU monitoring disabled.")
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
            logger.warning(f"GPU memory usage ({usage:.1f}%) exceeds threshold ({self.threshold_percent}%). Falling back to CPU.")
        
        return safe_to_use
    
    def __del__(self):
        """Cleanup NVML on deletion."""
        if self.gpu_available:
            try:
                pynvml.nvmlShutdown()
            except:
                pass