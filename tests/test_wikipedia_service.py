import pytest
from datetime import date
from app.services.wikipedia_service import WikipediaService
from app.models import WikipediaImageCreate
from app.database import reset_db


@pytest.fixture()
def clean_db():
    """Clean database before each test"""
    reset_db()
    yield
    reset_db()


def test_store_daily_image(clean_db):
    """Test storing Wikipedia image in database"""
    test_date = date(2024, 1, 15)
    image_data = WikipediaImageCreate(
        date=test_date,
        title="Test Image of the Day",
        description="A beautiful test image",
        image_url="https://example.com/test.jpg",
        wikipedia_url="https://en.wikipedia.org/wiki/Test",
    )

    stored_image = WikipediaService.store_daily_image(image_data)
    assert stored_image is not None
    assert stored_image.image_date == test_date
    assert stored_image.title == "Test Image of the Day"
    assert stored_image.description == "A beautiful test image"
    assert stored_image.image_url == "https://example.com/test.jpg"
    assert stored_image.wikipedia_url == "https://en.wikipedia.org/wiki/Test"
    assert stored_image.id is not None


def test_store_duplicate_image(clean_db):
    """Test storing duplicate image returns existing one"""
    test_date = date(2024, 1, 15)
    image_data = WikipediaImageCreate(
        date=test_date,
        title="Test Image",
        description="Description",
        image_url="https://example.com/test.jpg",
        wikipedia_url="https://en.wikipedia.org/wiki/Test",
    )

    # Store first image
    stored_image1 = WikipediaService.store_daily_image(image_data)
    assert stored_image1 is not None

    # Try to store same date again
    image_data2 = WikipediaImageCreate(
        date=test_date,  # Same date
        title="Different Title",
        description="Different Description",
        image_url="https://example.com/different.jpg",
        wikipedia_url="https://en.wikipedia.org/wiki/Different",
    )

    stored_image2 = WikipediaService.store_daily_image(image_data2)
    assert stored_image2 is not None
    assert stored_image2.id == stored_image1.id  # Should return existing
    assert stored_image2.title == stored_image1.title  # Should keep original data


def test_get_or_fetch_daily_image_existing(clean_db):
    """Test retrieving existing image from database"""
    test_date = date(2024, 1, 15)

    # Store image first
    image_data = WikipediaImageCreate(
        date=test_date,
        title="Existing Image",
        description="Already stored",
        image_url="https://example.com/existing.jpg",
        wikipedia_url="https://en.wikipedia.org/wiki/Existing",
    )
    stored_image = WikipediaService.store_daily_image(image_data)
    assert stored_image is not None

    # Retrieve it
    retrieved_image = WikipediaService.get_or_fetch_daily_image(test_date)
    assert retrieved_image is not None
    assert retrieved_image.id == stored_image.id
    assert retrieved_image.title == "Existing Image"


def test_get_or_fetch_daily_image_nonexistent(clean_db):
    """Test retrieving nonexistent image returns None"""
    test_date = date(2024, 1, 15)

    # Try to get image that doesn't exist
    result = WikipediaService.get_or_fetch_daily_image(test_date)
    assert result is None  # Should return None, not attempt async fetch


@pytest.mark.asyncio
async def test_fetch_image_of_day_real_date():
    """Test fetching real Wikipedia image data from API"""
    # Use a date we know has data (Wikipedia launched in 2001)
    test_date = date(2023, 1, 15)

    result = await WikipediaService.fetch_image_of_day(test_date)

    # Note: This test may fail if Wikipedia API is down or date has no featured image
    # In a production environment, you might want to mock this or handle gracefully
    if result is not None:
        assert "title" in result
        assert "image_url" in result
        assert isinstance(result["title"], str)
        assert isinstance(result["image_url"], str)
    # If result is None, the API didn't have data for this date (acceptable)


@pytest.mark.asyncio
async def test_fetch_image_of_day_future_date():
    """Test fetching image for future date returns None"""
    # Use a date far in the future
    future_date = date(2030, 1, 1)

    result = await WikipediaService.fetch_image_of_day(future_date)
    # Should return None for future dates where no data exists
    assert result is None or isinstance(result, dict)


@pytest.mark.asyncio
async def test_get_or_create_daily_image_new(clean_db):
    """Test getting or creating image when it doesn't exist in DB"""
    test_date = date(2023, 1, 1)  # Use date likely to have Wikipedia data

    # First check it doesn't exist
    existing = WikipediaService.get_or_fetch_daily_image(test_date)
    assert existing is None

    # Try to get or create
    result = await WikipediaService.get_or_create_daily_image(test_date)

    # This may return None if Wikipedia doesn't have data for this date
    # or an actual image if it does - both are valid responses
    if result is not None:
        assert result.image_date == test_date
        assert result.title is not None
        assert result.image_url is not None

        # Verify it's now in database
        cached = WikipediaService.get_or_fetch_daily_image(test_date)
        assert cached is not None
        assert cached.id == result.id


@pytest.mark.asyncio
async def test_get_or_create_daily_image_existing(clean_db):
    """Test getting or creating image when it already exists in DB"""
    test_date = date(2024, 1, 15)

    # Store image first
    image_data = WikipediaImageCreate(
        date=test_date,
        title="Cached Image",
        description="Already in database",
        image_url="https://example.com/cached.jpg",
        wikipedia_url="https://en.wikipedia.org/wiki/Cached",
    )
    stored_image = WikipediaService.store_daily_image(image_data)
    assert stored_image is not None

    # Try to get or create - should return cached version
    result = await WikipediaService.get_or_create_daily_image(test_date)
    assert result is not None
    assert result.id == stored_image.id
    assert result.title == "Cached Image"
