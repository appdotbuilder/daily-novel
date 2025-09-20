from nicegui import ui
from typing import List
import logging
from app.ui.auth_module import AuthModule
from app.ui.dashboard_module import DashboardModule
from app.services.entry_service import EntryService
from app.services.social_service import SocialService
from app.models import DailyEntryResponse, ContactRequestCreate

logger = logging.getLogger(__name__)


class DiscoverModule:
    """Module for discovering and interacting with shared reflections"""

    @staticmethod
    def create_shared_entry_card(entry: DailyEntryResponse, current_user_id: int):
        """Create a card displaying a shared reflection"""

        def handle_like():
            try:
                is_liked = SocialService.toggle_like(current_user_id, entry.id)

                # Update button appearance based on like status
                if is_liked:
                    like_button.text = "❤️ Liked"
                    like_button.classes("text-sm bg-red-50 text-red-600 border-red-200")
                    like_button.props("outlined")
                    # Show contact button when user likes
                    if "contact_button" not in locals():
                        contact_button = (
                            ui.button("✉️ Contact", on_click=handle_contact).classes("text-sm").props("outlined")
                        )
                else:
                    like_button.text = "🤍 Like"
                    like_button.classes("text-sm hover:bg-gray-50")
                    like_button.props("flat")
                    # Hide contact button when user unlikes (requires page refresh for full effect)

                # Update likes count
                new_count = SocialService.get_entry_likes_count(entry.id)
                likes_label.text = f"{new_count} likes" if new_count != 1 else "1 like"

                ui.notify("Liked!" if is_liked else "Like removed", type="positive")

            except Exception as e:
                logger.error(f"Error in social action: {e}")
                ui.notify(f"Error: {str(e)}", type="negative")

        async def handle_contact():
            """Handle contact request after liking"""
            try:
                # Check if user has liked this entry
                has_liked = SocialService.user_has_liked_entry(current_user_id, entry.id)
                if not has_liked:
                    ui.notify("Please like this reflection first to request contact", type="warning")
                    return

                # Show contact request dialog
                with ui.dialog() as dialog, ui.card().classes("p-6 min-w-96"):
                    ui.label("Request Contact").classes("text-xl font-bold mb-4")
                    ui.label(f"Send a message to {entry.author_display_name}").classes("text-gray-600 mb-4")

                    message_input = ui.textarea(
                        label="Your message (optional)",
                        placeholder="Hi! I loved your reflection and would like to connect...",
                    ).classes("w-full mb-4")

                    with ui.row().classes("gap-2 justify-end"):
                        ui.button("Cancel", on_click=lambda: dialog.submit(None)).props("flat")
                        ui.button("Send Request", on_click=lambda: dialog.submit(message_input.value)).classes(
                            "novel-button"
                        )

                result = await dialog
                if result is not None:
                    # Get the author ID by looking up the entry
                    entry_obj = EntryService.get_entry_by_id(entry.id)
                    if entry_obj is None:
                        ui.notify("Entry not found", type="negative")
                        return

                    request_data = ContactRequestCreate(
                        recipient_id=entry_obj.author_id, daily_entry_id=entry.id, message=result
                    )

                    contact_request = SocialService.send_contact_request(current_user_id, request_data)
                    if contact_request:
                        ui.notify("Contact request sent!", type="positive")
                        contact_button.set_enabled(False)
                        contact_button.text = "Request Sent"
                    else:
                        ui.notify("Failed to send contact request", type="negative")

            except Exception as e:
                logger.error(f"Error in social action: {e}")
                ui.notify(f"Error: {str(e)}", type="negative")

        with ui.card().classes("novel-card p-6 mb-6"):
            # Header with author and date
            with ui.row().classes("items-center justify-between mb-4"):
                ui.label(entry.author_display_name).classes("font-semibold text-gray-800")
                ui.label(entry.entry_date).classes("text-sm text-gray-500")

            # Wikipedia image info
            if entry.wikipedia_image_url:
                ui.image(entry.wikipedia_image_url).classes("w-full max-w-md mx-auto rounded mb-4")
            ui.label(entry.wikipedia_image_title).classes("text-sm text-gray-600 italic mb-4 text-center")

            # Reflection text
            ui.label(entry.reflection_text).classes("text-base text-gray-700 leading-relaxed mb-4 whitespace-pre-wrap")

            # Action buttons and stats
            with ui.row().classes("items-center justify-between"):
                with ui.row().classes("gap-2 items-center"):
                    # Like button - only show if user hasn't liked yet, or show "Liked" status
                    user_has_liked = SocialService.user_has_liked_entry(current_user_id, entry.id)

                    if user_has_liked:
                        # Show "Liked" status button (can click to unlike)
                        like_button = (
                            ui.button("❤️ Liked", on_click=handle_like)
                            .classes("text-sm bg-red-50 text-red-600 border-red-200")
                            .props("outlined")
                        )
                    else:
                        # Show "Like" button
                        like_button = (
                            ui.button("🤍 Like", on_click=handle_like).classes("text-sm hover:bg-gray-50").props("flat")
                        )

                    # Contact button - only show if user has liked the entry
                    if user_has_liked:
                        contact_button = (
                            ui.button("✉️ Contact", on_click=handle_contact).classes("text-sm").props("outlined")
                        )

                with ui.column().classes("text-right"):
                    likes_count_text = f"{entry.likes_count} likes" if entry.likes_count != 1 else "1 like"
                    likes_label = ui.label(likes_count_text).classes("text-sm text-gray-500")

    @staticmethod
    def create_discovery_feed(entries: List[DailyEntryResponse], current_user_id: int):
        """Create feed of shared reflections"""
        if not entries:
            with ui.card().classes("novel-card p-8 text-center"):
                ui.label("No shared reflections yet").classes("text-xl text-gray-600")
                ui.label("Be the first to share your daily reflection with the community!").classes(
                    "text-base text-gray-500 mt-2"
                )
            return

        ui.label("Community Reflections").classes("text-3xl novel-title mb-6 text-gray-800")

        for entry in entries:
            DiscoverModule.create_shared_entry_card(entry, current_user_id)


def create():
    """Create discover routes"""

    @ui.page("/discover")
    def discover_page():
        if not AuthModule.is_authenticated():
            ui.navigate.to("/login")
            return

        user_id = AuthModule.get_current_user_id()
        if user_id is None:
            ui.navigate.to("/login")
            return

        DashboardModule.create_navigation()

        with ui.column().classes("min-h-screen bg-gray-50"):
            with ui.column().classes("max-w-4xl mx-auto p-6"):
                # Get shared entries
                shared_entries = EntryService.get_shared_entries(limit=20)
                DiscoverModule.create_discovery_feed(shared_entries, user_id)
