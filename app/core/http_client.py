"""
HTTP Client utility functions
Provides robust async HTTP client handling to avoid event loop issues
"""

import httpx
import asyncio
import logging
from typing import Optional, Dict, Any, Union
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)

@asynccontextmanager
async def get_http_client(timeout: float = 30.0):
    """
    Context manager for httpx AsyncClient that properly manages the client lifecycle
    and prevents "Event loop is closed" errors.
    
    Usage:
        async with get_http_client() as client:
            response = await client.get("https://example.com")
    
    Args:
        timeout: Request timeout in seconds
        
    Yields:
        httpx.AsyncClient: The HTTP client
    """
    # Check if event loop is running to prevent "Event loop is closed" errors
    try:
        loop = asyncio.get_running_loop()
        if loop.is_closed():
            logger.warning("Detected closed event loop, creating a new one")
            new_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(new_loop)
    except RuntimeError:
        logger.warning("No running event loop detected, creating a new one")
        new_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(new_loop)
        
    # Create client with timeout and proper limits
    client = httpx.AsyncClient(
        timeout=timeout,
        limits=httpx.Limits(
            max_connections=100,
            max_keepalive_connections=20,
            keepalive_expiry=30.0
        )
    )
    
    try:
        yield client
    except Exception as e:
        logger.error(f"Error in HTTP client: {str(e)}")
        raise
    finally:
        try:
            await client.aclose()
        except Exception as e:
            logger.warning(f"Error closing HTTP client: {str(e)}")
            # Suppress exception during cleanup

async def fetch_json(
    url: str,
    method: str = "GET",
    data: Optional[Dict[str, Any]] = None,
    params: Optional[Dict[str, Any]] = None,
    headers: Optional[Dict[str, Any]] = None,
    timeout: float = 30.0
) -> Dict[str, Any]:
    """
    Fetch JSON data from a URL using httpx with proper error handling
    and event loop management.
    
    Args:
        url: URL to fetch data from
        method: HTTP method (GET, POST, etc.)
        data: Request data for POST/PUT requests
        params: URL parameters for GET requests
        headers: Request headers
        timeout: Request timeout in seconds
        
    Returns:
        Dict[str, Any]: JSON response
        
    Raises:
        httpx.HTTPStatusError: If the response status code is 4XX/5XX
    """
    async with get_http_client(timeout) as client:
        if method.upper() == "GET":
            response = await client.get(url, params=params, headers=headers)
        elif method.upper() == "POST":
            response = await client.post(url, data=data, headers=headers)
        elif method.upper() == "PUT":
            response = await client.put(url, data=data, headers=headers)
        elif method.upper() == "DELETE":
            response = await client.delete(url, headers=headers)
        else:
            raise ValueError(f"Unsupported HTTP method: {method}")
            
        # Raise exception for 4XX/5XX status codes
        response.raise_for_status()
        
        # Return JSON response
        return response.json()
