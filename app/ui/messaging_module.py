from nicegui import ui, app
from typing import List
import logging
from app.ui.auth_module import AuthModule
from app.ui.dashboard_module import DashboardModule
from app.services.social_service import SocialService
from app.models import ContactRequest, ConversationResponse, DirectMessageCreate

logger = logging.getLogger(__name__)


class MessagingModule:
    """Direct messaging and contact request handling"""

    @staticmethod
    def create_contact_requests_section(current_user_id: int):
        """Create section for pending contact requests"""
        pending_requests = SocialService.get_pending_contact_requests(current_user_id)

        if not pending_requests:
            return

        ui.label("Contact Requests").classes("text-2xl novel-title mb-4 text-gray-800")

        def handle_request_response(request: ContactRequest, accept: bool):
            try:
                if request.id is None:
                    ui.notify("Invalid request", type="negative")
                    return
                result = SocialService.respond_to_contact_request(request.id, current_user_id, accept)
                if result:
                    action = "accepted" if accept else "declined"
                    ui.notify(f"Contact request {action}!", type="positive")
                    ui.navigate.reload()
                else:
                    ui.notify("Failed to respond to request", type="negative")
            except Exception as e:
                logger.error(f"Error in messaging: {e}")
                ui.notify(f"Error: {str(e)}", type="negative")

        for request in pending_requests:
            with ui.card().classes("novel-card p-4 mb-4"):
                # Get sender info
                sender_info = f"From: {request.sender.display_name if request.sender else 'Unknown'}"
                ui.label(sender_info).classes("font-semibold text-gray-800 mb-2")

                if request.message:
                    ui.label(f'"{request.message}"').classes("text-gray-700 italic mb-3")

                ui.label(f"Received: {request.created_at.strftime('%b %d, %Y at %I:%M %p')}").classes(
                    "text-sm text-gray-500 mb-3"
                )

                with ui.row().classes("gap-2"):
                    ui.button("Accept", on_click=lambda: handle_request_response(request, True)).classes(
                        "novel-button px-4 py-2"
                    )

                    ui.button("Decline", on_click=lambda: handle_request_response(request, False)).classes(
                        "px-4 py-2"
                    ).props("outlined")

    @staticmethod
    def create_conversations_list(conversations: List[ConversationResponse], current_user_id: int):
        """Create modern conversations list with enhanced styling"""
        if not conversations:
            with ui.card().classes("bg-white p-12 text-center shadow-sm rounded-xl"):
                ui.icon("chat_bubble_outline").classes("text-6xl text-gray-300 mb-4")
                ui.label("No conversations yet").classes("text-xl text-gray-600 mb-2")
                ui.label("When someone accepts your contact request, you can start chatting here.").classes(
                    "text-base text-gray-500 leading-relaxed"
                )
                ui.button("Discover Reflections", on_click=lambda: ui.navigate.to("/discover")).classes(
                    "mt-6 bg-blue-500 text-white px-6 py-3 rounded-full font-semibold"
                )
            return

        ui.label("Messages").classes("text-3xl font-bold mb-6 text-gray-800")

        def open_conversation(conv_id):
            if isinstance(conv_id, int):
                ui.navigate.to(f"/conversation/{conv_id}")

        # Modern conversation cards
        for conv in conversations:
            with (
                ui.card()
                .classes(
                    "bg-white p-4 mb-3 cursor-pointer hover:bg-gray-50 hover:shadow-md transition-all duration-200 border-l-4 border-transparent hover:border-blue-400"
                )
                .on("click", lambda obj_id=conv.id: open_conversation(obj_id) if obj_id is not None else None)
            ):
                with ui.row().classes("items-center gap-4 w-full"):
                    # Avatar
                    ui.icon("account_circle").classes("text-4xl text-gray-400")

                    # Conversation details
                    with ui.column().classes("flex-1 min-w-0"):
                        with ui.row().classes("items-center justify-between"):
                            ui.label(conv.other_user_display_name).classes("font-semibold text-gray-800 text-lg")

                            if conv.unread_count > 0:
                                ui.badge(str(conv.unread_count)).classes("bg-red-500 text-white")

                        if conv.last_message_at:
                            try:
                                from datetime import datetime

                                last_msg_time = datetime.fromisoformat(conv.last_message_at)
                                time_str = last_msg_time.strftime("%b %d, %I:%M %p")
                                ui.label(f"Last active: {time_str}").classes("text-sm text-gray-500")
                            except (ValueError, TypeError) as e:
                                logger.error(f"Error parsing timestamp {conv.last_message_at}: {e}")
                                ui.label("Recently active").classes("text-sm text-gray-500")
                        else:
                            ui.label("No messages yet - start the conversation!").classes(
                                "text-sm text-gray-400 italic"
                            )

                    # Status indicator
                    with ui.column().classes("items-center"):
                        status_color = "text-green-500" if conv.unread_count > 0 else "text-gray-300"
                        ui.icon("circle").classes(f"{status_color} text-xs")

    @staticmethod
    def create_conversation_view(conversation_id: int, current_user_id: int):
        """Create modern chat view with real-time messaging"""
        # Get conversation messages
        messages = SocialService.get_conversation_messages(conversation_id, current_user_id, limit=50)

        # Get conversation info
        conversations = SocialService.get_user_conversations(current_user_id)
        current_conversation = next((c for c in conversations if c.id == conversation_id), None)

        if current_conversation is None:
            ui.label("Conversation not found").classes("text-center text-red-600 py-8")
            return

        # Mark messages as read
        SocialService.mark_messages_as_read(conversation_id, current_user_id)

        # Chat header with other user info
        with ui.card().classes("mb-4 p-4 bg-white shadow-sm"):
            with ui.row().classes("items-center gap-3"):
                # Avatar placeholder
                ui.icon("account_circle").classes("text-4xl text-gray-400")

                with ui.column().classes("flex-1"):
                    ui.label(current_conversation.other_user_display_name).classes(
                        "text-lg font-semibold text-gray-800"
                    )
                    ui.label("Active now").classes("text-sm text-green-500")

        # Messages container with improved styling
        with ui.card().classes("flex-1 bg-gray-50"):
            with ui.scroll_area().classes("h-96 p-4").props("id=messages-container"):
                if not messages:
                    with ui.column().classes("h-full items-center justify-center"):
                        ui.icon("chat_bubble_outline").classes("text-6xl text-gray-300 mb-4")
                        ui.label("Start your conversation!").classes("text-lg text-gray-500")
                        ui.label("Send a message to begin chatting").classes("text-sm text-gray-400")
                else:
                    for message in messages:
                        is_own_message = message.sender_display_name == app.storage.user.get("display_name")
                        MessagingModule._create_message_bubble(message, is_own_message)

    @staticmethod
    def _create_message_bubble(message, is_own_message: bool):
        """Create a styled message bubble"""
        with ui.row().classes(f"mb-3 {'justify-end' if is_own_message else 'justify-start'}"):
            if not is_own_message:
                # Other user's avatar
                ui.icon("account_circle").classes("text-2xl text-gray-400 mt-1")

            with ui.column().classes("max-w-xs"):
                # Message bubble
                bubble_classes = "p-3 rounded-2xl shadow-sm " + (
                    "bg-blue-500 text-white ml-2" if is_own_message else "bg-white text-gray-800 mr-2 border"
                )

                with ui.card().classes(bubble_classes):
                    if not is_own_message:
                        ui.label(message.sender_display_name).classes("text-xs font-semibold mb-1 opacity-75")

                    ui.label(message.message_text).classes("text-sm leading-relaxed whitespace-pre-wrap")

                # Timestamp
                timestamp_classes = "text-xs text-gray-400 mt-1 " + ("text-right" if is_own_message else "text-left")
                formatted_time = message.created_at[:16].replace("T", " at ")
                ui.label(formatted_time).classes(timestamp_classes)

            if is_own_message:
                # Own avatar
                ui.icon("account_circle").classes("text-2xl text-blue-400 mt-1")


