from nicegui import ui, app
from typing import Optional
from app.models import UserCreate, UserLogin
from app.services.auth_service import AuthService
import logging

logger = logging.getLogger(__name__)


class AuthModule:
    """Authentication UI module for login and registration"""

    @staticmethod
    def apply_novel_theme():
        """Apply minimalist novel-like styling"""
        ui.add_head_html("""
        <style>
        body { 
            font-family: 'Georgia', 'Times New Roman', serif;
            background: #faf7f2;
            color: #2c2c2c;
            line-height: 1.8;
        }
        .novel-card {
            background: #ffffff;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            border: 1px solid #e8e5e0;
        }
        .novel-input input {
            font-family: 'Georgia', serif;
            border: 1px solid #d4d4d8;
        }
        .novel-button {
            font-family: 'Georgia', serif;
            background: #374151;
            color: white;
            transition: all 0.2s;
        }
        .novel-button:hover {
            background: #1f2937;
        }
        .novel-title {
            font-weight: normal;
            letter-spacing: 0.5px;
        }
        </style>
        """)

    @staticmethod
    def create_login_form():
        """Create login form component"""

        def handle_login():
            try:
                login_data = UserLogin(username=username_input.value.strip(), password=password_input.value)

                user = AuthService.authenticate_user(login_data)
                if user is None:
                    ui.notify("Invalid username or password", type="negative")
                    return

                # Store user session
                app.storage.user["user_id"] = user.id
                app.storage.user["username"] = user.username
                app.storage.user["display_name"] = user.display_name

                ui.notify(f"Welcome back, {user.display_name}!", type="positive")
                ui.navigate.to("/dashboard")

            except Exception as e:
                logger.error(f"Login error: {e}")
                ui.notify("Login failed. Please try again.", type="negative")

        with ui.card().classes("novel-card p-8 max-w-md mx-auto mt-16"):
            ui.label("Welcome Back").classes("novel-title text-3xl text-center mb-8 text-gray-800")

            with ui.column().classes("gap-4 w-full"):
                username_input = ui.input("Username", placeholder="Enter your username").classes("novel-input w-full")
                password_input = ui.input("Password", password=True, placeholder="Enter your password").classes(
                    "novel-input w-full"
                )

                ui.button("Sign In", on_click=handle_login).classes("novel-button w-full py-3 rounded")

                with ui.row().classes("justify-center mt-4"):
                    ui.label("New reader?").classes("text-gray-600")
                    ui.link("Create an account", "/register").classes("text-blue-600 ml-2 hover:underline")

    @staticmethod
    def create_register_form():
        """Create registration form component"""

        def handle_register():
            try:
                # Validate password confirmation
                if password_input.value != confirm_password_input.value:
                    ui.notify("Passwords do not match", type="negative")
                    return

                user_data = UserCreate(
                    username=username_input.value.strip(),
                    email=email_input.value.strip(),
                    password=password_input.value,
                    display_name=display_name_input.value.strip(),
                )

                user = AuthService.create_user(user_data)
                if user is None:
                    ui.notify("Username or email already exists", type="negative")
                    return

                # Auto-login after registration
                app.storage.user["user_id"] = user.id
                app.storage.user["username"] = user.username
                app.storage.user["display_name"] = user.display_name

                ui.notify(f"Welcome to Daily Reflections, {user.display_name}!", type="positive")
                ui.navigate.to("/dashboard")

            except ValueError as e:
                ui.notify(f"Registration failed: {str(e)}", type="negative")
            except Exception as e:
                logger.error(f"Registration error: {e}")
                ui.notify("Registration failed. Please try again.", type="negative")

        with ui.card().classes("novel-card p-8 max-w-md mx-auto mt-16"):
            ui.label("Join Our Community").classes("novel-title text-3xl text-center mb-8 text-gray-800")

            with ui.column().classes("gap-4 w-full"):
                display_name_input = ui.input("Display Name", placeholder="How should we call you?").classes(
                    "novel-input w-full"
                )
                username_input = ui.input("Username", placeholder="Choose a unique username").classes(
                    "novel-input w-full"
                )
                email_input = ui.input("Email", placeholder="your.email@example.com").classes("novel-input w-full")
                password_input = ui.input("Password", password=True, placeholder="Create a strong password").classes(
                    "novel-input w-full"
                )
                confirm_password_input = ui.input(
                    "Confirm Password", password=True, placeholder="Confirm your password"
                ).classes("novel-input w-full")

                ui.button("Create Account", on_click=handle_register).classes("novel-button w-full py-3 rounded")

                with ui.row().classes("justify-center mt-4"):
                    ui.label("Already have an account?").classes("text-gray-600")
                    ui.link("Sign in", "/login").classes("text-blue-600 ml-2 hover:underline")

    @staticmethod
    def get_current_user_id() -> Optional[int]:
        """Get current user ID from session"""
        return app.storage.user.get("user_id")

    @staticmethod
    def is_authenticated() -> bool:
        """Check if user is authenticated"""
        return AuthModule.get_current_user_id() is not None

    @staticmethod
    def logout():
        """Log out current user"""
        app.storage.user.clear()
        ui.navigate.to("/login")


def create():
    """Create authentication routes"""
    AuthModule.apply_novel_theme()

    @ui.page("/login")
    def login_page():
        if AuthModule.is_authenticated():
            ui.navigate.to("/dashboard")
            return
        AuthModule.create_login_form()

    @ui.page("/register")
    def register_page():
        if AuthModule.is_authenticated():
            ui.navigate.to("/dashboard")
            return
        AuthModule.create_register_form()

    @ui.page("/logout")
    def logout_page():
        AuthModule.logout()
