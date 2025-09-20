from typing import Optional, List
from datetime import datetime
from sqlmodel import Session, select, func, or_, desc
from app.database import get_session
from app.models import (
    ReflectionLike,
    ContactRequest,
    Conversation,
    DirectMessage,
    User,
    DailyEntry,
    ContactRequestCreate,
    DirectMessageCreate,
    DirectMessageResponse,
    ConversationResponse,
    MessageStatus,
)


class SocialService:
    """Service for managing social interactions: likes, contact requests, direct messages"""

    # Likes functionality
    @staticmethod
    def toggle_like(user_id: int, entry_id: int) -> bool:
        """Toggle a like on a daily entry. Returns True if liked, False if unliked"""
        with get_session() as session:
            # Check if entry exists and is shared
            entry = session.get(DailyEntry, entry_id)
            if entry is None or not entry.is_shared or entry.author_id == user_id:
                return False  # Can't like own entry or non-shared entry

            # Check if like already exists
            existing_like = session.exec(
                select(ReflectionLike).where(
                    ReflectionLike.user_id == user_id, ReflectionLike.daily_entry_id == entry_id
                )
            ).first()

            if existing_like:
                # Remove like
                session.delete(existing_like)
                session.commit()
                return False
            else:
                # Add like
                like = ReflectionLike(user_id=user_id, daily_entry_id=entry_id)
                session.add(like)
                session.commit()
                return True

    @staticmethod
    def get_entry_likes_count(entry_id: int) -> int:
        """Get number of likes for an entry"""
        with get_session() as session:
            return session.exec(select(func.count()).where(ReflectionLike.daily_entry_id == entry_id)).one()

    @staticmethod
    def user_has_liked_entry(user_id: int, entry_id: int) -> bool:
        """Check if user has liked a specific entry"""
        with get_session() as session:
            like = session.exec(
                select(ReflectionLike).where(
                    ReflectionLike.user_id == user_id, ReflectionLike.daily_entry_id == entry_id
                )
            ).first()
            return like is not None

    # Contact requests functionality
    @staticmethod
    def send_contact_request(sender_id: int, request_data: ContactRequestCreate) -> Optional[ContactRequest]:
        """Send a contact request to another user"""
        with get_session() as session:
            # Verify entry exists, is shared, and sender has liked it
            entry = session.get(DailyEntry, request_data.daily_entry_id)
            if entry is None or not entry.is_shared or entry.author_id != request_data.recipient_id:
                return None

            # Check if sender has liked this entry
            has_liked = SocialService.user_has_liked_entry(sender_id, request_data.daily_entry_id)
            if not has_liked:
                return None  # Must like entry before sending contact request

            # Check if request already exists
            existing_request = session.exec(
                select(ContactRequest).where(
                    ContactRequest.sender_id == sender_id,
                    ContactRequest.recipient_id == request_data.recipient_id,
                    ContactRequest.daily_entry_id == request_data.daily_entry_id,
                )
            ).first()

            if existing_request:
                return existing_request  # Request already exists

            # Create new contact request
            contact_request = ContactRequest(
                sender_id=sender_id,
                recipient_id=request_data.recipient_id,
                daily_entry_id=request_data.daily_entry_id,
                message=request_data.message,
            )

            session.add(contact_request)
            session.commit()
            session.refresh(contact_request)
            return contact_request

    @staticmethod
    def respond_to_contact_request(request_id: int, recipient_id: int, accept: bool) -> Optional[ContactRequest]:
        """Respond to a contact request (accept or decline)"""
        with get_session() as session:
            request = session.get(ContactRequest, request_id)
            if request is None or request.recipient_id != recipient_id:
                return None

            # Update request status
            request.status = MessageStatus.ACCEPTED if accept else MessageStatus.DECLINED
            request.responded_at = datetime.utcnow()
            session.add(request)

            # If accepted, create conversation
            if accept:
                SocialService._create_conversation(request.sender_id, recipient_id, session)

            session.commit()
            session.refresh(request)
            return request

    @staticmethod
    def get_pending_contact_requests(user_id: int) -> List[ContactRequest]:
        """Get pending contact requests for a user"""
        with get_session() as session:
            # Get requests with eager loading of sender to avoid detached instance issues
            query = (
                select(ContactRequest)
                .where(ContactRequest.recipient_id == user_id, ContactRequest.status == MessageStatus.PENDING)
                .order_by(desc(ContactRequest.created_at))
            )
            requests = session.exec(query).all()

            # Force load sender relationships while session is active
            for request in requests:
                if request.sender:
                    _ = request.sender.display_name  # Access to force loading

            return list(requests)

    # Direct messaging functionality
    @staticmethod
    def _create_conversation(user1_id: int, user2_id: int, session: Session) -> Optional[Conversation]:
        """Create a new conversation between two users"""
        # Ensure consistent ordering of user IDs
        if user1_id > user2_id:
            user1_id, user2_id = user2_id, user1_id

        # Check if conversation already exists
        existing = session.exec(
            select(Conversation).where(Conversation.user1_id == user1_id, Conversation.user2_id == user2_id)
        ).first()

        if existing:
            return existing

        # Create new conversation
        conversation = Conversation(user1_id=user1_id, user2_id=user2_id)
        session.add(conversation)
        session.flush()  # Get ID without committing
        return conversation

    @staticmethod
    def get_user_conversations(user_id: int) -> List[ConversationResponse]:
        """Get all conversations for a user"""
        with get_session() as session:
            # Get conversations where user is either user1 or user2
            query = select(Conversation).where(or_(Conversation.user1_id == user_id, Conversation.user2_id == user_id))

            conversations = session.exec(query).all()
            results = []

            for conv in conversations:
                # Get the other user
                other_user_id = conv.user2_id if conv.user1_id == user_id else conv.user1_id
                other_user = session.get(User, other_user_id)
                if other_user is None:
                    continue

                # Count unread messages from the other user
                conv_id = conv.id if conv.id is not None else 0
                unread_count = session.exec(
                    select(func.count()).where(
                        DirectMessage.conversation_id == conv_id,
                        DirectMessage.sender_id != user_id,
                        DirectMessage.is_read == False,  # noqa: E712
                    )
                ).one()

                results.append(
                    ConversationResponse(
                        id=conv.id if conv.id is not None else 0,
                        other_user_display_name=other_user.display_name,
                        last_message_at=conv.last_message_at.isoformat() if conv.last_message_at else None,
                        unread_count=unread_count,
                    )
                )

            return results

    @staticmethod
    def send_message(sender_id: int, message_data: DirectMessageCreate) -> Optional[DirectMessage]:
        """Send a direct message"""
        with get_session() as session:
            # Verify conversation exists and user is part of it
            conversation = session.get(Conversation, message_data.conversation_id)
            if conversation is None:
                return None

            if sender_id not in [conversation.user1_id, conversation.user2_id]:
                return None  # User not part of conversation

            # Create message
            message = DirectMessage(
                conversation_id=message_data.conversation_id,
                sender_id=sender_id,
                message_text=message_data.message_text,
            )

            session.add(message)

            # Update conversation last message time
            conversation.last_message_at = datetime.utcnow()
            session.add(conversation)

            session.commit()
            session.refresh(message)
            return message

    @staticmethod
    def get_conversation_messages(conversation_id: int, user_id: int, limit: int = 50) -> List[DirectMessageResponse]:
        """Get messages for a conversation"""
        with get_session() as session:
            # Verify user is part of conversation
            conversation = session.get(Conversation, conversation_id)
            if conversation is None or user_id not in [conversation.user1_id, conversation.user2_id]:
                return []

            # Get messages with sender info
            query = (
                select(DirectMessage, User)
                .join(User)
                .where(DirectMessage.conversation_id == conversation_id)
                .order_by(desc(DirectMessage.created_at))
                .limit(limit)
            )

            results = session.exec(query).all()
            messages = []

            for message, sender in results:
                messages.append(
                    DirectMessageResponse(
                        id=message.id if message.id is not None else 0,
                        sender_display_name=sender.display_name,
                        message_text=message.message_text,
                        created_at=message.created_at.isoformat(),
                        is_read=message.is_read,
                    )
                )

            return list(reversed(messages))  # Return in chronological order

    @staticmethod
    def mark_messages_as_read(conversation_id: int, user_id: int) -> bool:
        """Mark all messages from other user in conversation as read"""
        with get_session() as session:
            # Verify user is part of conversation
            conversation = session.get(Conversation, conversation_id)
            if conversation is None or user_id not in [conversation.user1_id, conversation.user2_id]:
                return False

            # Mark messages from other user as read
            messages = session.exec(
                select(DirectMessage).where(
                    DirectMessage.conversation_id == conversation_id,
                    DirectMessage.sender_id != user_id,
                    DirectMessage.is_read == False,  # noqa: E712
                )
            ).all()

            for message in messages:
                message.is_read = True
                session.add(message)

            session.commit()
            return True
