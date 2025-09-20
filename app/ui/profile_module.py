from nicegui import ui, app
from typing import List
from app.ui.auth_module import AuthModule
from app.ui.dashboard_module import DashboardModule
from app.services.entry_service import EntryService
from app.models import DailyEntryResponse


class ProfileModule:
    """User profile and history module"""

    @staticmethod
    def create_user_stats(entries: List[DailyEntryResponse]):
        """Create user statistics display"""
        total_entries = len(entries)
        shared_entries = sum(1 for entry in entries if entry.is_shared)
        total_likes = sum(entry.likes_count for entry in entries)

        with ui.card().classes("novel-card p-6 mb-6"):
            user_name = app.storage.user.get("display_name", "User")
            ui.label(f"{user_name}'s Journal").classes("text-3xl novel-title mb-4 text-gray-800")

            with ui.row().classes("gap-8 justify-center"):
                with ui.column().classes("text-center"):
                    ui.label(str(total_entries)).classes("text-2xl font-bold text-blue-600")
                    ui.label("Total Reflections").classes("text-sm text-gray-600")

                with ui.column().classes("text-center"):
                    ui.label(str(shared_entries)).classes("text-2xl font-bold text-green-600")
                    ui.label("Shared").classes("text-sm text-gray-600")

                with ui.column().classes("text-center"):
                    ui.label(str(total_likes)).classes("text-2xl font-bold text-red-500")
                    ui.label("Total Likes").classes("text-sm text-gray-600")

    @staticmethod
    def create_entry_history_card(entry: DailyEntryResponse):
        """Create a card for user's past entry"""
        with ui.card().classes("novel-card p-6 mb-4"):
            # Header with date and sharing status
            with ui.row().classes("items-center justify-between mb-4"):
                ui.label(entry.entry_date).classes("font-semibold text-gray-800")

                with ui.row().classes("items-center gap-2"):
                    if entry.is_shared:
                        ui.icon("public", color="green").classes("text-sm")
                        ui.label("Shared").classes("text-sm text-green-600")
                        ui.label(f"{entry.likes_count} ❤️").classes("text-sm text-gray-500 ml-2")
                    else:
                        ui.icon("lock", color="gray").classes("text-sm")
                        ui.label("Private").classes("text-sm text-gray-500")

            # Wikipedia image info
            ui.label(entry.wikipedia_image_title).classes("text-sm text-blue-600 italic mb-2")

            # Reflection preview (truncated)
            reflection_preview = (
                entry.reflection_text[:200] + "..." if len(entry.reflection_text) > 200 else entry.reflection_text
            )
            ui.label(reflection_preview).classes("text-base text-gray-700 leading-relaxed whitespace-pre-wrap")

            # Show full text button if truncated
            if len(entry.reflection_text) > 200:

                def show_full_text():
                    # Replace preview with full text
                    reflection_label.text = entry.reflection_text
                    show_more_button.set_visibility(False)

                reflection_label = ui.label(reflection_preview).classes(
                    "text-base text-gray-700 leading-relaxed whitespace-pre-wrap"
                )
                show_more_button = (
                    ui.button("Show more...", on_click=show_full_text).classes("text-sm mt-2").props("flat")
                )

    @staticmethod
    def create_entry_history(entries: List[DailyEntryResponse]):
        """Create history of user's entries"""
        if not entries:
            with ui.card().classes("novel-card p-8 text-center"):
                ui.label("No reflections yet").classes("text-xl text-gray-600")
                ui.label("Start your journey by writing your first daily reflection!").classes(
                    "text-base text-gray-500 mt-2"
                )
                ui.button("Write First Reflection", on_click=lambda: ui.navigate.to("/dashboard")).classes(
                    "novel-button mt-4 px-6 py-2"
                )
            return

        ui.label("Your Reflections").classes("text-2xl novel-title mb-4 text-gray-800")

        for entry in entries:
            ProfileModule.create_entry_history_card(entry)


def create():
    """Create profile routes"""

    @ui.page("/profile")
    def profile_page():
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
                # Get user's entry history
                user_entries = EntryService.get_user_entries_history(user_id, limit=50)

                # Create stats and history display
                ProfileModule.create_user_stats(user_entries)
                ProfileModule.create_entry_history(user_entries)
