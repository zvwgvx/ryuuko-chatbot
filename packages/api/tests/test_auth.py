import pytest
from fastapi.testclient import TestClient
import mongomock

# Set dummy env vars required by the app at import time
import os
os.environ["JWT_SECRET_KEY"] = "test-secret"

from main import app, get_db

# --- Mock Database Setup ---
# Create a single mongomock client instance for the entire test session
mock_mongo_client = mongomock.MongoClient()
mock_db = mock_mongo_client.ryuuko_db

def get_mock_db_override():
    """
    Dependency override function. This will replace the real `get_db`
    dependency in the FastAPI app during tests.
    """
    try:
        yield mock_db
    finally:
        # No actual connection to close
        pass

# Apply the dependency override to the app instance
app.dependency_overrides[get_db] = get_mock_db_override


# --- Test Fixtures ---
@pytest.fixture(scope="function")
def client():
    """
    Provides a TestClient for the app and ensures the mock DB is clean
    for each test, guaranteeing test isolation.
    """
    # Clear all collections in the mock database before each test
    for collection_name in mock_db.list_collection_names():
        mock_db.drop_collection(collection_name)

    # Yield the test client for the test function to use
    with TestClient(app) as test_client:
        yield test_client


# --- Test Cases ---

def test_register_user_success(client: TestClient):
    """Tests successful user registration."""
    response = client.post("/auth/register", json={
        "email": "test@example.com",
        "password": "password123",
        "display_name": "Test User"
    })
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "test@example.com"

    user_in_db = mock_db.users.find_one({"email": "test@example.com"})
    assert user_in_db is not None
    assert "password_hash" in user_in_db

def test_register_user_duplicate_email(client: TestClient):
    """Tests that registering with a duplicate email fails."""
    client.post("/auth/register", json={
        "email": "test@example.com", "password": "p1", "display_name": "U1"
    })
    response = client.post("/auth/register", json={
        "email": "test@example.com", "password": "p2", "display_name": "U2"
    })
    assert response.status_code == 400
    assert "Email already registered" in response.json()["detail"]

def test_login_success(client: TestClient):
    """Tests successful login and JWT token retrieval."""
    client.post("/auth/register", json={
        "email": "test@example.com", "password": "password123", "display_name": "Test User"
    })

    response = client.post("/auth/login", data={
        "username": "test@example.com", "password": "password123"
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

def test_login_incorrect_password(client: TestClient):
    """Tests that login fails with an incorrect password."""
    client.post("/auth/register", json={
        "email": "test@example.com", "password": "password123", "display_name": "Test User"
    })

    response = client.post("/auth/login", data={
        "username": "test@example.com", "password": "wrongpassword"
    })
    assert response.status_code == 401
    assert "Incorrect email or password" in response.json()["detail"]

def test_get_current_user_success(client: TestClient):
    """Tests fetching the current user's profile with a valid token."""
    client.post("/auth/register", json={
        "email": "test@example.com", "password": "password123", "display_name": "Test User"
    })
    login_response = client.post("/auth/login", data={
        "username": "test@example.com", "password": "password123"
    })
    token = login_response.json()["access_token"]

    response = client.get("/users/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "test@example.com"