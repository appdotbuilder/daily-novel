import pytest
from datetime import date, datetime
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
)
from app.database import reset_db


@pytest.fixture()
def clean_db():
    """Clean database before each test"""
    reset_db()
    yield
    reset_db()


@pytest.fixture()
def test_users_with_conversation(clean_db):
    """Create test users with an active conversation"""
    # Create users
    user1_data = UserCreate(
        username="alice", email="alice@example.com", password="password123", display_name="Alice Smith"
    )
    user1 = AuthService.create_user(user1_data)

    user2_data = UserCreate(username="bob", email="bob@example.com", password="password123", display_name="Bob Johnson")
    user2 = AuthService.create_user(user2_data)

    assert user1 is not None and user2 is not None
    assert user1.id is not None and user2.id is not None

    # Create Wikipedia image
    image_data = WikipediaImageCreate(
        date=date.today(),
        title="Test Image for Conversation",
        description="Test description",
        image_url="https://example.com/test.jpg",
        wikipedia_url="https://en.wikipedia.org/wiki/Test",
    )
    wiki_image = WikipediaService.store_daily_image(image_data)
    assert wiki_image is not None and wiki_image.id is not None

    # Create shared entry
    entry_data = DailyEntryCreate(reflection_text="This is a shared reflection for testing", is_shared=True)
    entry = EntryService.create_entry(
        user_id=user1.id, wikipedia_image_id=wiki_image.id, entry_data=entry_data, entry_date=date.today()
    )

    assert entry is not None and entry.id is not None

    # Create conversation through contact request process
    SocialService.toggle_like(user2.id, entry.id)
    request_data = ContactRequestCreate(recipient_id=user1.id, daily_entry_id=entry.id, message="Hello!")
    contact_request = SocialService.send_contact_request(user2.id, request_data)
    assert contact_request is not None and contact_request.id is not None

    SocialService.respond_to_contact_request(contact_request.id, user1.id, accept=True)

    return user1, user2, entry


def test_conversation_creation_and_retrieval(test_users_with_conversation):
    """Test that conversations are created and can be retrieved"""
    user1, user2, entry = test_users_with_conversation

    # Both users should see the conversation
    user1_conversations = SocialService.get_user_conversations(user1.id)
    user2_conversations = SocialService.get_user_conversations(user2.id)

    assert len(user1_conversations) == 1
    assert len(user2_conversations) == 1

    # Verify conversation details
    conv1 = user1_conversations[0]
    conv2 = user2_conversations[0]

    assert conv1.id == conv2.id  # Same conversation
    assert conv1.other_user_display_name == "Bob Johnson"
    assert conv2.other_user_display_name == "Alice Smith"
    assert conv1.unread_count == 0
    assert conv2.unread_count == 0


def test_multiple_messages_in_conversation(test_users_with_conversation):
    """Test sending multiple messages and conversation flow"""
    user1, user2, entry = test_users_with_conversation

    conversations = SocialService.get_user_conversations(user1.id)
    conv_id = conversations[0].id

    # User2 sends first message
    message1_data = DirectMessageCreate(conversation_id=conv_id, message_text="Hi Alice! I loved your reflection.")
    message1 = SocialService.send_message(user2.id, message1_data)
    assert message1 is not None

    # User1 replies
    message2_data = DirectMessageCreate(
        conversation_id=conv_id, message_text="Thank you Bob! I'm glad it resonated with you."
    )
    message2 = SocialService.send_message(user1.id, message2_data)
    assert message2 is not None

    # User2 sends another message
    message3_data = DirectMessageCreate(
        conversation_id=conv_id,
        message_text="I've been thinking about similar themes lately. Would love to discuss more!",
    )
    message3 = SocialService.send_message(user2.id, message3_data)
    assert message3 is not None

    # Get conversation messages
    user1_messages = SocialService.get_conversation_messages(conv_id, user1.id)
    user2_messages = SocialService.get_conversation_messages(conv_id, user2.id)

    # Both users should see all messages
    assert len(user1_messages) == 3
    assert len(user2_messages) == 3

    # Verify message order (chronological)
    assert user1_messages[0].message_text == "Hi Alice! I loved your reflection."
    assert user1_messages[1].message_text == "Thank you Bob! I'm glad it resonated with you."
    assert (
        user1_messages[2].message_text == "I've been thinking about similar themes lately. Would love to discuss more!"
    )


def test_unread_message_tracking(test_users_with_conversation):
    """Test unread message tracking and marking as read"""
    user1, user2, entry = test_users_with_conversation

    conversations = SocialService.get_user_conversations(user1.id)
    conv_id = conversations[0].id

    # User2 sends a message
    message_data = DirectMessageCreate(conversation_id=conv_id, message_text="Hello Alice!")
    SocialService.send_message(user2.id, message_data)

    # User1 should have 1 unread message
    user1_conversations = SocialService.get_user_conversations(user1.id)
    assert user1_conversations[0].unread_count == 1

    # User2 should have 0 unread messages
    user2_conversations = SocialService.get_user_conversations(user2.id)
    assert user2_conversations[0].unread_count == 0

    # User1 marks messages as read
    result = SocialService.mark_messages_as_read(conv_id, user1.id)
    assert result

    # Now user1 should have 0 unread messages
    user1_conversations = SocialService.get_user_conversations(user1.id)
    assert user1_conversations[0].unread_count == 0


