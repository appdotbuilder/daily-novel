import pytest
from app.services.auth_service import AuthService
from app.models import UserCreate, UserLogin
from app.database import reset_db


@pytest.fixture()
def clean_db():
    """Clean database before each test"""
    reset_db()
    yield
    reset_db()


def test_create_user_success(clean_db):
    """Test successful user creation"""
    user_data = UserCreate(
        username="testuser", email="test@example.com", password="password123", display_name="Test User"
    )

    user = AuthService.create_user(user_data)
    assert user is not None
    assert user.username == "testuser"
    assert user.email == "test@example.com"
    assert user.display_name == "Test User"
    assert user.id is not None
    assert user.is_active


def test_create_duplicate_user(clean_db):
    """Test creating user with duplicate username/email fails"""
    user_data = UserCreate(
        username="testuser", email="test@example.com", password="password123", display_name="Test User"
    )

    # Create first user
    user1 = AuthService.create_user(user_data)
    assert user1 is not None

    # Try to create duplicate
    user2 = AuthService.create_user(user_data)
    assert user2 is None


def test_authenticate_user_success(clean_db):
    """Test successful user authentication"""
    # Create user first
    user_data = UserCreate(
        username="testuser", email="test@example.com", password="password123", display_name="Test User"
    )
    created_user = AuthService.create_user(user_data)
    assert created_user is not None

    # Test authentication
    login_data = UserLogin(username="testuser", password="password123")
    auth_user = AuthService.authenticate_user(login_data)

    assert auth_user is not None
    assert auth_user.id == created_user.id
    assert auth_user.username == "testuser"
    assert auth_user.last_login is not None


def test_authenticate_wrong_password(clean_db):
    """Test authentication with wrong password fails"""
    # Create user first
    user_data = UserCreate(
        username="testuser", email="test@example.com", password="password123", display_name="Test User"
    )
    AuthService.create_user(user_data)

    # Try wrong password
    login_data = UserLogin(username="testuser", password="wrongpassword")
    auth_user = AuthService.authenticate_user(login_data)

    assert auth_user is None


def test_authenticate_nonexistent_user(clean_db):
    """Test authentication with nonexistent user fails"""
    login_data = UserLogin(username="nonexistent", password="password123")
    auth_user = AuthService.authenticate_user(login_data)

    assert auth_user is None


def test_get_user_by_id(clean_db):
    """Test getting user by ID"""
    user_data = UserCreate(
        username="testuser", email="test@example.com", password="password123", display_name="Test User"
    )
    created_user = AuthService.create_user(user_data)
    assert created_user is not None
    assert created_user.id is not None

    # Get user by ID
    retrieved_user = AuthService.get_user_by_id(created_user.id)
    assert retrieved_user is not None
    assert retrieved_user.id == created_user.id
    assert retrieved_user.username == "testuser"


def test_get_user_by_id_nonexistent(clean_db):
    """Test getting nonexistent user returns None"""
    user = AuthService.get_user_by_id(999)
    assert user is None


def test_get_user_by_username(clean_db):
    """Test getting user by username"""
    user_data = UserCreate(
        username="testuser", email="test@example.com", password="password123", display_name="Test User"
    )
    created_user = AuthService.create_user(user_data)
    assert created_user is not None

    # Get user by username
    retrieved_user = AuthService.get_user_by_username("testuser")
    assert retrieved_user is not None
    assert retrieved_user.id == created_user.id
    assert retrieved_user.username == "testuser"


def test_get_user_by_username_nonexistent(clean_db):
    """Test getting nonexistent username returns None"""
    user = AuthService.get_user_by_username("nonexistent")
    assert user is None


def test_password_hashing():
    """Test password hashing and verification"""
    password = "test_password_123"

    # Hash password
    hash1 = AuthService.hash_password(password)
    hash2 = AuthService.hash_password(password)

    # Hashes should be different (due to random salt)
    assert hash1 != hash2

    # Both should verify correctly
    assert AuthService.verify_password(password, hash1)
    assert AuthService.verify_password(password, hash2)

    # Wrong password should fail
    assert not AuthService.verify_password("wrong_password", hash1)


def test_verify_invalid_hash():
    """Test password verification with invalid hash format"""
    assert not AuthService.verify_password("password", "invalid_hash_format")
    assert not AuthService.verify_password("password", "no_colon")
    assert not AuthService.verify_password("password", "")
