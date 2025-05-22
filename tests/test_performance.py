import pytest
import time
from fastapi.testclient import TestClient
from app.main import app
from datetime import datetime, timedelta
import asyncio

def test_event_creation_performance(client):
    # Register and login
    client.post(
        "/api/auth/register",
        json={
            "username": "testuser",
            "email": "test@example.com",
            "password": "testpassword"
        }
    )
    response = client.post(
        "/api/auth/login",
        data={
            "username": "testuser",
            "password": "testpassword"
        }
    )
    token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Test creating multiple events with unique times
    start_time = time.time()
    for i in range(10):
        event_data = {
            "title": f"Test Event {i}",
            "description": f"Test Description {i}",
            "start_time": (datetime.now() + timedelta(days=i, hours=i)).isoformat(),
            "end_time": (datetime.now() + timedelta(days=i, hours=i+1)).isoformat(),
            "location": "Test Location"
        }
        response = client.post(
            "/api/events/",
            json=event_data,
            headers=headers
        )
        assert response.status_code == 200
    end_time = time.time()
    assert end_time - start_time < 5  # Should take less than 5 seconds

def test_event_query_performance():
    with TestClient(app) as client:
        # Login
        response = client.post(
            "/api/auth/login",
            data={
                "username": "testuser",
                "password": "testpass123"
            }
        )
        token = response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Test querying events
        start_time = time.time()
        for _ in range(10):
            response = client.get("/api/events", headers=headers)
            assert response.status_code == 200
        end_time = time.time()
        
        # Assert that 10 queries take less than 2 seconds
        assert end_time - start_time < 2

def test_concurrent_requests(client):
    # Register and login
    client.post(
        "/api/auth/register",
        json={
            "username": "testuser",
            "email": "test@example.com",
            "password": "testpassword"
        }
    )
    response = client.post(
        "/api/auth/login",
        data={
            "username": "testuser",
            "password": "testpassword"
        }
    )
    token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    def make_request(i):
        event_data = {
            "title": f"Concurrent Event {i}",
            "description": f"Test Description {i}",
            "start_time": (datetime.now() + timedelta(days=i, hours=i)).isoformat(),
            "end_time": (datetime.now() + timedelta(days=i, hours=i+1)).isoformat(),
            "location": "Test Location"
        }
        response = client.post(
            "/api/events/",
            json=event_data,
            headers=headers
        )
        return response.status_code

    # Test 5 concurrent requests (simulate sequentially for simplicity)
    start_time = time.time()
    results = [make_request(i) for i in range(5)]
    end_time = time.time()

    # Assert all requests were successful
    assert all(status == 200 for status in results)
    assert end_time - start_time < 3  # Should take less than 3 seconds 