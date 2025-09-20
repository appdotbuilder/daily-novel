from app.database import create_tables
from nicegui import ui
import app.ui.auth_module
import app.ui.dashboard_module
import app.ui.discover_module
import app.ui.profile_module
import app.ui.messaging_module


def startup() -> None:
    # this function is called before the first request
    create_tables()

    # Create all UI modules
    app.ui.auth_module.create()
    app.ui.dashboard_module.create()
    app.ui.discover_module.create()
    app.ui.profile_module.create()
    app.ui.messaging_module.create()

    @ui.page("/")
    def index():
        # Redirect to dashboard if authenticated, otherwise to login
        from app.ui.auth_module import AuthModule

        if AuthModule.is_authenticated():
            ui.navigate.to("/dashboard")
        else:
            ui.navigate.to("/login")
