from typing import Optional
from datetime import datetime
import hashlib
import secrets
import logging
from sqlmodel import select
from app.database import get_session
from app.models import User, UserCreate, UserLogin

logger = logging.getLogger(__name__)


class AuthService:
    """Authentication service handling user registration and login"""

    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a password with a random salt"""
        salt = secrets.token_hex(32)
        password_hash = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100000)
        return f"{salt}:{password_hash.hex()}"

    @staticmethod
    def verify_password(password: str, password_hash: str) -> bool:
        """Verify a password against its hash"""
        try:
            salt, stored_hash = password_hash.split(":")
            password_hash_computed = hashlib.pbkdf2_hmac(
                "sha256", password.encode("utf-8"), salt.encode("utf-8"), 100000
            )
            return stored_hash == password_hash_computed.hex()
        except (ValueError, TypeError) as e:
            logger.error(f"Password verification failed: {e}")
            return False

    @staticmethod
    def create_user(user_data: UserCreate) -> Optional[User]:
        """Create a new user account"""
        with get_session() as session:
            # Check if username or email already exists
            existing_user = session.exec(
                select(User).where((User.username == user_data.username) | (User.email == user_data.email))
            ).first()

            if existing_user:
                return None

            # Create new user
            password_hash = AuthService.hash_password(user_data.password)
            user = User(
                username=user_data.username,
                email=user_data.email,
                password_hash=password_hash,
                display_name=user_data.display_name,
            )

            session.add(user)
            session.commit()
            session.refresh(user)
            return user

    @staticmethod
    def authenticate_user(login_data: UserLogin) -> Optional[User]:
        """Authenticate a user with username/password"""
        with get_session() as session:
            user = session.exec(select(User).where(User.username == login_data.username)).first()

            if user is None:
                return None

            if not AuthService.verify_password(login_data.password, user.password_hash):
                return None

            # Update last login
            user.last_login = datetime.utcnow()
            session.add(user)
            session.commit()
            session.refresh(user)

            return user

    @staticmethod
    def get_user_by_id(user_id: int) -> Optional[User]:
        """Get user by ID"""
        with get_session() as session:
            return session.get(User, user_id)

    @staticmethod
    def get_user_by_username(username: str) -> Optional[User]:
        """Get user by username"""
        with get_session() as session:
            return session.exec(select(User).where(User.username == username)).first()
