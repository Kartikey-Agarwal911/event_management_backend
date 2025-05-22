import asyncio
import httpx
import websockets
import pytest
import json
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from app.main import app
from unittest.mock import patch
import uuid
from app.database import reset_database

@pytest.fixture(autouse=True)
def mock_rate_limiter():
    with patch('app.utils.rate_limiter.RateLimiter') as mock:
        mock.return_value.is_rate_limited.return_value = (False, 1000)
        yield mock

@pytest.fixture(autouse=True)
def clear_db():
    reset_database()
    yield

@pytest.mark.asyncio
async def test_websocket_event_notification_integration():
    # Create test client
    client = TestClient(app)
    
    # Use a unique username/email
    unique_id = str(uuid.uuid4())[:8]
    username = f"testuser_{unique_id}"
    email = f"test_{unique_id}@example.com"
    
    # Register user
    response = client.post(
        "/api/auth/register",
        json={
            "username": username,
            "email": email,
            "password": "testpass123"
        }
    )
    if response.status_code != 200:
        print('Registration response:', response.status_code, response.text)
    assert response.status_code == 200
    
    # Login
    response = client.post(
        "/api/auth/login",
        data={
            "username": username,
            "password": "testpass123"
        }
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Connect to WebSocket
    with client.websocket_connect("/ws/1", headers=headers) as websocket:
        # Create an event
        event_data = {
            "title": "Test Event",
            "description": "Testing WebSocket notifications",
            "start_time": datetime.now().isoformat(),
            "end_time": (datetime.now() + timedelta(hours=1)).isoformat(),
            "location": "Test Location"
        }
        
        # Send event creation request
        response = client.post(
            "/api/events/",
            json=event_data,
            headers=headers
        )
        assert response.status_code == 200
        
        # Wait for notification
        data = websocket.receive_text()
        notification = json.loads(data)
        assert notification["type"] == "event_created"
        assert notification["event"]["title"] == "Test Event" 