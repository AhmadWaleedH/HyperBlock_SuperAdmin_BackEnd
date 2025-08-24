#!/usr/bin/env python
"""
startup script for running the API.
"""
import uvicorn
import os
import asyncio
import platform
import logging
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("hyperblock-api")

# Load environment variables
load_dotenv()

# Configure asyncio policies based on platform
if platform.system() == "Windows":
    # Windows-specific event loop policy
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    logger.info("Using WindowsSelectorEventLoopPolicy for Windows")
else:
    # For Unix-based systems, ensure we use the default policy with proper cleanup
    try:
        import uvloop
        asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
        logger.info("Using uvloop event loop policy")
    except ImportError:
        logger.info("uvloop not available, using default event loop policy")

if __name__ == "__main__":
    # Set default port or get from environment
    port = int(os.getenv("PORT", "8000"))
    
    # Configure asyncio debug mode based on environment
    debug_mode = os.getenv("DEBUG", "false").lower() in ("true", "1", "yes")
    if debug_mode:
        logger.info("Running in debug mode with asyncio debug enabled")
    
    # Run the API with explicit event loop settings
    logger.info(f"Starting HyperBlock API on port {port}")
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=port,
        reload=True,
        log_level="info",
        loop="auto"
    )