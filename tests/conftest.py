"""
Pytest configuration and fixtures for testing
"""
import pytest
import os
import sys
from unittest.mock import Mock, patch

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.database.db import SessionLocal
from src.api.app import app as flask_app


@pytest.fixture
def client():
    """Create a test client for the Flask app"""
    flask_app.config['TESTING'] = True
    with flask_app.test_client() as client:
        yield client


@pytest.fixture
def db_session():
    """Create a database session for testing"""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def admin_token():
    """Generate a mock admin JWT token"""
    import jwt
    from datetime import datetime, timedelta
    from src.config.settings import JWT_SECRET, JWT_ALGORITHM
    
    payload = {
        "userId": "test-admin-id",
        "email": "admin@test.com",
        "role": "admin",
        "exam_id": None,
        "exp": datetime.utcnow() + timedelta(days=30)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


@pytest.fixture
def user_token():
    """Generate a mock user JWT token"""
    import jwt
    from datetime import datetime, timedelta
    from src.config.settings import JWT_SECRET, JWT_ALGORITHM
    
    payload = {
        "userId": "test-user-id",
        "email": "user@test.com",
        "role": "user",
        "exam_id": "test-exam-id",
        "exp": datetime.utcnow() + timedelta(days=30)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


