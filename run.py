#!/usr/bin/env python
"""
startup script for running the API.
"""
import uvicorn
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

if __name__ == "__main__":
    # Set default port or get from environment
    port = int(os.getenv("PORT", "8000"))
    
    # Run the API
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=port,
        reload=True,
        log_level="info"
    )