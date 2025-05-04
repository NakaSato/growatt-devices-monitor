import functools
import hashlib
import json
from typing import Any, Callable, Dict, Optional, Union, List, Tuple, cast

from flask import request, current_app

def make_cache_key(*args, **kwargs) -> str:
    """
    Create a cache key based on the request path and arguments.
    
    Args:
        *args: Variable arguments to include in cache key
        **kwargs: Keyword arguments to include in cache key
        
    Returns:
        str: A unique cache key for the request
    """
    # Combine request path, query args, and function args
    key_parts = [request.path]
    
    # Add any custom args/kwargs
    if args:
        key_parts.append(str(args))
    if kwargs:
        key_parts.append(str(sorted(kwargs.items())))
    
    # Add query params if present
    if request.args:
        # Sort query params for consistency
        key_parts.append(str(sorted(request.args.items())))
    
    # Add form data for POST requests
    if request.form:
        key_parts.append(str(sorted(request.form.items())))
    
    # Generate the key using SHA-256
    key_string = '|'.join(key_parts)
    return hashlib.sha256(key_string.encode('utf-8')).hexdigest()

def cached_route(timeout: Optional[int] = None, key_prefix: str = 'route_'):
    """
    A decorator for caching Flask routes.
    
    Args:
        timeout: Cache timeout in seconds, or None for default
        key_prefix: Prefix for the cache key
        
    Returns:
        Callable: The decorated function
    """
    def decorator(f: Callable) -> Callable:
        @functools.wraps(f)
        def decorated_function(*args, **kwargs):
            # Always bypass cache if requested via headers
            force_refresh = request.headers.get('Cache-Control') == 'no-cache'
            if force_refresh:
                current_app.logger.debug(f"Bypassing cache for {request.path} due to Cache-Control header")
                return f(*args, **kwargs)
            
            # Get the cache instance
            cache = current_app.extensions.get('cache')
            if not cache:
                current_app.logger.warning("Cache extension not found, skipping cache")
                return f(*args, **kwargs)
            
            # Generate a cache key
            cache_key = f"{key_prefix}{make_cache_key(*args, **kwargs)}"
            
            # Try to get from cache
            cached_result = cache.get(cache_key) if hasattr(cache, 'get') else None
            if cached_result is not None:
                current_app.logger.debug(f"Cache hit for {request.path} ({cache_key})")
                return cached_result
            
            # Run the function and cache the result
            result = f(*args, **kwargs)
            
            # Only cache if result is cacheable (tuple with response, status code)
            if isinstance(result, tuple) and len(result) == 2:
                cache_ttl = timeout or current_app.config.get('CACHE_DEFAULT_TIMEOUT', 300)
                
                # Check if cache object has the set method before calling it
                if hasattr(cache, 'set'):
                    cache.set(cache_key, result, timeout=cache_ttl)
                    current_app.logger.debug(f"Cached result for {request.path} ({cache_key}) with TTL {cache_ttl}s")
                elif isinstance(cache, dict):
                    # Fallback for dict-like caches
                    cache[cache_key] = result
                    current_app.logger.debug(f"Cached result for {request.path} ({cache_key}) using dictionary storage")
            
            return result
        return decorated_function
    return decorator

def invalidate_cache_pattern(pattern: str) -> int:
    """
    Invalidate cache keys matching a pattern.
    
    Args:
        pattern: Pattern to match cache keys
        
    Returns:
        int: Number of keys deleted
    """
    # Get the cache instance
    cache = current_app.extensions.get('cache')
    if not cache:
        current_app.logger.warning("Cache extension not found, can't invalidate cache")
        return 0
    
    # This only works for Redis cache backend
    if hasattr(cache, '_client') and hasattr(cache._client, 'keys') and hasattr(cache._client, 'delete'):
        try:
            # Get all keys matching the pattern
            keys = cache._client.keys(pattern)
            if not keys:
                return 0
            
            # Delete the keys
            num_deleted = len(keys)
            cache._client.delete(*keys)
            current_app.logger.info(f"Invalidated {num_deleted} cache keys matching '{pattern}'")
            return num_deleted
        except Exception as e:
            current_app.logger.error(f"Error invalidating cache keys: {e}")
            return 0
    else:
        current_app.logger.warning("Cache backend doesn't support pattern invalidation")
        return 0