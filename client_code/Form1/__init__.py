from ._anvil_designer import Form1Template
from anvil import *
import anvil.server
import anvil.users

from ..CurrentWorkoutForm import CurrentWorkoutForm
from ..HistoryForm import HistoryForm
from ..AccountForm import AccountForm


class Form1(Form1Template):
    def __init__(self, **properties):
        self.init_components(**properties)
        self.state = {}
        self._build_ui()
        self._bootstrap()

    def _build_ui(self):
        self.background = "#0b0f14"
        self.foreground = "#f3f6fb"

        self.root_panel = LinearPanel(spacing="none", background="#0b0f14", foreground="#f3f6fb")
        self.add_component(self.root_panel)

        self.header = ColumnPanel(background="#141c26", foreground="#f3f6fb", border="1px solid #283548")
        self.root_panel.add_component(self.header)

        logo_row = FlowPanel(align="left", spacing="small")
        self.header.add_component(logo_row)

        self.logo = Image(source="_/theme/512x512OsloconWorkout.png", height=72)
        logo_row.add_component(self.logo)

        title_col = LinearPanel(spacing="none")
        logo_row.add_component(title_col)
        self.title_label = Label(text="Oslocon Workouts", bold=True, font_size=28, foreground="#f3f6fb")
        self.subtitle_label = Label(text="Loading...", foreground="#97a5b7")
        title_col.add_component(self.title_label)
        title_col.add_component(self.subtitle_label)

        self.nav_row = FlowPanel(align="left", spacing="medium")
        self.header.add_component(self.nav_row)
        self.workout_btn = Button(text="Workout", role="filled-button")
        self.history_btn = Button(text="History")
        self.account_btn = Button(text="Account")
        self.nav_row.add_component(self.workout_btn)
        self.nav_row.add_component(self.history_btn)
        self.nav_row.add_component(self.account_btn)

        self.content_panel = ColumnPanel(background="#0b0f14")
        self.root_panel.add_component(self.content_panel, full_width_row=True)

        self.workout_btn.set_event_handler("click", self.show_workout)
        self.history_btn.set_event_handler("click", self.show_history)
        self.account_btn.set_event_handler("click", self.show_account)

    def _bootstrap(self):
        if anvil.users.get_user() is None:
            try:
                anvil.users.login_with_google()
            except Exception as e:
                alert(f"Google login is required.\n\n{e}")
                return

        payload = anvil.server.call("get_bootstrap_payload")
        self.state = payload
        user = payload["user"]
        self.subtitle_label.text = f"Logged in as {user['display_name']} • {user['email']}"
        self.show_workout()

    def _swap_content(self, form_obj):
        self.content_panel.clear()
        self.content_panel.add_component(form_obj, full_width_row=True)

    def show_workout(self, **event_args):
        self._swap_content(CurrentWorkoutForm())
        self._set_nav_active("workout")

    def show_history(self, **event_args):
        self._swap_content(HistoryForm())
        self._set_nav_active("history")

    def show_account(self, **event_args):
        self._swap_content(AccountForm())
        self._set_nav_active("account")

    def _set_nav_active(self, active):
        self.workout_btn.role = "filled-button" if active == "workout" else None
        self.history_btn.role = "filled-button" if active == "history" else None
        self.account_btn.role = "filled-button" if active == "account" else None
