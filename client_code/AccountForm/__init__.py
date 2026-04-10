from ._anvil_designer import AccountFormTemplate
from anvil import *
import anvil.server

from ..ProgressionSettingsModal import ProgressionSettingsModal


class AccountForm(AccountFormTemplate):
  def __init__(self, initial_user=None, **properties):
    self.init_components(**properties)
    self.user_payload = initial_user or {}
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
    user = (payload or {}).get("user") or {}

    self.user_payload = {
      "display_name": user.get("display_name") or "User",
      "email": user.get("email") or "",
      "progress_every_n_qualifying_workouts": int(user.get("progress_every_n_qualifying_workouts") or 3),
    }

    self.info_panel.clear()
    self.info_panel.add_component(Label(text=f"Name: {self.user_payload['display_name']}"))
    self.info_panel.add_component(Label(text=f"Email: {self.user_payload['email']}"))
    self.info_panel.add_component(
      Label(text=f"Progress every: {self.user_payload['progress_every_n_qualifying_workouts']} qualifying workouts")
    )

  def progress_btn_click(self, **event_args):
    current_value = int(self.user_payload.get("progress_every_n_qualifying_workouts") or 3)
    modal = ProgressionSettingsModal(current_value)
    result = alert(content=modal, title="Progression Settings", buttons=[], dismissible=True)
    if isinstance(result, dict) and result.get("action") == "save":
      anvil.server.call("update_progression_setting", result.get("value"))
      self.refresh_user()