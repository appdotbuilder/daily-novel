"""Simple integration tests for enhanced messaging features that focus on service logic"""

import pytest
from datetime import date
from app.services.social_service import SocialService
from app.services.auth_service import AuthService
from app.services.wikipedia_service import WikipediaService
from app.services.entry_service import EntryService
from app.models import UserCreate, DailyEntryCreate, WikipediaImageCreate, ContactRequestCreate, DirectMessageCreate
from app.database import reset_db


@pytest.fixture()
def clean_db():
    """Clean database before each test"""
    reset_db()
    yield
    reset_db()


@pytest.fixture()
def test_setup(clean_db):
    """Create basic test setup with users and entry"""
    # Create two users
    user1_data = UserCreate(
        username="alice", email="alice@example.com", password="password123", display_name="Alice Smith"
    )
    user1 = AuthService.create_user(user1_data)

    user2_data = UserCreate(username="bob", email="bob@example.com", password="password123", display_name="Bob Johnson")
    user2 = AuthService.create_user(user2_data)

    # Verify users were created successfully
    assert user1 is not None and user1.id is not None
    assert user2 is not None and user2.id is not None

    # Create a Wikipedia image
    image_data = WikipediaImageCreate(
        date=date.today(),
        title="Beautiful Forest",
        description="A peaceful forest scene",
        image_url="https://example.com/forest.jpg",
        wikipedia_url="https://en.wikipedia.org/wiki/Forest",
    )
    wiki_image = WikipediaService.store_daily_image(image_data)
    assert wiki_image is not None and wiki_image.id is not None

    # Create a shared entry
    entry_data = DailyEntryCreate(reflection_text="Nature brings me peace and clarity.", is_shared=True)
    entry = EntryService.create_entry(
        user_id=user1.id, wikipedia_image_id=wiki_image.id, entry_data=entry_data, entry_date=date.today()
    )
    assert entry is not None and entry.id is not None

    return user1, user2, entry


def test_like_toggle_functionality(test_setup):
    """Test the core like toggle functionality"""
    user1, user2, entry = test_setup

    # Initially no likes
    assert SocialService.get_entry_likes_count(entry.id) == 0
    assert not SocialService.user_has_liked_entry(user2.id, entry.id)

    # User2 likes the entry
    result = SocialService.toggle_like(user2.id, entry.id)
    assert result  # Should return True for liked

    # Verify like was recorded
    assert SocialService.get_entry_likes_count(entry.id) == 1
    assert SocialService.user_has_liked_entry(user2.id, entry.id)

    # User2 unlikes the entry
    result = SocialService.toggle_like(user2.id, entry.id)
    assert not result  # Should return False for unliked

    # Verify like was removed
    assert SocialService.get_entry_likes_count(entry.id) == 0
    assert not SocialService.user_has_liked_entry(user2.id, entry.id)


def test_contact_request_requires_like(test_setup):
    """Test that contact requests require liking first"""
    user1, user2, entry = test_setup

    # Try to send contact request without liking
    request_data = ContactRequestCreate(recipient_id=user1.id, daily_entry_id=entry.id, message="Hello without liking!")
    contact_request = SocialService.send_contact_request(user2.id, request_data)
    assert contact_request is None  # Should fail

    # Like first, then send contact request
    SocialService.toggle_like(user2.id, entry.id)
    contact_request = SocialService.send_contact_request(user2.id, request_data)
    assert contact_request is not None  # Should succeed


