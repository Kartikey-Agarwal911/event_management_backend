from functools import wraps
from typing import Any, Callable, Optional, List
from datetime import datetime, timedelta
import json
from fastapi import HTTPException
from sqlalchemy.orm import Session
from ..models import Event, EventVersion, Changelog
from ..utils.logger import logger

class SimpleCache:
    def __init__(self):
        self._cache = {}
        self._expiry = {}

    def set(self, key: str, value: Any, expire: int = 300) -> bool:
        try:
            self._cache[key] = value
            self._expiry[key] = datetime.now() + timedelta(seconds=expire)
            return True
        except Exception as e:
            logger.error(f"Cache set error: {str(e)}")
            return False

    def get(self, key: str) -> Optional[Any]:
        try:
            if key in self._cache:
                if datetime.now() > self._expiry.get(key, datetime.now()):
                    del self._cache[key]
                    del self._expiry[key]
                    return None
                return self._cache[key]
            return None
        except Exception as e:
            logger.error(f"Cache get error: {str(e)}")
            return None

    def delete(self, key: str) -> bool:
        try:
            if key in self._cache:
                del self._cache[key]
                del self._expiry[key]
            return True
        except Exception as e:
            logger.error(f"Cache delete error: {str(e)}")
            return False

    def clear_pattern(self, pattern: str) -> bool:
        try:
            keys_to_delete = [k for k in self._cache.keys() if pattern in k]
            for key in keys_to_delete:
                del self._cache[key]
                del self._expiry[key]
            return True
        except Exception as e:
            logger.error(f"Cache clear pattern error: {str(e)}")
            return False

# Create a singleton instance
cache = SimpleCache()


def cache_event(func: Callable) -> Callable:
    @wraps(func)
    async def wrapper(*args, **kwargs):
        event_id = kwargs.get('event_id')
        if not event_id:
            return await func(*args, **kwargs)
        
        cache_key = f"event:{event_id}"
        cached_event = cache.get(cache_key)
        
        if cached_event:
            return cached_event
        
        result = await func(*args, **kwargs)
        cache.set(cache_key, result)
        return result
    
    return wrapper


def cache_event_list(func: Callable) -> Callable:
    @wraps(func)
    async def wrapper(*args, **kwargs):
        user_id = kwargs.get('current_user').id
        cache_key = f"events:user:{user_id}"
        cached_events = cache.get(cache_key)
        
        if cached_events:
            return cached_events
        
        result = await func(*args, **kwargs)
        cache.set(cache_key, result)
        return result
    
    return wrapper


def invalidate_event_cache(event_id: int):
    cache.delete(f"event:{event_id}")


def invalidate_user_events_cache(user_id: int):
    cache.delete(f"events:user:{user_id}")


def get_cached_event_versions(db: Session, event_id: int) -> List[EventVersion]:
    cache_key = f"event_versions:{event_id}"
    cached_versions = cache.get(cache_key)
    
    if cached_versions:
        return cached_versions
    
    versions = db.query(EventVersion).filter(
        EventVersion.event_id == event_id
    ).order_by(EventVersion.version_number).all()
    
    cache.set(cache_key, versions)
    return versions


def get_cached_changelog(db: Session, event_id: int) -> List[Changelog]:
    cache_key = f"changelog:{event_id}"
    cached_changelog = cache.get(cache_key)
    
    if cached_changelog:
        return cached_changelog
    
    changelog = db.query(Changelog).filter(
        Changelog.event_id == event_id
    ).order_by(Changelog.created_at).all()
    
    cache.set(cache_key, changelog)
    return changelog 