"""Prometheus metrics for Interview Copilot API."""

from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from fastapi import Response
import time
from functools import wraps
from logger import logger

# Define metrics
request_count = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

request_duration = Histogram(
    'http_request_duration_seconds',
    'HTTP request latency',
    ['method', 'endpoint']
)

transcription_count = Counter(
    'transcriptions_total',
    'Total transcriptions performed'
)

transcription_duration = Histogram(
    'transcription_duration_seconds',
    'Transcription processing time'
)

generation_count = Counter(
    'generations_total',
    'Total answer generations'
)

generation_duration = Histogram(
    'generation_duration_seconds',
    'Answer generation processing time'
)

question_detected_count = Counter(
    'questions_detected_total',
    'Total questions detected'
)

active_sessions = Gauge(
    'active_sessions',
    'Number of active sessions'
)

error_count = Counter(
    'errors_total',
    'Total errors',
    ['error_type', 'endpoint']
)


def track_time(metric_histogram):
    """Decorator to track execution time."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                return result
            finally:
                duration = time.time() - start_time
                metric_histogram.observe(duration)
                logger.debug(f"{func.__name__} took {duration:.3f}s", extra={
                    'function': func.__name__,
                    'duration': duration
                })
        return wrapper
    return decorator


async def get_metrics():
    """Generate Prometheus metrics."""
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )
