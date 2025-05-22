from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.exceptions import RequestValidationError
from .routers import auth, events
from .database import engine, Base
from .utils.rate_limiter import rate_limit_middleware
from .utils.logger import logger
from .utils.error_handler import error_handler, APIError
from .utils.cache import cache
from .utils.websocket_manager import manager
from typing import Dict, List
import json
from datetime import datetime

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Event Management API",
    description="""
    A collaborative event management system with features including:
    
    * User authentication and authorization
    * Event CRUD operations
    * Recurring events
    * Conflict detection and resolution
    * Version control and rollback
    * Real-time notifications
    * Granular permissions
    """,
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json"
)

# Add exception handlers
app.add_exception_handler(Exception, error_handler)
app.add_exception_handler(APIError, error_handler)
app.add_exception_handler(RequestValidationError, error_handler)

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    
    # Add security schemes
    openapi_schema["components"]["securitySchemes"] = {
        "Bearer": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
        }
    }
    
    # Add security requirement to all operations
    for path in openapi_schema["paths"].values():
        for operation in path.values():
            operation["security"] = [{"Bearer": []}]
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add rate limiting middleware
app.middleware("http")(rate_limit_middleware)

# WebSocket endpoint for real-time notifications
@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: int):
    """
    WebSocket endpoint for real-time notifications.
    
    Parameters:
    - user_id: The ID of the user to receive notifications
    
    The connection will remain open and receive notifications for:
    - Event updates
    - New shares
    - Conflict resolutions
    - Permission changes
    """
    await manager.connect(websocket, user_id)
    try:
        while True:
            # Keep the connection alive and wait for notifications
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket, user_id)

# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(events.router, prefix="/api/events", tags=["Events"])

# Root endpoint
@app.get("/", tags=["Root"])
async def root():
    """
    Root endpoint that returns API information.
    
    Returns:
    - message: Welcome message
    - version: API version
    - docs_url: URL to API documentation
    """
    return {
        "message": "Welcome to the Event Management API",
        "version": app.version,
        "docs_url": "/api/docs"
    }

# Startup event
@app.on_event("startup")
async def startup_event():
    logger.info("Application startup")
    # Initialize cache
    cache.set("app_started", datetime.utcnow().isoformat())

# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Application shutdown")
    # Clear cache
    cache.clear_pattern("*") 