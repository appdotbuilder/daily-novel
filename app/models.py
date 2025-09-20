from sqlmodel import SQLModel, Field, Relationship
from datetime import datetime, date
from typing import Optional, List
from enum import Enum


# Enums for better type safety
class MessageStatus(str, Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    DECLINED = "declined"


class ConversationStatus(str, Enum):
    ACTIVE = "active"
    ARCHIVED = "archived"
    BLOCKED = "blocked"


# Persistent models (stored in database)
class User(SQLModel, table=True):
    __tablename__ = "users"  # type: ignore[assignment]

    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(unique=True, max_length=50, regex=r"^[a-zA-Z0-9_-]+$")
    email: str = Field(unique=True, max_length=255, regex=r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")
    password_hash: str = Field(max_length=255)
    display_name: str = Field(max_length=100)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_login: Optional[datetime] = Field(default=None)

    # Relationships
    daily_entries: List["DailyEntry"] = Relationship(back_populates="author")
    likes_given: List["ReflectionLike"] = Relationship(back_populates="user")
    sent_contact_requests: List["ContactRequest"] = Relationship(
        back_populates="sender", sa_relationship_kwargs={"foreign_keys": "ContactRequest.sender_id"}
    )
    received_contact_requests: List["ContactRequest"] = Relationship(
        back_populates="recipient", sa_relationship_kwargs={"foreign_keys": "ContactRequest.recipient_id"}
    )
    conversations_as_user1: List["Conversation"] = Relationship(
        back_populates="user1", sa_relationship_kwargs={"foreign_keys": "Conversation.user1_id"}
    )
    conversations_as_user2: List["Conversation"] = Relationship(
        back_populates="user2", sa_relationship_kwargs={"foreign_keys": "Conversation.user2_id"}
    )
    direct_messages_sent: List["DirectMessage"] = Relationship(back_populates="sender")


class WikipediaImage(SQLModel, table=True):
    __tablename__ = "wikipedia_images"  # type: ignore[assignment]

    id: Optional[int] = Field(default=None, primary_key=True)
    image_date: date = Field(unique=True, index=True)
    title: str = Field(max_length=500)
    description: str = Field(default="")
    image_url: str = Field(max_length=1000)
    wikipedia_url: str = Field(max_length=1000)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    daily_entries: List["DailyEntry"] = Relationship(back_populates="wikipedia_image")


class DailyEntry(SQLModel, table=True):
    __tablename__ = "daily_entries"  # type: ignore[assignment]

    id: Optional[int] = Field(default=None, primary_key=True)
    author_id: int = Field(foreign_key="users.id")
    wikipedia_image_id: int = Field(foreign_key="wikipedia_images.id")
    entry_date: date = Field(index=True)
    reflection_text: str = Field(max_length=2000)
    is_shared: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    author: User = Relationship(back_populates="daily_entries")
    wikipedia_image: WikipediaImage = Relationship(back_populates="daily_entries")
    likes: List["ReflectionLike"] = Relationship(back_populates="daily_entry")


class ReflectionLike(SQLModel, table=True):
    __tablename__ = "reflection_likes"  # type: ignore[assignment]

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id")
    daily_entry_id: int = Field(foreign_key="daily_entries.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    user: User = Relationship(back_populates="likes_given")
    daily_entry: DailyEntry = Relationship(back_populates="likes")


class ContactRequest(SQLModel, table=True):
    __tablename__ = "contact_requests"  # type: ignore[assignment]

    id: Optional[int] = Field(default=None, primary_key=True)
    sender_id: int = Field(foreign_key="users.id")
    recipient_id: int = Field(foreign_key="users.id")
    daily_entry_id: int = Field(foreign_key="daily_entries.id")  # The entry that prompted the contact
    message: str = Field(max_length=500, default="")
    status: MessageStatus = Field(default=MessageStatus.PENDING)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    responded_at: Optional[datetime] = Field(default=None)

    # Relationships
    sender: User = Relationship(
        back_populates="sent_contact_requests", sa_relationship_kwargs={"foreign_keys": "ContactRequest.sender_id"}
    )
    recipient: User = Relationship(
        back_populates="received_contact_requests",
        sa_relationship_kwargs={"foreign_keys": "ContactRequest.recipient_id"},
    )


class Conversation(SQLModel, table=True):
    __tablename__ = "conversations"  # type: ignore[assignment]

    id: Optional[int] = Field(default=None, primary_key=True)
    user1_id: int = Field(foreign_key="users.id")
    user2_id: int = Field(foreign_key="users.id")
    status: ConversationStatus = Field(default=ConversationStatus.ACTIVE)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_message_at: Optional[datetime] = Field(default=None)

    # Relationships
    user1: User = Relationship(
        back_populates="conversations_as_user1", sa_relationship_kwargs={"foreign_keys": "Conversation.user1_id"}
    )
    user2: User = Relationship(
        back_populates="conversations_as_user2", sa_relationship_kwargs={"foreign_keys": "Conversation.user2_id"}
    )
    messages: List["DirectMessage"] = Relationship(back_populates="conversation")


class DirectMessage(SQLModel, table=True):
    __tablename__ = "direct_messages"  # type: ignore[assignment]

    id: Optional[int] = Field(default=None, primary_key=True)
    conversation_id: int = Field(foreign_key="conversations.id")
    sender_id: int = Field(foreign_key="users.id")
    message_text: str = Field(max_length=1000)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    is_read: bool = Field(default=False)

    # Relationships
    conversation: Conversation = Relationship(back_populates="messages")
    sender: User = Relationship(back_populates="direct_messages_sent")


# Non-persistent schemas (for validation, forms, API requests/responses)
class UserCreate(SQLModel, table=False):
    username: str = Field(max_length=50, regex=r"^[a-zA-Z0-9_-]+$")
    email: str = Field(max_length=255, regex=r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")
    password: str = Field(min_length=8, max_length=100)
    display_name: str = Field(max_length=100)


class UserLogin(SQLModel, table=False):
    username: str = Field(max_length=50)
    password: str = Field(max_length=100)


class UserProfile(SQLModel, table=False):
    id: int
    username: str
    display_name: str
    created_at: str  # ISO format string


class DailyEntryCreate(SQLModel, table=False):
    reflection_text: str = Field(max_length=2000)
    is_shared: bool = Field(default=False)


class DailyEntryUpdate(SQLModel, table=False):
    reflection_text: Optional[str] = Field(default=None, max_length=2000)
    is_shared: Optional[bool] = Field(default=None)


class DailyEntryResponse(SQLModel, table=False):
    id: int
    entry_date: str  # ISO format
    reflection_text: str
    is_shared: bool
    author_display_name: str
    wikipedia_image_title: str
    wikipedia_image_url: str
    likes_count: int
    created_at: str  # ISO format


class WikipediaImageCreate(SQLModel, table=False):
    date: date
    title: str = Field(max_length=500)
    description: str = Field(default="")
    image_url: str = Field(max_length=1000)
    wikipedia_url: str = Field(max_length=1000)


class ContactRequestCreate(SQLModel, table=False):
    recipient_id: int
    daily_entry_id: int
    message: str = Field(max_length=500, default="")


class ContactRequestResponse(SQLModel, table=False):
    status: MessageStatus


class DirectMessageCreate(SQLModel, table=False):
    conversation_id: int
    message_text: str = Field(max_length=1000)


class DirectMessageResponse(SQLModel, table=False):
    id: int
    sender_display_name: str
    message_text: str
    created_at: str  # ISO format
    is_read: bool


class ConversationResponse(SQLModel, table=False):
    id: int
    other_user_display_name: str
    last_message_at: Optional[str]  # ISO format
    unread_count: int
