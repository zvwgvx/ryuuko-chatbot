# /packages/ryuuko-api/src/tests/test_api.py
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

# It's important to set the environment variables *before* importing the app
import os
os.environ["CORE_API_KEY"] = "test-key"
os.environ["MONGODB_CONNECTION_STRING"] = "mongodb://localhost:27017/testdb"

# Now, import the app
from ..main import app, verify_api_key

# Create a TestClient instance
client = TestClient(app)

# --- Test Cases ---

def test_read_root():
    """Test the root endpoint to ensure the API is running."""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Ryuuko API is running."}

def test_list_models_unauthenticated():
    """Test that accessing a protected endpoint without an API key fails."""
    response = client.get("/api/v1/models")
    assert response.status_code == 403  # Expect 403 Forbidden for missing header

def test_list_models_wrong_key():
    """Test that accessing a protected endpoint with an incorrect API key fails."""
    response = client.get("/api/v1/models", headers={"X-API-Key": "wrong-key"})
    assert response.status_code == 401

# We use a patch to mock the database dependency for this test
@patch('src.main.db_store', new_callable=MagicMock)
def test_list_models_authenticated(mock_db_store):
    """Test the /api/v1/models endpoint with proper authentication and a mocked database."""
    # Configure the mock to return a sample list of models
    mock_db_store.list_all_models.return_value = [
        {"model_name": "test-model-1", "credit_cost": 10, "access_level": 1},
        {"model_name": "test-model-2", "credit_cost": 20, "access_level": 2},
    ]

    # Make the request with the correct API key
    response = client.get("/api/v1/models", headers={"X-API-Key": "test-key"})
    
    # Assertions
    assert response.status_code == 200
    assert len(response.json()) == 2
    assert response.json()[0]["model_name"] == "test-model-1"
    # Verify that our mock database function was called
    mock_db_store.list_all_models.assert_called_once()

@patch('src.main.db_store', new_callable=MagicMock)
def test_clear_user_memory_success(mock_db_store):
    """Test that clearing user memory returns a success message."""
    # Configure the mock to simulate a successful memory clear
    mock_db_store.clear_user_memory.return_value = True
    user_id = 12345

    response = client.delete(f"/api/v1/users/{user_id}/memory", headers={"X-API-Key": "test-key"})

    assert response.status_code == 200
    assert response.json() == {"message": f"Memory cleared for user {user_id}"}
    mock_db_store.clear_user_memory.assert_called_with(user_id)
