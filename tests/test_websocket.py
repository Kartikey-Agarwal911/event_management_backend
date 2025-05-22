import pytest
from fastapi.testclient import TestClient
from app.main import app
import json
from datetime import datetime, timedelta
import asyncio
from unittest.mock import patch

@pytest.fixture(autouse=True)
def mock_rate_limiter():
    with patch('app.utils.rate_limiter.RateLimiter') as mock:
        mock.return_value.is_rate_limited.return_value = (False, 1000)
        yield mock

@pytest.mark.skip(reason="Replaced by real integration tests in test_websocket_integration.py")
def test_websocket_connection(client):
    # Register and login
    client.post(
        "/api/auth/register",
        json={
            "username": "testuser",
            "email": "test@example.com",
            "password": "testpass123"
        }
    )
    response = client.post(
        "/api/auth/login",
        data={
            "username": "testuser",
            "password": "testpass123"
        }
    )
    token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Connect to WebSocket
    with client.websocket_connect("/ws/1", headers=headers) as websocket:
        # Send a simple event
        event_data = {
            "title": "Test Event",
            "description": "Test Description",
            "start_time": datetime.now().isoformat(),
            "end_time": (datetime.now() + timedelta(hours=1)).isoformat(),
            "location": "Test Location"
        }
        client.post("/api/events/", json=event_data, headers=headers)
        # Wait for notification
        try:
            data = websocket.receive_text()
            notification = json.loads(data)
            assert "type" in notification
            assert notification["type"] == "event_created"
        except Exception as e:
            pytest.fail(f"Failed to receive notification: {str(e)}")

@pytest.mark.skip(reason="Replaced by real integration tests in test_websocket_integration.py")
def test_event_notification(client):
    # Register and login
    client.post(
        "/api/auth/register",
        json={
            "username": "testuser2",
            "email": "test2@example.com",
            "password": "testpass123"
        }
    )
    response = client.post(
        "/api/auth/login",
        data={
            "username": "testuser2",
            "password": "testpass123"
        }
    )
    token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Connect to WebSocket
    with client.websocket_connect("/ws/2", headers=headers) as websocket:
        # Create an event
        event_data = {
            "title": "Test Event",
            "description": "Test Description",
            "start_time": (datetime.now() + timedelta(days=1)).isoformat(),
            "end_time": (datetime.now() + timedelta(days=1, hours=1)).isoformat(),
            "location": "Test Location"
        }
        
        response = client.post(
            "/api/events/",
            json=event_data,
            headers=headers
        )
        
        # Check for notification
        try:
            data = websocket.receive_text()
            notification = json.loads(data)
            assert "type" in notification
            assert notification["type"] == "event_created"
            assert notification["event"]["title"] == "Test Event"
        except Exception as e:
            pytest.fail(f"Failed to receive notification: {str(e)}")

@pytest.mark.skip(reason="Replaced by real integration tests in test_websocket_integration.py")
def test_share_notification(client):
    # Register and login first user
    client.post(
        "/api/auth/register",
        json={
            "username": "testuser3",
            "email": "test3@example.com",
            "password": "testpass123"
        }
    )
    response = client.post(
        "/api/auth/login",
        data={
            "username": "testuser3",
            "password": "testpass123"
        }
    )
    token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Create a second user
    client.post(
        "/api/auth/register",
        json={
            "username": "testuser4",
            "email": "test4@example.com",
            "password": "testpass123"
        }
    )

    # Connect to WebSocket
    with client.websocket_connect("/ws/3", headers=headers) as websocket:
        # Create an event first
        event_data = {
            "title": "Test Event",
            "description": "Test Description",
            "start_time": (datetime.now() + timedelta(days=1)).isoformat(),
            "end_time": (datetime.now() + timedelta(days=1, hours=1)).isoformat(),
            "location": "Test Location"
        }
        event_response = client.post("/api/events/", json=event_data, headers=headers)
        event_id = event_response.json()["id"]

        # Share the event
        share_data = {
            "user_id": 4,
            "role": "editor"
        }
        
        client.post(
            f"/api/events/{event_id}/share",
            json=share_data,
            headers=headers
        )
        
        # Check for notification
        try:
            data = websocket.receive_text()
            notification = json.loads(data)
            assert "type" in notification
            assert notification["type"] == "event_shared"
            assert notification["event_id"] == event_id
        except Exception as e:
            pytest.fail(f"Failed to receive notification: {str(e)}") 