def create():
    """Create messaging routes"""

    @ui.page("/messages")
    def messages_page():
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
                # Show contact requests section
                MessagingModule.create_contact_requests_section(user_id)

                # Show conversations
                conversations = SocialService.get_user_conversations(user_id)
                MessagingModule.create_conversations_list(conversations, user_id)

    @ui.page("/conversation/{conversation_id}")
    def conversation_page(conversation_id: int):
        if not AuthModule.is_authenticated():
            ui.navigate.to("/login")
            return

        user_id = AuthModule.get_current_user_id()
        if user_id is None:
            ui.navigate.to("/login")
            return

        DashboardModule.create_navigation()

        with ui.column().classes("min-h-screen bg-gray-100"):
            with ui.column().classes("max-w-5xl mx-auto p-4 h-screen flex"):
                # Header with back button and title
                with ui.row().classes("items-center gap-4 mb-4"):
                    ui.button("← Back", on_click=lambda: ui.navigate.to("/messages")).classes(
                        "text-blue-600 hover:bg-blue-50 px-4 py-2 rounded-full font-semibold"
                    ).props("flat")
                    ui.label("Chat").classes("text-2xl font-bold text-gray-800")

                # Main chat container
                with ui.card().classes("flex-1 flex flex-col shadow-lg rounded-xl overflow-hidden"):
                    # Store conversation components for potential refresh
                    conversation_container = ui.column()

                    with conversation_container:
                        MessagingModule.create_conversation_view(conversation_id, user_id)

                    # Auto-refresh messages every 10 seconds for real-time feel
                    def refresh_messages():
                        try:
                            # Mark new messages as read
                            SocialService.mark_messages_as_read(conversation_id, user_id)
                        except Exception as e:
                            logger.error(f"Error refreshing messages: {e}")

                    # Set up periodic refresh (disabled for now to avoid UI flicker)
                    # ui.timer(10.0, refresh_messages)

                # Enhanced message input section
                def send_message():
                    try:
                        message_text = message_input.value.strip()
                        if not message_text:
                            return

                        # Disable send button to prevent double-sends
                        send_button.set_enabled(False)

                        message_data = DirectMessageCreate(conversation_id=conversation_id, message_text=message_text)

                        sent_message = SocialService.send_message(user_id, message_data)
                        if sent_message:
                            message_input.value = ""
                            ui.notify("Message sent!", type="positive")
                            # Refresh the page to show new message
                            ui.navigate.reload()
                        else:
                            ui.notify("Failed to send message", type="negative")

                    except Exception as e:
                        logger.error(f"Error sending message: {e}")
                        ui.notify(f"Error: {str(e)}", type="negative")
                    finally:
                        send_button.set_enabled(True)

                # Modern message input design
                with ui.card().classes("bg-white shadow-lg border-t"):
                    with ui.row().classes("p-4 gap-3 items-end"):
                        # Emoji/attachment buttons placeholder
                        with ui.row().classes("gap-1"):
                            ui.button("😊", on_click=lambda: None).classes("text-lg").props("flat round size=sm")
                            ui.button("📎", on_click=lambda: None).classes("text-lg").props("flat round size=sm")

                        # Message input
                        message_input = (
                            ui.textarea(
                                placeholder="Type your message...",
                            )
                            .classes("flex-1 max-h-24")
                            .props("outlined dense rows=1 autogrow")
                        )

                        # Send button with modern styling
                        send_button = (
                            ui.button("Send", on_click=send_message)
                            .classes("bg-blue-500 text-white px-6 py-2 rounded-full font-semibold")
                            .props("size=lg")
                        )

                        # Enter key to send
                        message_input.on(
                            "keydown.enter", lambda e: send_message() if not e.args.get("shiftKey") else None
                        )
