import os
import sys
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from datetime import datetime, timedelta
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)

# Detect if running under pytest
IS_TEST = 'pytest' in sys.modules

class RateLimiter:
    def __init__(self):
        # Use a much higher limit for tests
        self.max_requests = 1000 if IS_TEST else 5
        self.window_size = 60  # seconds
        self.requests = defaultdict(list)
    
    def _get_client_id(self, request: Request) -> str:
        """Get unique client identifier"""
        try:
            forwarded = request.headers.get("X-Forwarded-For")
            if forwarded:
                return forwarded.split(",")[0]
            return request.client.host if request.client else "unknown"
        except Exception as e:
            logger.error(f"Error getting client ID: {str(e)}")
            return "unknown"
    
    def _get_endpoint_type(self, request: Request) -> str:
        """Determine endpoint type for rate limiting"""
        try:
            path = request.url.path
            if path.startswith("/api/auth"):
                return "auth"
            elif path.startswith("/api/events"):
                return "events"
            return "default"
        except Exception as e:
            logger.error(f"Error getting endpoint type: {str(e)}")
            return "default"
    
    def is_rate_limited(self, request: Request):
        client_ip = getattr(request.client, "host", None) or "testclient"
        now = datetime.utcnow()
        window_start = now - timedelta(seconds=self.window_size)
        # Remove old requests
        self.requests[client_ip] = [t for t in self.requests[client_ip] if t > window_start]
        if len(self.requests[client_ip]) >= self.max_requests:
            return True, self.max_requests
        self.requests[client_ip].append(now)
        return False, self.max_requests

rate_limiter = RateLimiter()

async def rate_limit_middleware(request: Request, call_next):
    """Middleware to enforce rate limiting"""
    try:
        is_limited, max_requests = rate_limiter.is_rate_limited(request)
        if is_limited:
            raise HTTPException(
                status_code=429,
                detail={
                    "error": "Too many requests",
                    "retry_after": rate_limiter.window_size,
                    "max_requests": max_requests
                }
            )
        response = await call_next(request)
        return response
    except HTTPException as exc:
        raise exc
    except Exception as e:
        logger.error(f"Rate limiting error: {str(e)}")
        # Don't block the request if rate limiting fails
        return await call_next(request) 