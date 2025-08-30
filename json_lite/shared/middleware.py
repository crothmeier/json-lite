"""
Middleware pipeline for cross-cutting concerns in JSON processing.
Provides composable middleware for streaming operations.
"""
from typing import AsyncIterator, Callable, Optional, Any, List
from dataclasses import dataclass
import asyncio
import time
from functools import wraps
import logging

logger = logging.getLogger(__name__)


@dataclass
class Context:
    """Middleware context passed through the pipeline."""
    data: Any
    metadata: dict
    timestamp: float
    
    def __init__(self, data: Any, **kwargs):
        self.data = data
        self.metadata = kwargs
        self.timestamp = time.time()


class Middleware:
    """Base middleware class for pipeline components."""
    
    def __init__(self, next_handler: Optional[Callable] = None):
        self.next = next_handler
    
    async def __call__(self, ctx: Context) -> Context:
        """Process context through middleware."""
        ctx = await self.process(ctx)
        if self.next:
            ctx = await self.next(ctx)
        return ctx
    
    async def process(self, ctx: Context) -> Context:
        """Override in subclasses to implement middleware logic."""
        return ctx


class RateLimiter(Middleware):
    """Rate limiting middleware for backpressure control."""
    
    def __init__(self, max_per_second: int = 1000, **kwargs):
        super().__init__(**kwargs)
        self.max_per_second = max_per_second
        self.window = []
        self.lock = asyncio.Lock()
    
    async def process(self, ctx: Context) -> Context:
        async with self.lock:
            now = time.time()
            # Clean old entries
            self.window = [t for t in self.window if now - t < 1.0]
            
            if len(self.window) >= self.max_per_second:
                # Calculate wait time
                oldest = self.window[0]
                wait_time = 1.0 - (now - oldest)
                if wait_time > 0:
                    await asyncio.sleep(wait_time)
                    now = time.time()
            
            self.window.append(now)
            ctx.metadata['rate_limited_at'] = now
        
        return ctx


class MetricsCollector(Middleware):
    """Collect processing metrics for monitoring."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.metrics = {
            'processed': 0,
            'errors': 0,
            'total_bytes': 0,
            'avg_latency_ms': 0.0
        }
        self.latencies = []
    
    async def process(self, ctx: Context) -> Context:
        start = time.time()
        
        try:
            if hasattr(ctx.data, '__len__'):
                self.metrics['total_bytes'] += len(ctx.data)
            self.metrics['processed'] += 1
            
        except Exception as e:
            self.metrics['errors'] += 1
            logger.error(f"Metrics collection error: {e}")
        
        finally:
            latency = (time.time() - start) * 1000
            self.latencies.append(latency)
            if len(self.latencies) > 100:
                self.latencies.pop(0)
            self.metrics['avg_latency_ms'] = sum(self.latencies) / len(self.latencies)
            ctx.metadata['metrics'] = self.metrics.copy()
        
        return ctx


class ValidationMiddleware(Middleware):
    """Validate data against schemas or business rules."""
    
    def __init__(self, validators: List[Callable] = None, **kwargs):
        super().__init__(**kwargs)
        self.validators = validators or []
    
    async def process(self, ctx: Context) -> Context:
        for validator in self.validators:
            try:
                if not await self._run_validator(validator, ctx.data):
                    ctx.metadata['validation_failed'] = True
                    ctx.metadata['validator'] = validator.__name__
                    logger.warning(f"Validation failed: {validator.__name__}")
                    break
            except Exception as e:
                logger.error(f"Validator {validator.__name__} error: {e}")
                ctx.metadata['validation_error'] = str(e)
        
        return ctx
    
    async def _run_validator(self, validator: Callable, data: Any) -> bool:
        if asyncio.iscoroutinefunction(validator):
            return await validator(data)
        return validator(data)


class BackpressureController(Middleware):
    """Control backpressure based on memory and queue depth."""
    
    def __init__(self, max_queue_size: int = 1000, max_memory_mb: int = 100, **kwargs):
        super().__init__(**kwargs)
        self.max_queue_size = max_queue_size
        self.max_memory_mb = max_memory_mb
        self.queue_size = 0
        self.lock = asyncio.Lock()
    
    async def process(self, ctx: Context) -> Context:
        from .gpu_guard import MemoryGuard
        
        guard = MemoryGuard(self.max_memory_mb)
        
        async with self.lock:
            # Check memory before processing
            estimated_size = len(str(ctx.data)) if ctx.data else 0
            
            if not guard.check_allocation(estimated_size):
                ctx.metadata['backpressure'] = 'memory_limit'
                await asyncio.sleep(0.1)  # Brief pause
            
            if self.queue_size >= self.max_queue_size:
                ctx.metadata['backpressure'] = 'queue_limit'
                await asyncio.sleep(0.05)
            
            self.queue_size += 1
            
        try:
            return ctx
        finally:
            async with self.lock:
                self.queue_size -= 1


class Pipeline:
    """Compose and execute middleware pipeline."""
    
    def __init__(self):
        self.middlewares: List[Middleware] = []
    
    def use(self, middleware: Middleware) -> 'Pipeline':
        """Add middleware to pipeline."""
        self.middlewares.append(middleware)
        return self
    
    def build(self) -> Callable:
        """Build the complete pipeline."""
        if not self.middlewares:
            return lambda ctx: ctx
        
        # Chain middlewares in reverse order
        handler = None
        for middleware in reversed(self.middlewares):
            middleware.next = handler
            handler = middleware
        
        return handler
    
    async def execute(self, data: Any, **metadata) -> Context:
        """Execute pipeline with data."""
        ctx = Context(data, **metadata)
        handler = self.build()
        
        if handler:
            if asyncio.iscoroutinefunction(handler):
                return await handler(ctx)
            return handler(ctx)
        
        return ctx


# Convenience decorators
def with_rate_limit(max_per_second: int = 1000):
    """Decorator to add rate limiting to async functions."""
    def decorator(func):
        limiter = RateLimiter(max_per_second)
        
        @wraps(func)
        async def wrapper(*args, **kwargs):
            ctx = Context(None, function=func.__name__)
            await limiter.process(ctx)
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator


def with_metrics():
    """Decorator to collect metrics for async functions."""
    def decorator(func):
        collector = MetricsCollector()
        
        @wraps(func)
        async def wrapper(*args, **kwargs):
            ctx = Context(None, function=func.__name__)
            await collector.process(ctx)
            result = await func(*args, **kwargs)
            logger.info(f"Metrics for {func.__name__}: {collector.metrics}")
            return result
        
        return wrapper
    return decorator


async def create_streaming_pipeline(
    rate_limit: Optional[int] = None,
    collect_metrics: bool = True,
    enable_backpressure: bool = True,
    validators: Optional[List[Callable]] = None
) -> Pipeline:
    """
    Create a pre-configured streaming pipeline.
    
    Args:
        rate_limit: Max operations per second
        collect_metrics: Enable metrics collection
        enable_backpressure: Enable backpressure control
        validators: List of validation functions
    
    Returns:
        Configured Pipeline instance
    """
    pipeline = Pipeline()
    
    if collect_metrics:
        pipeline.use(MetricsCollector())
    
    if rate_limit:
        pipeline.use(RateLimiter(rate_limit))
    
    if enable_backpressure:
        pipeline.use(BackpressureController())
    
    if validators:
        pipeline.use(ValidationMiddleware(validators))
    
    return pipeline