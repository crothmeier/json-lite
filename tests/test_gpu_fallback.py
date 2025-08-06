#!/usr/bin/env python3
"""Tests for GPU memory management and fallback mechanisms."""

import pytest
import sys
import pathlib
from unittest.mock import patch, MagicMock, PropertyMock

sys.path.append(str(pathlib.Path(__file__).parent.parent))


class TestGPUMemoryGuard:
    """Test suite for GPUMemoryGuard functionality."""
    
    @pytest.fixture
    def mock_pynvml(self):
        """Mock pynvml module for testing."""
        with patch('shared.gpu_guard.pynvml') as mock:
            # Setup default mock behaviors
            mock.nvmlInit.return_value = None
            mock.nvmlShutdown.return_value = None
            mock.nvmlDeviceGetCount.return_value = 1
            mock.NVMLError = Exception  # Create a mock exception class
            
            # Mock memory info
            mem_info = MagicMock()
            mem_info.total = 8 * 1024 * 1024 * 1024  # 8GB
            mem_info.used = 2 * 1024 * 1024 * 1024   # 2GB (25% usage)
            
            handle = MagicMock()
            mock.nvmlDeviceGetHandleByIndex.return_value = handle
            mock.nvmlDeviceGetMemoryInfo.return_value = mem_info
            
            yield mock
    
    def test_initialization_with_gpu(self, mock_pynvml):
        """Test GPUMemoryGuard initialization with GPU available."""
        from shared.gpu_guard import GPUMemoryGuard
        
        guard = GPUMemoryGuard(threshold_percent=80)
        
        assert guard.threshold_percent == 80
        assert guard.gpu_available is True
        assert guard.device_count == 1
        mock_pynvml.nvmlInit.assert_called_once()
    
    def test_initialization_without_gpu(self):
        """Test GPUMemoryGuard initialization when pynvml is not available."""
        with patch('shared.gpu_guard.pynvml.nvmlInit', side_effect=Exception("No GPU")):
            from shared.gpu_guard import GPUMemoryGuard
            
            guard = GPUMemoryGuard(threshold_percent=80)
            
            assert guard.threshold_percent == 80
            assert guard.gpu_available is False
    
    def test_get_memory_usage_normal(self, mock_pynvml):
        """Test getting GPU memory usage under normal conditions."""
        from shared.gpu_guard import GPUMemoryGuard
        
        # Set 25% memory usage
        mem_info = MagicMock()
        mem_info.total = 8 * 1024 * 1024 * 1024  # 8GB
        mem_info.used = 2 * 1024 * 1024 * 1024   # 2GB
        mock_pynvml.nvmlDeviceGetMemoryInfo.return_value = mem_info
        
        guard = GPUMemoryGuard()
        usage = guard.get_memory_usage(device_id=0)
        
        assert usage == 25.0
    
    def test_get_memory_usage_high(self, mock_pynvml):
        """Test getting GPU memory usage when it's high."""
        from shared.gpu_guard import GPUMemoryGuard
        
        # Set 85% memory usage
        mem_info = MagicMock()
        mem_info.total = 8 * 1024 * 1024 * 1024  # 8GB
        mem_info.used = int(6.8 * 1024 * 1024 * 1024)  # 6.8GB (85%)
        mock_pynvml.nvmlDeviceGetMemoryInfo.return_value = mem_info
        
        guard = GPUMemoryGuard()
        usage = guard.get_memory_usage(device_id=0)
        
        assert usage == 85.0
    
    def test_get_memory_usage_no_gpu(self):
        """Test get_memory_usage when no GPU is available."""
        with patch('shared.gpu_guard.pynvml.nvmlInit', side_effect=Exception("No GPU")):
            from shared.gpu_guard import GPUMemoryGuard
            
            guard = GPUMemoryGuard()
            usage = guard.get_memory_usage(device_id=0)
            
            assert usage == 0.0
    
    def test_get_memory_usage_invalid_device(self, mock_pynvml):
        """Test get_memory_usage with invalid device ID."""
        from shared.gpu_guard import GPUMemoryGuard
        
        guard = GPUMemoryGuard()
        usage = guard.get_memory_usage(device_id=5)  # Invalid device ID
        
        assert usage == 0.0
    
    def test_get_memory_usage_nvml_error(self, mock_pynvml):
        """Test get_memory_usage when NVML raises an error."""
        from shared.gpu_guard import GPUMemoryGuard
        
        mock_pynvml.nvmlDeviceGetMemoryInfo.side_effect = Exception("NVML Error")
        
        guard = GPUMemoryGuard()
        usage = guard.get_memory_usage(device_id=0)
        
        # Should return 100% on error (safe fallback)
        assert usage == 100.0
    
    def test_should_use_gpu_below_threshold(self, mock_pynvml):
        """Test should_use_gpu returns True when memory is below threshold."""
        from shared.gpu_guard import GPUMemoryGuard
        
        # Set 50% memory usage
        mem_info = MagicMock()
        mem_info.total = 8 * 1024 * 1024 * 1024
        mem_info.used = 4 * 1024 * 1024 * 1024
        mock_pynvml.nvmlDeviceGetMemoryInfo.return_value = mem_info
        
        guard = GPUMemoryGuard(threshold_percent=80)
        result = guard.should_use_gpu(device_id=0)
        
        assert result is True
    
    def test_should_use_gpu_above_threshold(self, mock_pynvml):
        """Test should_use_gpu returns False when memory exceeds threshold."""
        from shared.gpu_guard import GPUMemoryGuard
        
        # Set 85% memory usage
        mem_info = MagicMock()
        mem_info.total = 8 * 1024 * 1024 * 1024
        mem_info.used = int(6.8 * 1024 * 1024 * 1024)
        mock_pynvml.nvmlDeviceGetMemoryInfo.return_value = mem_info
        
        guard = GPUMemoryGuard(threshold_percent=80)
        result = guard.should_use_gpu(device_id=0)
        
        assert result is False
    
    def test_should_use_gpu_exactly_at_threshold(self, mock_pynvml):
        """Test should_use_gpu behavior at exactly the threshold."""
        from shared.gpu_guard import GPUMemoryGuard
        
        # Set exactly 80% memory usage
        mem_info = MagicMock()
        mem_info.total = 10 * 1024 * 1024 * 1024
        mem_info.used = 8 * 1024 * 1024 * 1024
        mock_pynvml.nvmlDeviceGetMemoryInfo.return_value = mem_info
        
        guard = GPUMemoryGuard(threshold_percent=80)
        result = guard.should_use_gpu(device_id=0)
        
        assert result is False  # Should not use GPU at exactly threshold
    
    def test_should_use_gpu_no_gpu_available(self):
        """Test should_use_gpu when no GPU is available."""
        with patch('shared.gpu_guard.pynvml.nvmlInit', side_effect=Exception("No GPU")):
            from shared.gpu_guard import GPUMemoryGuard
            
            guard = GPUMemoryGuard()
            result = guard.should_use_gpu(device_id=0)
            
            assert result is False
    
    def test_hysteresis_behavior(self, mock_pynvml):
        """Test hysteresis prevents flapping between GPU/CPU modes."""
        from shared.gpu_guard import GPUMemoryGuard
        
        guard = GPUMemoryGuard(threshold_percent=80)
        
        # Simulate memory going above threshold (85%)
        mem_info = MagicMock()
        mem_info.total = 8 * 1024 * 1024 * 1024
        mem_info.used = int(6.8 * 1024 * 1024 * 1024)
        mock_pynvml.nvmlDeviceGetMemoryInfo.return_value = mem_info
        
        assert guard.should_use_gpu() is False
        
        # Memory drops to 70% (between 60% and 80%)
        mem_info.used = int(5.6 * 1024 * 1024 * 1024)
        mock_pynvml.nvmlDeviceGetMemoryInfo.return_value = mem_info
        
        # Should still return False due to hysteresis
        # (would need to drop below 60% to re-enable)
        assert guard.should_use_gpu() is False
        
        # Memory drops to 55% (below 60% hysteresis point)
        mem_info.used = int(4.4 * 1024 * 1024 * 1024)
        mock_pynvml.nvmlDeviceGetMemoryInfo.return_value = mem_info
        
        # Now should return True again
        assert guard.should_use_gpu() is True
    
    def test_multiple_gpus(self, mock_pynvml):
        """Test handling multiple GPU devices."""
        from shared.gpu_guard import GPUMemoryGuard
        
        mock_pynvml.nvmlDeviceGetCount.return_value = 3
        
        guard = GPUMemoryGuard()
        assert guard.device_count == 3
        
        # Setup different memory usage for each GPU
        def get_memory_info(handle):
            # Mock different usage based on handle
            mem_info = MagicMock()
            mem_info.total = 8 * 1024 * 1024 * 1024
            if handle == 0:
                mem_info.used = 2 * 1024 * 1024 * 1024  # 25%
            elif handle == 1:
                mem_info.used = 7 * 1024 * 1024 * 1024  # 87.5%
            else:
                mem_info.used = 4 * 1024 * 1024 * 1024  # 50%
            return mem_info
        
        mock_pynvml.nvmlDeviceGetHandleByIndex.side_effect = lambda x: x
        mock_pynvml.nvmlDeviceGetMemoryInfo.side_effect = get_memory_info
        
        # Test each GPU
        assert guard.should_use_gpu(device_id=0) is True   # 25% < 80%
        assert guard.should_use_gpu(device_id=1) is False  # 87.5% > 80%
        assert guard.should_use_gpu(device_id=2) is True   # 50% < 80%
    
    def test_custom_threshold(self, mock_pynvml):
        """Test custom threshold percentage settings."""
        from shared.gpu_guard import GPUMemoryGuard
        
        # Set 50% memory usage
        mem_info = MagicMock()
        mem_info.total = 8 * 1024 * 1024 * 1024
        mem_info.used = 4 * 1024 * 1024 * 1024
        mock_pynvml.nvmlDeviceGetMemoryInfo.return_value = mem_info
        
        # Test with 40% threshold
        guard = GPUMemoryGuard(threshold_percent=40)
        assert guard.should_use_gpu() is False  # 50% > 40%
        
        # Test with 60% threshold
        guard = GPUMemoryGuard(threshold_percent=60)
        assert guard.should_use_gpu() is True   # 50% < 60%
    
    def test_cleanup_on_deletion(self, mock_pynvml):
        """Test that NVML is properly shut down on object deletion."""
        from shared.gpu_guard import GPUMemoryGuard
        
        guard = GPUMemoryGuard()
        del guard
        
        mock_pynvml.nvmlShutdown.assert_called_once()
    
    def test_cleanup_on_deletion_no_gpu(self):
        """Test cleanup when no GPU was available."""
        with patch('shared.gpu_guard.pynvml.nvmlInit', side_effect=Exception("No GPU")):
            from shared.gpu_guard import GPUMemoryGuard
            
            guard = GPUMemoryGuard()
            # Should not raise exception
            del guard
    
    def test_concurrent_guards(self, mock_pynvml):
        """Test multiple GPUMemoryGuard instances can coexist."""
        from shared.gpu_guard import GPUMemoryGuard
        
        guard1 = GPUMemoryGuard(threshold_percent=70)
        guard2 = GPUMemoryGuard(threshold_percent=90)
        
        # Set 80% memory usage
        mem_info = MagicMock()
        mem_info.total = 10 * 1024 * 1024 * 1024
        mem_info.used = 8 * 1024 * 1024 * 1024
        mock_pynvml.nvmlDeviceGetMemoryInfo.return_value = mem_info
        
        assert guard1.should_use_gpu() is False  # 80% > 70%
        assert guard2.should_use_gpu() is True   # 80% < 90%
    
    @pytest.mark.parametrize("usage_percent,threshold,expected", [
        (0, 80, True),
        (25, 80, True),
        (50, 80, True),
        (79, 80, True),
        (80, 80, False),
        (81, 80, False),
        (90, 80, False),
        (100, 80, False),
    ])
    def test_threshold_boundaries(self, mock_pynvml, usage_percent, threshold, expected):
        """Test GPU usage decision at various threshold boundaries."""
        from shared.gpu_guard import GPUMemoryGuard
        
        mem_info = MagicMock()
        mem_info.total = 100 * 1024 * 1024  # 100MB for easy percentage calculation
        mem_info.used = usage_percent * 1024 * 1024  # Usage in MB
        mock_pynvml.nvmlDeviceGetMemoryInfo.return_value = mem_info
        
        guard = GPUMemoryGuard(threshold_percent=threshold)
        assert guard.should_use_gpu() is expected