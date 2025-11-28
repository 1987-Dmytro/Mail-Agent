"""Unit tests for Gmail label management methods.

Tests cover:
- list_labels(): Label list fetching and parsing
- create_label(): Label creation with color and visibility settings
- create_label() duplicate handling: 409 Conflict fallback to list_labels()
- apply_label(): Adding labels to email messages
- remove_label(): Removing labels from email messages
- Error handling for 404 Not Found errors
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest
from googleapiclient.errors import HttpError

from app.core.gmail_client import GmailClient


# Test Fixtures
@pytest.fixture
def mock_db_service():
    """Mock DatabaseService for dependency injection."""
    return Mock()


@pytest.fixture
def gmail_client(mock_db_service):
    """GmailClient instance with mocked database service."""
    return GmailClient(user_id=123, db_service=mock_db_service)


@pytest.fixture
def sample_labels_response():
    """Sample Gmail API labels().list() response."""
    return {
        "labels": [
            {
                "id": "INBOX",
                "name": "INBOX",
                "type": "system",
                "labelListVisibility": "labelShow",
            },
            {
                "id": "Label_123",
                "name": "Government",
                "type": "user",
                "labelListVisibility": "labelShow",
            },
            {
                "id": "Label_456",
                "name": "Work",
                "type": "user",
                "labelListVisibility": "labelShow",
            },
        ]
    }


@pytest.fixture
def sample_label_create_response():
    """Sample Gmail API labels().create() response."""
    return {
        "id": "Label_789",
        "name": "Important Clients",
        "type": "user",
        "labelListVisibility": "labelShow",
        "messageListVisibility": "show",
        "color": {"backgroundColor": "#FF5733"},
    }


# Test: list_labels() success
@pytest.mark.asyncio
async def test_list_labels_success(gmail_client, sample_labels_response):
    """Test successful label listing and parsing."""
    # Mock Gmail API service
    mock_service = Mock()
    mock_labels = Mock()
    mock_list = Mock()

    mock_service.users.return_value.labels.return_value = mock_labels
    mock_labels.list.return_value = mock_list
    mock_list.execute.return_value = sample_labels_response

    # Patch _get_gmail_service to return mock
    with patch.object(gmail_client, "_get_gmail_service", return_value=mock_service):
        labels = await gmail_client.list_labels()

    # Verify results
    assert len(labels) == 3
    assert labels[0]["label_id"] == "INBOX"
    assert labels[0]["name"] == "INBOX"
    assert labels[0]["type"] == "system"
    assert labels[1]["label_id"] == "Label_123"
    assert labels[1]["name"] == "Government"
    assert labels[1]["type"] == "user"


# Test: create_label() success with color
@pytest.mark.asyncio
async def test_create_label_with_color(gmail_client, sample_label_create_response):
    """Test successful label creation with color parameter."""
    # Mock Gmail API service
    mock_service = Mock()
    mock_labels = Mock()
    mock_create = Mock()

    mock_service.users.return_value.labels.return_value = mock_labels
    mock_labels.create.return_value = mock_create
    mock_create.execute.return_value = sample_label_create_response

    # Patch _get_gmail_service
    with patch.object(gmail_client, "_get_gmail_service", return_value=mock_service):
        label_id = await gmail_client.create_label(name="Important Clients", color="#FF5733")

    # Verify results
    assert label_id == "Label_789"

    # Verify API call was made with correct parameters
    mock_labels.create.assert_called_once()
    call_args = mock_labels.create.call_args
    assert call_args[1]["body"]["name"] == "Important Clients"
    assert call_args[1]["body"]["color"] == {"backgroundColor": "#FF5733"}


# Test: create_label() duplicate handling (409 Conflict)
@pytest.mark.asyncio
async def test_create_label_duplicate_returns_existing(gmail_client, sample_labels_response):
    """Test create_label() returns existing label ID on duplicate (409 Conflict)."""
    # Mock Gmail API service
    mock_service = Mock()
    mock_labels = Mock()
    mock_create = Mock()

    # Create 409 Conflict error
    http_error = HttpError(resp=Mock(status=409), content=b"Conflict")
    mock_create.execute.side_effect = http_error

    mock_service.users.return_value.labels.return_value = mock_labels
    mock_labels.create.return_value = mock_create

    # Mock list_labels to return existing label
    with patch.object(gmail_client, "_get_gmail_service", return_value=mock_service):
        with patch.object(gmail_client, "list_labels") as mock_list_labels:
            mock_list_labels.return_value = [
                {
                    "label_id": "Label_123",
                    "name": "Government",
                    "type": "user",
                    "visibility": "labelShow",
                }
            ]

            label_id = await gmail_client.create_label(name="Government")

    # Verify fallback to existing label
    assert label_id == "Label_123"
    mock_list_labels.assert_called_once()


# Test: apply_label() success
@pytest.mark.asyncio
async def test_apply_label_to_message(gmail_client):
    """Test successful label application to email message."""
    # Mock Gmail API service
    mock_service = Mock()
    mock_messages = Mock()
    mock_modify = Mock()

    mock_service.users.return_value.messages.return_value = mock_messages
    mock_messages.modify.return_value = mock_modify
    mock_modify.execute.return_value = {"id": "msg123", "labelIds": ["Label_123"]}

    # Patch _get_gmail_service
    with patch.object(gmail_client, "_get_gmail_service", return_value=mock_service):
        success = await gmail_client.apply_label(message_id="msg123", label_id="Label_123")

    # Verify results
    assert success is True

    # Verify API call
    mock_messages.modify.assert_called_once()
    call_args = mock_messages.modify.call_args
    assert call_args[1]["id"] == "msg123"
    assert call_args[1]["body"] == {"addLabelIds": ["Label_123"]}


# Test: remove_label() success
@pytest.mark.asyncio
async def test_remove_label_from_message(gmail_client):
    """Test successful label removal from email message."""
    # Mock Gmail API service
    mock_service = Mock()
    mock_messages = Mock()
    mock_modify = Mock()

    mock_service.users.return_value.messages.return_value = mock_messages
    mock_messages.modify.return_value = mock_modify
    mock_modify.execute.return_value = {"id": "msg123", "labelIds": []}

    # Patch _get_gmail_service
    with patch.object(gmail_client, "_get_gmail_service", return_value=mock_service):
        success = await gmail_client.remove_label(message_id="msg123", label_id="Label_123")

    # Verify results
    assert success is True

    # Verify API call
    mock_messages.modify.assert_called_once()
    call_args = mock_messages.modify.call_args
    assert call_args[1]["id"] == "msg123"
    assert call_args[1]["body"] == {"removeLabelIds": ["Label_123"]}


# Test: apply_label() 404 error
@pytest.mark.asyncio
async def test_apply_label_not_found(gmail_client):
    """Test apply_label() handles 404 Not Found errors."""
    # Mock Gmail API service
    mock_service = Mock()
    mock_messages = Mock()
    mock_modify = Mock()

    # Create 404 Not Found error
    http_error = HttpError(resp=Mock(status=404), content=b"Not Found")
    mock_modify.execute.side_effect = http_error

    mock_service.users.return_value.messages.return_value = mock_messages
    mock_messages.modify.return_value = mock_modify

    # Patch _get_gmail_service
    with patch.object(gmail_client, "_get_gmail_service", return_value=mock_service):
        success = await gmail_client.apply_label(message_id="invalid_id", label_id="Label_123")

    # Verify error handled gracefully
    assert success is False


# Test: label color configuration
@pytest.mark.asyncio
async def test_label_color_configuration(gmail_client, sample_label_create_response):
    """Test color parameter is correctly passed to Gmail API."""
    # Mock Gmail API service
    mock_service = Mock()
    mock_labels = Mock()
    mock_create = Mock()

    mock_service.users.return_value.labels.return_value = mock_labels
    mock_labels.create.return_value = mock_create
    mock_create.execute.return_value = sample_label_create_response

    # Test with color
    with patch.object(gmail_client, "_get_gmail_service", return_value=mock_service):
        await gmail_client.create_label(name="Red Label", color="#FF0000")

    # Verify color in API call
    call_args = mock_labels.create.call_args
    assert call_args[1]["body"]["color"]["backgroundColor"] == "#FF0000"

    # Reset mock
    mock_labels.reset_mock()

    # Test without color
    with patch.object(gmail_client, "_get_gmail_service", return_value=mock_service):
        await gmail_client.create_label(name="No Color Label")

    # Verify no color in API call
    call_args = mock_labels.create.call_args
    assert "color" not in call_args[1]["body"]
