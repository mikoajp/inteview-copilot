"""Rate limiting configuration for Interview Copilot API."""

from functools import wraps
from fastapi import Request
from config import config

# Initialize rate limiter
limiter = None

if config.rate_limit_enabled:
    from slowapi import Limiter
    from slowapi.util import get_remote_address

    if config.rate_limit_storage == "redis":
        limiter = Limiter(
            key_func=get_remote_address,
            storage_uri=config.redis_url
        )
    else:
        limiter = Limiter(key_func=get_remote_address)


def rate_limit(limit_string: str = None):
    """
    Rate limiting decorator that can be conditionally applied.

    Args:
        limit_string: Rate limit string (e.g., "30/minute")
    """
    if limit_string is None:
        limit_string = f"{config.rate_limit_per_minute}/minute"

    def decorator(func):
        if config.rate_limit_enabled and limiter:
            return limiter.limit(limit_string)(func)
        return func
    return decorator


def get_limiter():
    """Get the rate limiter instance."""
    return limiter
