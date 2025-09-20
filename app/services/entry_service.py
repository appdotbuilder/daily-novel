from typing import Optional, List
from datetime import date, datetime
from sqlmodel import select, func, desc
from app.database import get_session
from app.models import (
    DailyEntry,
    User,
    WikipediaImage,
    ReflectionLike,
    DailyEntryCreate,
    DailyEntryUpdate,
    DailyEntryResponse,
)


class EntryService:
    """Service for managing daily entries and reflections"""

    @staticmethod
    def create_entry(
        user_id: int, wikipedia_image_id: int, entry_data: DailyEntryCreate, entry_date: date
    ) -> Optional[DailyEntry]:
        """Create a new daily entry"""
        with get_session() as session:
            # Check if user already has an entry for this date
            existing_entry = session.exec(
                select(DailyEntry).where(DailyEntry.author_id == user_id, DailyEntry.entry_date == entry_date)
            ).first()

            if existing_entry:
                return None  # User already has entry for today

            entry = DailyEntry(
                author_id=user_id,
                wikipedia_image_id=wikipedia_image_id,
                entry_date=entry_date,
                reflection_text=entry_data.reflection_text,
                is_shared=entry_data.is_shared,
            )

            session.add(entry)
            session.commit()
            session.refresh(entry)
            return entry

    @staticmethod
    def update_entry(entry_id: int, user_id: int, update_data: DailyEntryUpdate) -> Optional[DailyEntry]:
        """Update an existing entry (only by its author)"""
        with get_session() as session:
            entry = session.get(DailyEntry, entry_id)
            if entry is None or entry.author_id != user_id:
                return None

            if update_data.reflection_text is not None:
                entry.reflection_text = update_data.reflection_text
            if update_data.is_shared is not None:
                entry.is_shared = update_data.is_shared

            entry.updated_at = datetime.utcnow()
            session.add(entry)
            session.commit()
            session.refresh(entry)
            return entry

    @staticmethod
    def get_user_entry_for_date(user_id: int, entry_date: date) -> Optional[DailyEntry]:
        """Get user's entry for a specific date"""
        with get_session() as session:
            return session.exec(
                select(DailyEntry).where(DailyEntry.author_id == user_id, DailyEntry.entry_date == entry_date)
            ).first()

    @staticmethod
    def get_user_entries_history(user_id: int, limit: int = 50) -> List[DailyEntryResponse]:
        """Get user's entry history with Wikipedia images"""
        with get_session() as session:
            query = (
                select(DailyEntry, User, WikipediaImage)
                .join(User)
                .join(WikipediaImage)
                .where(DailyEntry.author_id == user_id)
                .order_by(desc(DailyEntry.entry_date))
                .limit(limit)
            )

            results = session.exec(query).all()
            entries = []

            for entry, user, image in results:
                # Count likes for each entry
                entry_id = entry.id if entry.id is not None else 0
                likes_count = session.exec(select(func.count()).where(ReflectionLike.daily_entry_id == entry_id)).one()

                entries.append(
                    DailyEntryResponse(
                        id=entry.id if entry.id is not None else 0,
                        entry_date=entry.entry_date.isoformat(),
                        reflection_text=entry.reflection_text,
                        is_shared=entry.is_shared,
                        author_display_name=user.display_name,
                        wikipedia_image_title=image.title,
                        wikipedia_image_url=image.image_url,
                        likes_count=likes_count,
                        created_at=entry.created_at.isoformat(),
                    )
                )

            return entries

    @staticmethod
    def get_shared_entries(limit: int = 50, offset: int = 0) -> List[DailyEntryResponse]:
        """Get shared entries from all users"""
        with get_session() as session:
            query = (
                select(DailyEntry, User, WikipediaImage)
                .join(User)
                .join(WikipediaImage)
                .where(DailyEntry.is_shared == True)  # noqa: E712
                .order_by(desc(DailyEntry.created_at))
                .offset(offset)
                .limit(limit)
            )

            results = session.exec(query).all()
            entries = []

            for entry, user, image in results:
                # Count likes for each entry
                entry_id = entry.id if entry.id is not None else 0
                likes_count = session.exec(select(func.count()).where(ReflectionLike.daily_entry_id == entry_id)).one()

                entries.append(
                    DailyEntryResponse(
                        id=entry.id if entry.id is not None else 0,
                        entry_date=entry.entry_date.isoformat(),
                        reflection_text=entry.reflection_text,
                        is_shared=entry.is_shared,
                        author_display_name=user.display_name,
                        wikipedia_image_title=image.title,
                        wikipedia_image_url=image.image_url,
                        likes_count=likes_count,
                        created_at=entry.created_at.isoformat(),
                    )
                )

            return entries

    @staticmethod
    def get_entry_by_id(entry_id: int) -> Optional[DailyEntry]:
        """Get entry by ID"""
        with get_session() as session:
            return session.get(DailyEntry, entry_id)
