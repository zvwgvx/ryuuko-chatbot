# tests/services/test_auth.py
"""
Test suite for the authentication service.
"""

import pytest
from unittest.mock import Mock, patch

# Import the service to be tested
from bot.services import auth

@pytest.fixture
def mock_mongodb_store():
    """Fixture to create a mock MongoDBStore."""
    return Mock()

class TestLoadAuthorizedUsers:
    """Tests for the load_authorized_users function."""

    def test_load_successfully(self, mock_mongodb_store):
        """
        Test that users are loaded correctly when the database call is successful.
        """
        # Arrange: Configure the mock to return a sample set of user IDs
        expected_users = {123, 456, 789}
        mock_mongodb_store.get_authorized_users.return_value = expected_users

        # Act: Call the function with the mock store
        result = auth.load_authorized_users(mock_mongodb_store)

        # Assert: Check that the correct set of users is returned
        assert result == expected_users
        mock_mongodb_store.get_authorized_users.assert_called_once()

    def test_load_with_database_exception(self, mock_mongodb_store):
        """
        Test that an empty set is returned when the database raises an exception.
        """
        # Arrange: Configure the mock to raise an exception
        mock_mongodb_store.get_authorized_users.side_effect = Exception("DB Connection Error")

        # Act: Call the function
        result = auth.load_authorized_users(mock_mongodb_store)

        # Assert: Check that an empty set is returned and the error was logged (implicitly)
        assert result == set()
        mock_mongodb_store.get_authorized_users.assert_called_once()


class TestAddAuthorizedUser:
    """Tests for the add_authorized_user function."""

    def test_add_user_successfully(self, mock_mongodb_store):
        """
        Test that a user is added successfully.
        """
        # Arrange: Configure the mock to return True for a successful addition
        user_id = 111
        mock_mongodb_store.add_authorized_user.return_value = True

        # Act: Call the function
        result = auth.add_authorized_user(user_id, mock_mongodb_store)

        # Assert: Check that the result is True and the mock was called correctly
        assert result is True
        mock_mongodb_store.add_authorized_user.assert_called_once_with(user_id)

    def test_add_user_already_exists(self, mock_mongodb_store):
        """
        Test that the function returns False if the user already exists.
        """
        # Arrange: Configure the mock to return False
        user_id = 222
        mock_mongodb_store.add_authorized_user.return_value = False

        # Act: Call the function
        result = auth.add_authorized_user(user_id, mock_mongodb_store)

        # Assert: Check that the result is False
        assert result is False
        mock_mongodb_store.add_authorized_user.assert_called_once_with(user_id)

    def test_add_user_with_database_exception(self, mock_mongodb_store):
        """
        Test that the function returns False when the database raises an exception.
        """
        # Arrange: Configure the mock to raise an exception
        user_id = 333
        mock_mongodb_store.add_authorized_user.side_effect = Exception("DB Write Error")

        # Act: Call the function
        result = auth.add_authorized_user(user_id, mock_mongodb_store)

        # Assert: Check that the result is False
        assert result is False
        mock_mongodb_store.add_authorized_user.assert_called_once_with(user_id)


class TestRemoveAuthorizedUser:
    """Tests for the remove_authorized_user function."""

    def test_remove_user_successfully(self, mock_mongodb_store):
        """
        Test that a user is removed successfully.
        """
        # Arrange: Configure the mock to return True for a successful removal
        user_id = 123
        mock_mongodb_store.remove_authorized_user.return_value = True

        # Act: Call the function
        result = auth.remove_authorized_user(user_id, mock_mongodb_store)

        # Assert: Check that the result is True and the mock was called correctly
        assert result is True
        mock_mongodb_store.remove_authorized_user.assert_called_once_with(user_id)

    def test_remove_user_does_not_exist(self, mock_mongodb_store):
        """
        Test that the function returns False if the user to be removed does not exist.
        """
        # Arrange: Configure the mock to return False
        user_id = 456
        mock_mongodb_store.remove_authorized_user.return_value = False

        # Act: Call the function
        result = auth.remove_authorized_user(user_id, mock_mongodb_store)

        # Assert: Check that the result is False
        assert result is False
        mock_mongodb_store.remove_authorized_user.assert_called_once_with(user_id)

    def test_remove_user_with_database_exception(self, mock_mongodb_store):
        """
        Test that the function returns False when the database raises an exception.
        """
        # Arrange: Configure the mock to raise an exception
        user_id = 789
        mock_mongodb_store.remove_authorized_user.side_effect = Exception("DB Write Error")

        # Act: Call the function
        result = auth.remove_authorized_user(user_id, mock_mongodb_store)

        # Assert: Check that the result is False
        assert result is False
        mock_mongodb_store.remove_authorized_user.assert_called_once_with(user_id)