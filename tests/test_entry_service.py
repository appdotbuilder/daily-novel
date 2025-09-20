import pytest
from datetime import date
from app.services.entry_service import EntryService
from app.services.auth_service import AuthService
from app.services.wikipedia_service import WikipediaService
from app.models import UserCreate, DailyEntryCreate, DailyEntryUpdate, WikipediaImageCreate
from app.database import reset_db


@pytest.fixture()
def clean_db():
    """Clean database before each test"""
    reset_db()
    yield
    reset_db()


@pytest.fixture()
def test_user(clean_db):
    """Create test user"""
    user_data = UserCreate(
        username="testuser", email="test@example.com", password="password123", display_name="Test User"
    )
    return AuthService.create_user(user_data)


@pytest.fixture()
def test_wikipedia_image(clean_db):
    """Create test Wikipedia image"""
    image_data = WikipediaImageCreate(
        date=date.today(),
        title="Test Image",
        description="Test description",
        image_url="https://example.com/test.jpg",
        wikipedia_url="https://en.wikipedia.org/wiki/Test",
    )
    return WikipediaService.store_daily_image(image_data)


def test_create_entry_success(test_user, test_wikipedia_image):
    """Test successful entry creation"""
    entry_data = DailyEntryCreate(reflection_text="This is my reflection on today's image.", is_shared=True)

    entry = EntryService.create_entry(
        user_id=test_user.id, wikipedia_image_id=test_wikipedia_image.id, entry_data=entry_data, entry_date=date.today()
    )

    assert entry is not None
    assert entry.author_id == test_user.id
    assert entry.wikipedia_image_id == test_wikipedia_image.id
    assert entry.reflection_text == "This is my reflection on today's image."
    assert entry.is_shared
    assert entry.entry_date == date.today()
    assert entry.id is not None


def test_create_duplicate_entry_same_date(test_user, test_wikipedia_image):
    """Test that user cannot create multiple entries for same date"""
    entry_data = DailyEntryCreate(reflection_text="First reflection", is_shared=False)

    # Create first entry
    entry1 = EntryService.create_entry(
        user_id=test_user.id, wikipedia_image_id=test_wikipedia_image.id, entry_data=entry_data, entry_date=date.today()
    )
    assert entry1 is not None

    # Try to create second entry for same date
    entry_data2 = DailyEntryCreate(reflection_text="Second reflection", is_shared=True)

    entry2 = EntryService.create_entry(
        user_id=test_user.id,
        wikipedia_image_id=test_wikipedia_image.id,
        entry_data=entry_data2,
        entry_date=date.today(),
    )
    assert entry2 is None


def test_update_entry_success(test_user, test_wikipedia_image):
    """Test successful entry update"""
    # Create entry first
    entry_data = DailyEntryCreate(reflection_text="Original reflection", is_shared=False)

    entry = EntryService.create_entry(
        user_id=test_user.id, wikipedia_image_id=test_wikipedia_image.id, entry_data=entry_data, entry_date=date.today()
    )
    assert entry is not None

    # Update entry
    update_data = DailyEntryUpdate(reflection_text="Updated reflection", is_shared=True)

    assert entry.id is not None
    updated_entry = EntryService.update_entry(entry.id, test_user.id, update_data)
    assert updated_entry is not None
    assert updated_entry.reflection_text == "Updated reflection"
    assert updated_entry.is_shared
    assert updated_entry.updated_at > updated_entry.created_at


def test_update_entry_unauthorized(test_user, test_wikipedia_image):
    """Test that users cannot update other users' entries"""
    # Create second user
    user2_data = UserCreate(
        username="testuser2", email="test2@example.com", password="password123", display_name="Test User 2"
    )
    user2 = AuthService.create_user(user2_data)
    assert user2 is not None

    # Create entry by first user
    entry_data = DailyEntryCreate(reflection_text="Original reflection", is_shared=False)

    entry = EntryService.create_entry(
        user_id=test_user.id, wikipedia_image_id=test_wikipedia_image.id, entry_data=entry_data, entry_date=date.today()
    )
    assert entry is not None

    # Try to update by second user
    update_data = DailyEntryUpdate(reflection_text="Hacked!")
    assert entry.id is not None and user2.id is not None
    updated_entry = EntryService.update_entry(entry.id, user2.id, update_data)
    assert updated_entry is None


def test_update_nonexistent_entry(test_user):
    """Test updating nonexistent entry returns None"""
    update_data = DailyEntryUpdate(reflection_text="New text")
    result = EntryService.update_entry(999, test_user.id, update_data)
    assert result is None


