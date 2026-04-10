from ._anvil_designer import AccountFormTemplate
from anvil import *
import anvil.server

from ..ProgressionSettingsModal import ProgressionSettingsModal


class AccountForm(AccountFormTemplate):
    def __init__(self, **properties):
        self.init_components(**properties)
        self._build_ui()
        self.refresh_user()

    def _build_ui(self):
        self.root = LinearPanel()
        self.add_component(self.root)
        self.root.add_component(Label(text="Account", bold=True, font_size=24))
        self.info_panel = LinearPanel(spacing="small")
        self.root.add_component(self.info_panel)
        self.progress_btn = Button(text="Update Progression Setting", role="filled-button")
        self.root.add_component(self.progress_btn)
        self.progress_btn.set_event_handler("click", self.progress_btn_click)

    def refresh_user(self):
        payload = anvil.server.call("get_bootstrap_payload")
        user = payload["user"]
        self.user_payload = user
        self.info_panel.clear()
        self.info_panel.add_component(Label(text=f"Name: {user['display_name']}"))
        self.info_panel.add_component(Label(text=f"Email: {user['email']}"))
        self.info_panel.add_component(Label(text=f"Progress every: {user['progress_every_n_qualifying_workouts']} qualifying workouts"))

    def progress_btn_click(self, **event_args):
        modal = ProgressionSettingsModal(self.user_payload["progress_every_n_qualifying_workouts"])
        result = alert(content=modal, title="Progression Settings", buttons=[], dismissible=True)
        if isinstance(result, dict) and result.get("action") == "save":
            anvil.server.call("update_progression_setting", result["value"])
            self.refresh_user()