def test_conversation_last_message_timestamp(test_users_with_conversation):
    """Test that conversation last_message_at is updated correctly"""
    user1, user2, entry = test_users_with_conversation

    conversations = SocialService.get_user_conversations(user1.id)
    conv_id = conversations[0].id

    # Initially no last message time
    initial_conversations = SocialService.get_user_conversations(user1.id)
    assert initial_conversations[0].last_message_at is None

    # Send a message
    message_data = DirectMessageCreate(conversation_id=conv_id, message_text="First message")
    sent_message = SocialService.send_message(user1.id, message_data)
    assert sent_message is not None

    # Check that last_message_at is updated
    updated_conversations = SocialService.get_user_conversations(user1.id)
    assert updated_conversations[0].last_message_at is not None

    # Parse the ISO format timestamp to verify it's recent
    last_message_time = datetime.fromisoformat(updated_conversations[0].last_message_at)
    time_diff = datetime.utcnow() - last_message_time
    assert time_diff.seconds < 10  # Should be very recent


def test_like_functionality_affects_contact_visibility(clean_db):
    """Test that liking affects contact button visibility"""
    # Create users
    user1_data = UserCreate(
        username="user1", email="user1@example.com", password="password123", display_name="User One"
    )
    user1 = AuthService.create_user(user1_data)

    user2_data = UserCreate(
        username="user2", email="user2@example.com", password="password123", display_name="User Two"
    )
    user2 = AuthService.create_user(user2_data)

    assert user1 is not None and user2 is not None
    assert user1.id is not None and user2.id is not None

    # Create Wikipedia image and entry
    image_data = WikipediaImageCreate(
        date=date.today(),
        title="Test Image",
        description="Test description",
        image_url="https://example.com/test.jpg",
        wikipedia_url="https://en.wikipedia.org/wiki/Test",
    )
    wiki_image = WikipediaService.store_daily_image(image_data)
    assert wiki_image is not None and wiki_image.id is not None

    entry_data = DailyEntryCreate(reflection_text="This is a test reflection", is_shared=True)
    entry = EntryService.create_entry(
        user_id=user1.id, wikipedia_image_id=wiki_image.id, entry_data=entry_data, entry_date=date.today()
    )

    assert entry is not None and entry.id is not None

    # User2 hasn't liked yet
    assert not SocialService.user_has_liked_entry(user2.id, entry.id)
    assert SocialService.get_entry_likes_count(entry.id) == 0

    # Like the entry
    result = SocialService.toggle_like(user2.id, entry.id)
    assert result  # Should be liked

    # Verify like status
    assert SocialService.user_has_liked_entry(user2.id, entry.id)
    assert SocialService.get_entry_likes_count(entry.id) == 1

    # Unlike the entry
    result = SocialService.toggle_like(user2.id, entry.id)
    assert not result  # Should be unliked

    # Verify unlike status
    assert not SocialService.user_has_liked_entry(user2.id, entry.id)
    assert SocialService.get_entry_likes_count(entry.id) == 0


def test_empty_conversation_messages(test_users_with_conversation):
    """Test retrieving messages from empty conversation"""
    user1, user2, entry = test_users_with_conversation

    conversations = SocialService.get_user_conversations(user1.id)
    conv_id = conversations[0].id

    # New conversation should have no messages
    messages = SocialService.get_conversation_messages(conv_id, user1.id)
    assert messages == []


def test_unauthorized_conversation_access(test_users_with_conversation):
    """Test that users cannot access conversations they're not part of"""
    user1, user2, entry = test_users_with_conversation

    # Create a third user
    user3_data = UserCreate(
        username="user3", email="user3@example.com", password="password123", display_name="User Three"
    )
    user3 = AuthService.create_user(user3_data)
    assert user3 is not None

    conversations = SocialService.get_user_conversations(user1.id)
    conv_id = conversations[0].id

    # User3 should not be able to access the conversation
    assert user3.id is not None
    messages = SocialService.get_conversation_messages(conv_id, user3.id)
    assert messages == []

    # User3 should not be able to send messages
    message_data = DirectMessageCreate(conversation_id=conv_id, message_text="Unauthorized message")
    result = SocialService.send_message(user3.id, message_data)
    assert result is None


def test_contact_request_without_like_fails(clean_db):
    """Test that contact requests fail if user hasn't liked the entry"""
    # Create users and entry
    user1_data = UserCreate(
        username="user1", email="user1@example.com", password="password123", display_name="User One"
    )
    user1 = AuthService.create_user(user1_data)

    user2_data = UserCreate(
        username="user2", email="user2@example.com", password="password123", display_name="User Two"
    )
    user2 = AuthService.create_user(user2_data)

    # Verify users were created with IDs
    assert user1 is not None and user1.id is not None
    assert user2 is not None and user2.id is not None

    image_data = WikipediaImageCreate(
        date=date.today(),
        title="Test Image",
        description="Test description",
        image_url="https://example.com/test.jpg",
        wikipedia_url="https://en.wikipedia.org/wiki/Test",
    )
    wiki_image = WikipediaService.store_daily_image(image_data)
    assert wiki_image is not None and wiki_image.id is not None

    entry_data = DailyEntryCreate(reflection_text="This is a test reflection", is_shared=True)
    entry = EntryService.create_entry(
        user_id=user1.id, wikipedia_image_id=wiki_image.id, entry_data=entry_data, entry_date=date.today()
    )
    assert entry is not None and entry.id is not None

    # Try to send contact request without liking
    request_data = ContactRequestCreate(recipient_id=user1.id, daily_entry_id=entry.id, message="Hello without liking!")

    contact_request = SocialService.send_contact_request(user2.id, request_data)
    assert contact_request is None  # Should fail