def test_get_user_entry_for_date(test_user, test_wikipedia_image):
    """Test getting user's entry for specific date"""
    # Create entry
    entry_data = DailyEntryCreate(reflection_text="Today's reflection", is_shared=True)

    created_entry = EntryService.create_entry(
        user_id=test_user.id, wikipedia_image_id=test_wikipedia_image.id, entry_data=entry_data, entry_date=date.today()
    )
    assert created_entry is not None

    # Retrieve entry
    retrieved_entry = EntryService.get_user_entry_for_date(test_user.id, date.today())
    assert retrieved_entry is not None
    assert retrieved_entry.id == created_entry.id
    assert retrieved_entry.reflection_text == "Today's reflection"


def test_get_user_entry_for_date_nonexistent(test_user):
    """Test getting entry for date with no entry returns None"""
    result = EntryService.get_user_entry_for_date(test_user.id, date.today())
    assert result is None


def test_get_user_entries_history(test_user, test_wikipedia_image):
    """Test getting user's entry history"""
    # Create multiple entries (different dates)
    yesterday = date(2024, 1, 14)
    today = date(2024, 1, 15)

    # Create image for yesterday
    yesterday_image_data = WikipediaImageCreate(
        date=yesterday,
        title="Yesterday Image",
        description="Yesterday description",
        image_url="https://example.com/yesterday.jpg",
        wikipedia_url="https://en.wikipedia.org/wiki/Yesterday",
    )
    yesterday_image = WikipediaService.store_daily_image(yesterday_image_data)

    # Create entries
    entry1_data = DailyEntryCreate(reflection_text="Yesterday's reflection", is_shared=True)
    assert yesterday_image is not None and yesterday_image.id is not None
    EntryService.create_entry(
        user_id=test_user.id, wikipedia_image_id=yesterday_image.id, entry_data=entry1_data, entry_date=yesterday
    )

    entry2_data = DailyEntryCreate(reflection_text="Today's reflection", is_shared=False)
    assert test_wikipedia_image is not None and test_wikipedia_image.id is not None
    EntryService.create_entry(
        user_id=test_user.id, wikipedia_image_id=test_wikipedia_image.id, entry_data=entry2_data, entry_date=today
    )

    # Get history
    history = EntryService.get_user_entries_history(test_user.id)

    assert len(history) == 2
    # Should be ordered by date descending (newest first)
    assert history[0].entry_date == today.isoformat()
    assert history[1].entry_date == yesterday.isoformat()

    # Check content
    assert history[0].reflection_text == "Today's reflection"
    assert history[0].is_shared == False  # noqa: E712
    assert history[1].reflection_text == "Yesterday's reflection"
    assert history[1].is_shared == True  # noqa: E712


def test_get_user_entries_history_empty(test_user):
    """Test getting empty entry history"""
    history = EntryService.get_user_entries_history(test_user.id)
    assert history == []


def test_get_shared_entries(test_user, test_wikipedia_image):
    """Test getting shared entries from all users"""
    # Create second user
    user2_data = UserCreate(
        username="testuser2", email="test2@example.com", password="password123", display_name="Test User 2"
    )
    user2 = AuthService.create_user(user2_data)
    assert user2 is not None

    # Create shared entry
    shared_entry_data = DailyEntryCreate(reflection_text="This is shared", is_shared=True)
    EntryService.create_entry(
        user_id=test_user.id,
        wikipedia_image_id=test_wikipedia_image.id,
        entry_data=shared_entry_data,
        entry_date=date.today(),
    )

    # Create private entry
    private_entry_data = DailyEntryCreate(reflection_text="This is private", is_shared=False)
    assert user2.id is not None
    EntryService.create_entry(
        user_id=user2.id,
        wikipedia_image_id=test_wikipedia_image.id,
        entry_data=private_entry_data,
        entry_date=date(2024, 1, 14),  # Different date
    )

    # Get shared entries
    shared_entries = EntryService.get_shared_entries(limit=10)

    assert len(shared_entries) == 1
    assert shared_entries[0].reflection_text == "This is shared"
    assert shared_entries[0].is_shared
    assert shared_entries[0].author_display_name == "Test User"


def test_get_shared_entries_empty(clean_db):
    """Test getting shared entries when none exist"""
    shared_entries = EntryService.get_shared_entries()
    assert shared_entries == []


def test_get_entry_by_id(test_user, test_wikipedia_image):
    """Test getting entry by ID"""
    entry_data = DailyEntryCreate(reflection_text="Test reflection", is_shared=True)

    created_entry = EntryService.create_entry(
        user_id=test_user.id, wikipedia_image_id=test_wikipedia_image.id, entry_data=entry_data, entry_date=date.today()
    )
    assert created_entry is not None

    # Get entry by ID
    assert created_entry.id is not None
    retrieved_entry = EntryService.get_entry_by_id(created_entry.id)
    assert retrieved_entry is not None
    assert retrieved_entry.id == created_entry.id
    assert retrieved_entry.reflection_text == "Test reflection"


def test_get_entry_by_id_nonexistent(clean_db):
    """Test getting nonexistent entry returns None"""
    result = EntryService.get_entry_by_id(999)
    assert result is None
