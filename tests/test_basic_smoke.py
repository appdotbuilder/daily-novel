"""
Basic smoke tests to verify core functionality works
"""

from app.database import reset_db
from app.services.auth_service import AuthService
from app.models import UserCreate


def test_basic_smoke():
    """Basic smoke test that core services work"""
    reset_db()

    # Test user creation
    user_data = UserCreate(
        username="smoketest", email="smoke@test.com", password="password123", display_name="Smoke Test User"
    )

    user = AuthService.create_user(user_data)
    assert user is not None
    assert user.username == "smoketest"

    # Test authentication
    from app.models import UserLogin

    login_data = UserLogin(username="smoketest", password="password123")
    auth_user = AuthService.authenticate_user(login_data)
    assert auth_user is not None
    assert auth_user.id == user.id

    reset_db()
