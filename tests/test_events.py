import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database import Base, engine, get_db
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta

# Create test database
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)

def get_test_token():
    # Register and login to get token
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
    return response.json()["access_token"]

def test_create_event(client):
    token = get_test_token()
    headers = {"Authorization": f"Bearer {token}"}
    response = client.post("/api/events/", json={"title": "Test Event", "description": "Test Description", "start_time": "2023-01-01T10:00:00", "end_time": "2023-01-01T11:00:00"}, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Test Event"
    assert "id" in data

def test_create_recurring_event(client):
    token = get_test_token()
    headers = {"Authorization": f"Bearer {token}"}
    response = client.post(
        "/api/events/",
        json={
            "title": "Recurring Event",
            "description": "Recurring event description",
            "start_time": "2023-01-01T10:00:00",
            "end_time": "2023-01-01T11:00:00",
            "is_recurring": True,
            "recurrence_frequency": "weekly",
            "recurrence_interval": 1,
            "recurrence_days": ["monday"],
            "recurrence_end_type": "count",
            "recurrence_end_count": 4
        },
        headers=headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Recurring Event"
    assert "id" in data

def test_event_conflict(client):
    token = get_test_token()
    headers = {"Authorization": f"Bearer {token}"}
    # Create a base event
    client.post(
        "/api/events/",
        json={
            "title": "Base Event",
            "description": "Base event description",
            "start_time": "2023-01-01T10:00:00",
            "end_time": "2023-01-01T11:00:00"
        },
        headers=headers
    )
    # Try to create a conflicting event
    response = client.post(
        "/api/events/",
        json={
            "title": "Conflicting Event",
            "description": "Conflicting event description",
            "start_time": "2023-01-01T10:00:00",
            "end_time": "2023-01-01T11:00:00"
        },
        headers=headers
    )
    assert response.status_code == 409
    data = response.json()
    assert "detail" in data 