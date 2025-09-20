import httpx
from datetime import date
from typing import Optional, Dict, Any
import logging
from sqlmodel import select
from app.database import get_session
from app.models import WikipediaImage, WikipediaImageCreate

logger = logging.getLogger(__name__)


class WikipediaService:
    """Service for fetching and managing Wikipedia Image of the Day"""

    BASE_URL = "https://en.wikipedia.org/api/rest_v1"

    @staticmethod
    async def fetch_image_of_day(target_date: date) -> Optional[Dict[str, Any]]:
        """Fetch Wikipedia's Image of the Day for a specific date"""
        try:
            # Format date for Wikipedia API (YYYY/MM/DD)
            date_str = target_date.strftime("%Y/%m/%d")

            async with httpx.AsyncClient(timeout=10.0) as client:
                # First, get the featured content for the date
                featured_url = f"{WikipediaService.BASE_URL}/feed/featured/{date_str}"
                response = await client.get(featured_url)
                response.raise_for_status()

                data = response.json()

                # Extract image information
                if "image" in data and data["image"]:
                    image_data = data["image"]
                    return {
                        "title": image_data.get("title", "Unknown Image"),
                        "description": image_data.get("description", {}).get("text", ""),
                        "image_url": image_data.get("image", {}).get("source", ""),
                        "wikipedia_url": image_data.get("content_urls", {}).get("desktop", {}).get("page", ""),
                    }

                return None

        except Exception as e:
            logger.error(f"Failed to fetch Wikipedia image for {target_date}: {e}")
            return None

    @staticmethod
    def get_or_fetch_daily_image(target_date: date) -> Optional[WikipediaImage]:
        """Get cached image or fetch from Wikipedia API"""
        with get_session() as session:
            # Check if we already have this image
            existing_image = session.exec(
                select(WikipediaImage).where(WikipediaImage.image_date == target_date)
            ).first()

            if existing_image:
                return existing_image

            # Need to fetch from Wikipedia - this requires async context
            return None

    @staticmethod
    def store_daily_image(image_data: WikipediaImageCreate) -> Optional[WikipediaImage]:
        """Store a Wikipedia image in the database"""
        try:
            with get_session() as session:
                # Check if image already exists for this date
                existing = session.exec(
                    select(WikipediaImage).where(WikipediaImage.image_date == image_data.date)
                ).first()

                if existing:
                    return existing

                # Create new image record
                wiki_image = WikipediaImage(
                    image_date=image_data.date,
                    title=image_data.title,
                    description=image_data.description,
                    image_url=image_data.image_url,
                    wikipedia_url=image_data.wikipedia_url,
                )

                session.add(wiki_image)
                session.commit()
                session.refresh(wiki_image)
                return wiki_image

        except Exception as e:
            logger.error(f"Failed to store Wikipedia image: {e}")
            return None

    @staticmethod
    async def get_or_create_daily_image(target_date: date) -> Optional[WikipediaImage]:
        """Get cached image or fetch and store from Wikipedia"""
        # First try to get from database
        existing = WikipediaService.get_or_fetch_daily_image(target_date)
        if existing:
            return existing

        # Fetch from Wikipedia API
        image_data = await WikipediaService.fetch_image_of_day(target_date)
        if image_data is None:
            return None

        # Store in database
        create_data = WikipediaImageCreate(
            date=target_date,
            title=image_data["title"],
            description=image_data["description"],
            image_url=image_data["image_url"],
            wikipedia_url=image_data["wikipedia_url"],
        )

        return WikipediaService.store_daily_image(create_data)
