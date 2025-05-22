# NeoFi Event Management System - Assignment Submission

This repository contains the backend implementation for the NeoFi Event Management System, developed as part of the assignment requirements.

## Overview

The system provides a collaborative event scheduling application with real-time notifications, version control, and role-based access control. It is built using FastAPI and SQLite (for development).

## Features

- **Authentication and Authorization:** Token-based authentication with role-based access control (Owner, Editor, Viewer).
- **Event Management:** CRUD operations, recurring events, conflict detection, and batch operations.
- **Collaboration Features:** Sharing system with permissions, real-time notifications, and edit history tracking.
- **Advanced Features:** Versioning system with rollback, changelog with diff, event conflict resolution, and transaction system.

## Tech Stack

- **Framework:** FastAPI
- **Database:** SQLite (development)
- **Authentication:** JWT
- **Real-time:** WebSocket
- **Testing:** pytest

## Prerequisites

- Python 3.8+
- pip
- virtualenv (recommended)

## Installation

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd neofi-backend-task
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   .\venv\Scripts\activate   # Windows
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Set up environment variables:
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

5. Initialize the database:
   ```bash
   python -m app.database
   ```

## Running the Application

### Development
```bash
uvicorn app.main:app --reload
```

### Production
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## API Documentation

Once the server is running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Testing

Run all tests:
```bash
pytest
```

Run specific test categories:
```bash
pytest tests/test_auth.py      # Authentication tests
pytest tests/test_events.py    # Event management tests
pytest tests/test_performance.py  # Performance tests
```

Run with coverage:
```bash
pytest --cov=app tests/
```

## Docker Deployment

1. Build the image:
   ```bash
   docker build -t neofi-event-system .
   ```

2. Run the container:
   ```bash
   docker run -p 8000:8000 neofi-event-system
   ```

## API Endpoints

### Authentication
- `POST /api/auth/register` - Register new user
- `POST /api/auth/login` - Login
- `POST /api/auth/refresh` - Refresh token
- `POST /api/auth/logout` - Logout

### Events
- `POST /api/events` - Create event
- `GET /api/events` - List events
- `GET /api/events/{id}` - Get event
- `PUT /api/events/{id}` - Update event
- `DELETE /api/events/{id}` - Delete event
- `POST /api/events/batch` - Create multiple events

### Collaboration
- `POST /api/events/{id}/share` - Share event
- `GET /api/events/{id}/permissions` - List permissions
- `PUT /api/events/{id}/permissions/{userId}` - Update permissions
- `DELETE /api/events/{id}/permissions/{userId}` - Remove access

### Version History
- `GET /api/events/{id}/history/{versionId}` - Get version
- `POST /api/events/{id}/rollback/{versionId}` - Rollback version
- `GET /api/events/{id}/changelog` - Get changelog
- `GET /api/events/{id}/diff/{versionId1}/{versionId2}` - Get diff

## Assignment Submission

This project is submitted as part of the NeoFi backend assignment. It demonstrates the implementation of a collaborative event management system with real-time notifications, version control, and role-based access control.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Key Concepts

- **Token-Based Authentication:** The system uses JWT tokens for secure user authentication. Tokens are issued upon login and must be included in subsequent requests for authorization.
- **Role-Based Access Control (RBAC):** Users are assigned roles (Owner, Editor, Viewer) that determine their permissions for event management and collaboration.
- **Event Management:** The system supports creating, reading, updating, and deleting events. It also handles recurring events and detects conflicts to ensure data integrity.
- **Real-Time Notifications:** WebSockets are used to provide real-time updates to users, such as event creation, updates, and sharing notifications.
- **Version Control:** Each event change is tracked, allowing users to view the history of modifications and roll back to previous versions if needed.
- **Conflict Resolution:** The system detects overlapping events and provides mechanisms to resolve conflicts, ensuring that event schedules remain consistent.
- **Batch Operations:** Users can perform multiple event operations in a single request, improving efficiency for bulk updates. 