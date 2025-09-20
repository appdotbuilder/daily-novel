from nicegui import ui, app
from datetime import date
import logging
from app.ui.auth_module import AuthModule
from app.services.wikipedia_service import WikipediaService
from app.services.entry_service import EntryService
from app.models import DailyEntryCreate, DailyEntryUpdate, WikipediaImage

logger = logging.getLogger(__name__)


class DashboardModule:
    """Main dashboard for daily reflections"""

    @staticmethod
    def create_navigation():
        """Create navigation bar"""
        with ui.header().classes("bg-gray-800 text-white p-4"):
            with ui.row().classes("w-full items-center justify-between"):
                ui.link("Daily Reflections", "/dashboard").classes("text-2xl font-bold text-white no-underline")

                with ui.row().classes("gap-4 items-center"):
                    ui.link("Discover", "/discover").classes("text-white hover:text-gray-300 px-3 py-2")
                    ui.link("My Entries", "/profile").classes("text-white hover:text-gray-300 px-3 py-2")
                    ui.link("Messages", "/messages").classes("text-white hover:text-gray-300 px-3 py-2")

                    user_name = app.storage.user.get("display_name", "User")
                    ui.button(f"Sign out ({user_name})", on_click=AuthModule.logout).classes("text-sm").props("flat")

    @staticmethod
    def create_image_display(wiki_image: WikipediaImage):
        """Create Wikipedia image display"""
        with ui.card().classes("novel-card p-6 mb-6"):
            ui.label("Today's Inspiration").classes("text-2xl novel-title mb-4 text-center text-gray-800")

            if wiki_image.image_url:
                ui.image(wiki_image.image_url).classes("w-full max-w-2xl mx-auto rounded-lg shadow-lg")

            ui.label(wiki_image.title).classes("text-xl font-semibold mt-4 text-center text-gray-700")

            if wiki_image.description:
                ui.label(wiki_image.description).classes("text-base text-gray-600 mt-2 text-center leading-relaxed")

            if wiki_image.wikipedia_url:
                with ui.row().classes("justify-center mt-4"):
                    ui.link("Learn more on Wikipedia", wiki_image.wikipedia_url, new_tab=True).classes(
                        "text-blue-600 hover:underline"
                    )

    @staticmethod
    def create_reflection_form(wiki_image: WikipediaImage, existing_entry=None):
        """Create reflection writing form"""
        user_id = AuthModule.get_current_user_id()
        if user_id is None:
            return

        is_editing = existing_entry is not None

        def handle_save():
            try:
                reflection_text = text_area.value.strip()
                if not reflection_text:
                    ui.notify("Please write your reflection before saving", type="warning")
                    return

                is_shared = share_checkbox.value

                if is_editing and existing_entry and existing_entry.id is not None:
                    # Update existing entry
                    update_data = DailyEntryUpdate(reflection_text=reflection_text, is_shared=is_shared)
                    updated_entry = EntryService.update_entry(existing_entry.id, user_id, update_data)
                    if updated_entry:
                        ui.notify("Reflection updated successfully!", type="positive")
                        ui.navigate.reload()
                    else:
                        ui.notify("Failed to update reflection", type="negative")
                else:
                    # Create new entry
                    entry_data = DailyEntryCreate(reflection_text=reflection_text, is_shared=is_shared)

                    if wiki_image.id is not None:
                        new_entry = EntryService.create_entry(
                            user_id=user_id,
                            wikipedia_image_id=wiki_image.id,
                            entry_data=entry_data,
                            entry_date=date.today(),
                        )
                    else:
                        new_entry = None

                    if new_entry:
                        ui.notify("Reflection saved successfully!", type="positive")
                        ui.navigate.reload()
                    else:
                        ui.notify("You have already written a reflection for today", type="warning")

            except Exception as e:
                logger.error(f"Error saving reflection: {e}")
                ui.notify(f"Error saving reflection: {str(e)}", type="negative")

        with ui.card().classes("novel-card p-6"):
            title = "Edit Your Reflection" if is_editing else "Your Daily Reflection"
            ui.label(title).classes("text-2xl novel-title mb-4 text-gray-800")

            initial_text = existing_entry.reflection_text if existing_entry else ""
            initial_shared = existing_entry.is_shared if existing_entry else False

            text_area = (
                ui.textarea(
                    label="Write your thoughts...",
                    placeholder="What does this image inspire in you? Share your thoughts, feelings, or memories...",
                    value=initial_text,
                )
                .classes("w-full mb-4")
                .props("rows=8 outlined")
            )

            with ui.row().classes("items-center gap-4 mb-4"):
                share_checkbox = ui.checkbox("Share with community", value=initial_shared).classes("text-gray-700")
                ui.label("Others will be able to see and like your reflection").classes("text-sm text-gray-500")

            button_text = "Update Reflection" if is_editing else "Save Reflection"
            ui.button(button_text, on_click=handle_save).classes("novel-button px-6 py-2 rounded")

    @staticmethod
    def create_existing_entry_display(entry):
        """Display existing entry for today"""
        with ui.card().classes("novel-card p-6"):
            ui.label("Today's Reflection").classes("text-2xl novel-title mb-4 text-gray-800")

            ui.label(entry.reflection_text).classes("text-base text-gray-700 mb-4 leading-relaxed whitespace-pre-wrap")

            with ui.row().classes("items-center justify-between"):
                status_text = "Shared with community" if entry.is_shared else "Private reflection"
                status_color = "text-green-600" if entry.is_shared else "text-gray-500"
                ui.label(status_text).classes(f"text-sm {status_color}")

                ui.button("Edit", on_click=lambda: ui.navigate.reload()).classes("text-sm").props("outlined")


async def create_dashboard_content():
    """Create main dashboard content"""
    user_id = AuthModule.get_current_user_id()
    if user_id is None:
        ui.navigate.to("/login")
        return

    today = date.today()

    # Get or fetch today's Wikipedia image
    wiki_image = await WikipediaService.get_or_create_daily_image(today)
    if wiki_image is None:
        with ui.card().classes("novel-card p-6 text-center"):
            ui.label("Unable to load today's image").classes("text-xl text-gray-600")
            ui.label("Please check your internet connection and try again.").classes("text-base text-gray-500 mt-2")
        return

    # Check if user has already written entry for today
    existing_entry = EntryService.get_user_entry_for_date(user_id, today)

    # Create layout
    with ui.column().classes("max-w-4xl mx-auto p-6 gap-6"):
        DashboardModule.create_image_display(wiki_image)

        if existing_entry:
            DashboardModule.create_existing_entry_display(existing_entry)
        else:
            DashboardModule.create_reflection_form(wiki_image)


def create():
    """Create dashboard routes"""

    @ui.page("/dashboard")
    async def dashboard_page():
        if not AuthModule.is_authenticated():
            ui.navigate.to("/login")
            return

        DashboardModule.create_navigation()

        # Create main content with loading state
        with ui.column().classes("min-h-screen bg-gray-50"):
            content_area = ui.column().classes("flex-1")

            with content_area:
                ui.label("Loading today's inspiration...").classes("text-center text-gray-600 mt-8")
                ui.spinner(size="lg").classes("mx-auto mt-4")

            # Load content asynchronously
            async def load_content():
                content_area.clear()
                with content_area:
                    await create_dashboard_content()

            # Schedule content loading
            ui.timer(0.1, load_content, once=True)