def test_conversation_creation_flow(test_setup):
    """Test the complete flow from contact request to conversation"""
    user1, user2, entry = test_setup

    # Step 1: Like and send contact request
    SocialService.toggle_like(user2.id, entry.id)
    request_data = ContactRequestCreate(recipient_id=user1.id, daily_entry_id=entry.id, message="Love your reflection!")
    contact_request = SocialService.send_contact_request(user2.id, request_data)
    assert contact_request is not None and contact_request.id is not None

    # Step 2: Check pending requests
    pending_requests = SocialService.get_pending_contact_requests(user1.id)
    assert len(pending_requests) == 1
    request = pending_requests[0]

    # Access sender info while loaded (should work now with our fix)
    sender_name = request.sender.display_name if request.sender else "Unknown"
    assert sender_name == "Bob Johnson"

    # Step 3: Accept the request
    response = SocialService.respond_to_contact_request(contact_request.id, user1.id, accept=True)
    assert response is not None
    assert response.status.value == "accepted"

    # Step 4: Verify conversation was created
    user1_conversations = SocialService.get_user_conversations(user1.id)
    user2_conversations = SocialService.get_user_conversations(user2.id)

    assert len(user1_conversations) == 1
    assert len(user2_conversations) == 1

    conv1 = user1_conversations[0]
    conv2 = user2_conversations[0]

    assert conv1.id == conv2.id
    assert conv1.other_user_display_name == "Bob Johnson"
    assert conv2.other_user_display_name == "Alice Smith"


def test_messaging_functionality(test_setup):
    """Test direct messaging functionality"""
    user1, user2, entry = test_setup

    # Create conversation through contact request
    SocialService.toggle_like(user2.id, entry.id)
    request_data = ContactRequestCreate(recipient_id=user1.id, daily_entry_id=entry.id, message="Hi!")
    contact_request = SocialService.send_contact_request(user2.id, request_data)
    assert contact_request is not None and contact_request.id is not None

    SocialService.respond_to_contact_request(contact_request.id, user1.id, accept=True)

    # Get conversation
    conversations = SocialService.get_user_conversations(user1.id)
    assert len(conversations) == 1
    conv_id = conversations[0].id

    # Send messages
    message1_data = DirectMessageCreate(conversation_id=conv_id, message_text="Hello Alice!")
    message1 = SocialService.send_message(user2.id, message1_data)
    assert message1 is not None

    message2_data = DirectMessageCreate(conversation_id=conv_id, message_text="Hi Bob, thanks for reaching out!")
    message2 = SocialService.send_message(user1.id, message2_data)
    assert message2 is not None

    # Retrieve conversation messages
    messages = SocialService.get_conversation_messages(conv_id, user1.id)
    assert len(messages) == 2
    assert messages[0].message_text == "Hello Alice!"
    assert messages[1].message_text == "Hi Bob, thanks for reaching out!"


def test_unread_message_tracking(test_setup):
    """Test unread message tracking"""
    user1, user2, entry = test_setup

    # Create conversation
    SocialService.toggle_like(user2.id, entry.id)
    request_data = ContactRequestCreate(recipient_id=user1.id, daily_entry_id=entry.id, message="Hi!")
    contact_request = SocialService.send_contact_request(user2.id, request_data)
    assert contact_request is not None and contact_request.id is not None

    SocialService.respond_to_contact_request(contact_request.id, user1.id, accept=True)

    conversations = SocialService.get_user_conversations(user1.id)
    conv_id = conversations[0].id

    # Send message from user2
    message_data = DirectMessageCreate(conversation_id=conv_id, message_text="Hello!")
    SocialService.send_message(user2.id, message_data)

    # User1 should have unread messages
    user1_conversations = SocialService.get_user_conversations(user1.id)
    assert user1_conversations[0].unread_count == 1

    # Mark as read
    SocialService.mark_messages_as_read(conv_id, user1.id)

    # Should have no unread messages now
    user1_conversations = SocialService.get_user_conversations(user1.id)
    assert user1_conversations[0].unread_count == 0


def test_cannot_like_own_entry(test_setup):
    """Test that users cannot like their own entries"""
    user1, user2, entry = test_setup

    # User1 (author) tries to like their own entry
    result = SocialService.toggle_like(user1.id, entry.id)
    assert not result  # Should fail

    # Verify no like was recorded
    assert SocialService.get_entry_likes_count(entry.id) == 0
    assert not SocialService.user_has_liked_entry(user1.id, entry.id)
