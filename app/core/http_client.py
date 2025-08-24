"""
HTTP Client utility functions
Provides robust async HTTP client handling to avoid event loop issues
"""

import httpx
import asyncio
from typing import Optional, Dict, Any, Union
from contextlib import asynccontextmanager

@asynccontextmanager
async def get_http_client(timeout: float = 30.0) -> httpx.AsyncClient:
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
    client = httpx.AsyncClient(timeout=timeout)
    try:
        yield client
    finally:
        await client.aclose()

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
