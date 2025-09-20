import pytest
from datetime import date
from app.services.social_service import SocialService
from app.services.auth_service import AuthService
from app.services.wikipedia_service import WikipediaService
from app.services.entry_service import EntryService
from app.models import (
    UserCreate,
    DailyEntryCreate,
    WikipediaImageCreate,
    ContactRequestCreate,
    DirectMessageCreate,
    MessageStatus,
)
from app.database import reset_db


@pytest.fixture()
def clean_db():
    """Clean database before each test"""
    reset_db()
    yield
    reset_db()


@pytest.fixture()
def test_users(clean_db):
    """Create test users"""
    user1_data = UserCreate(
        username="user1", email="user1@example.com", password="password123", display_name="User One"
    )
    user1 = AuthService.create_user(user1_data)

    user2_data = UserCreate(
        username="user2", email="user2@example.com", password="password123", display_name="User Two"
    )
    user2 = AuthService.create_user(user2_data)

    assert user1 is not None and user2 is not None
    return user1, user2


@pytest.fixture()
def shared_entry(test_users):
    """Create a shared entry"""
    user1, user2 = test_users

    # Create Wikipedia image
    image_data = WikipediaImageCreate(
        date=date.today(),
        title="Test Image",
        description="Test description",
        image_url="https://example.com/test.jpg",
        wikipedia_url="https://en.wikipedia.org/wiki/Test",
    )
    wiki_image = WikipediaService.store_daily_image(image_data)
    assert wiki_image is not None and wiki_image.id is not None

    # Create shared entry
    entry_data = DailyEntryCreate(reflection_text="This is a shared reflection", is_shared=True)
    entry = EntryService.create_entry(
        user_id=user1.id, wikipedia_image_id=wiki_image.id, entry_data=entry_data, entry_date=date.today()
    )

    assert entry is not None and entry.id is not None
    return entry, user1, user2


def test_toggle_like_success(shared_entry):
    """Test successfully liking an entry"""
    entry, user1, user2 = shared_entry

    # User2 likes user1's entry
    result = SocialService.toggle_like(user2.id, entry.id)
    assert result  # Entry was liked

    # Verify like exists
    assert SocialService.user_has_liked_entry(user2.id, entry.id)
    assert SocialService.get_entry_likes_count(entry.id) == 1


def test_toggle_like_unlike(shared_entry):
    """Test unliking an entry"""
    entry, user1, user2 = shared_entry

    # Like first
    result1 = SocialService.toggle_like(user2.id, entry.id)
    assert result1
    assert SocialService.get_entry_likes_count(entry.id) == 1

    # Unlike
    result2 = SocialService.toggle_like(user2.id, entry.id)
    assert not result2  # Entry was unliked
    assert not SocialService.user_has_liked_entry(user2.id, entry.id)
    assert SocialService.get_entry_likes_count(entry.id) == 0


def test_cannot_like_own_entry(shared_entry):
    """Test that users cannot like their own entries"""
    entry, user1, user2 = shared_entry

    # User1 tries to like their own entry
    result = SocialService.toggle_like(user1.id, entry.id)
    assert not result  # Should not be allowed
    assert not SocialService.user_has_liked_entry(user1.id, entry.id)
    assert SocialService.get_entry_likes_count(entry.id) == 0


def test_send_contact_request_success(shared_entry):
    """Test sending contact request after liking"""
    entry, user1, user2 = shared_entry

    # User2 likes the entry first
    SocialService.toggle_like(user2.id, entry.id)

    # Send contact request
    request_data = ContactRequestCreate(
        recipient_id=user1.id, daily_entry_id=entry.id, message="I loved your reflection!"
    )

    contact_request = SocialService.send_contact_request(user2.id, request_data)
    assert contact_request is not None
    assert contact_request.sender_id == user2.id
    assert contact_request.recipient_id == user1.id
    assert contact_request.daily_entry_id == entry.id
    assert contact_request.message == "I loved your reflection!"
    assert contact_request.status == MessageStatus.PENDING


def test_respond_to_contact_request_accept(shared_entry):
    """Test accepting contact request"""
    entry, user1, user2 = shared_entry

    # Setup contact request
    SocialService.toggle_like(user2.id, entry.id)
    request_data = ContactRequestCreate(recipient_id=user1.id, daily_entry_id=entry.id, message="Hello!")
    contact_request = SocialService.send_contact_request(user2.id, request_data)
    assert contact_request is not None and contact_request.id is not None

    # Accept request
    response = SocialService.respond_to_contact_request(contact_request.id, user1.id, accept=True)
    assert response is not None
    assert response.status == MessageStatus.ACCEPTED
    assert response.responded_at is not None


def test_get_user_conversations_empty(test_users):
    """Test getting conversations when user has none"""
    user1, user2 = test_users

    conversations = SocialService.get_user_conversations(user1.id)
    assert conversations == []


def test_send_direct_message_and_get_messages(shared_entry):
    """Test sending direct message after accepted contact request"""
    entry, user1, user2 = shared_entry

    # Setup accepted contact request (creates conversation)
    SocialService.toggle_like(user2.id, entry.id)
    request_data = ContactRequestCreate(recipient_id=user1.id, daily_entry_id=entry.id, message="Hello!")
    contact_request = SocialService.send_contact_request(user2.id, request_data)
    assert contact_request is not None and contact_request.id is not None

    SocialService.respond_to_contact_request(contact_request.id, user1.id, accept=True)

    # Get conversations to find conversation ID
    conversations = SocialService.get_user_conversations(user1.id)
    assert len(conversations) == 1
    conv_id = conversations[0].id

    # Send message
    message_data = DirectMessageCreate(conversation_id=conv_id, message_text="Hello, nice to meet you!")
    message = SocialService.send_message(user2.id, message_data)
    assert message is not None
    assert message.sender_id == user2.id
    assert message.message_text == "Hello, nice to meet you!"

    # Get messages
    messages = SocialService.get_conversation_messages(conv_id, user1.id)
    assert len(messages) == 1
    assert messages[0].message_text == "Hello, nice to meet you!"
