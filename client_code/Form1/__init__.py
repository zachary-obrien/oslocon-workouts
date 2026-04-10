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

    self.active_form = None
    self.bootstrap_payload = None

    self._build_shell()
    self._ensure_logged_in()
    self._bootstrap_user()

    self.show_current_workout()

  def _build_shell(self):
    self._root = self._get_root_container()

    if hasattr(self._root, "clear"):
      self._root.clear()

    self.header_panel = ColumnPanel()
    self.nav_panel = FlowPanel()
    self.main_content_host = ColumnPanel()

    self.logo_image = Image(source="_/theme/512x512OsloconWorkout.png", height=72)
    self.title_label = Label(
      text="Oslocon Workout",
      bold=True,
      font_size=26,
      spacing_above="none",
      spacing_below="none",
    )
    self.subtitle_label = Label(
      text="Workout Tracker",
      foreground="theme:Secondary",
      spacing_above="none",
    )

    self.current_button = Button(text="Current Workout", role="filled-button")
    self.history_button = Button(text="History")
    self.account_button = Button(text="Account")

    self.current_button.set_event_handler("click", self.current_button_click)
    self.history_button.set_event_handler("click", self.history_button_click)
    self.account_button.set_event_handler("click", self.account_button_click)

    self.header_panel.add_component(self.logo_image)
    self.header_panel.add_component(self.title_label)
    self.header_panel.add_component(self.subtitle_label)

    self.nav_panel.add_component(self.current_button)
    self.nav_panel.add_component(self.history_button)
    self.nav_panel.add_component(self.account_button)

    self._root.add_component(self.header_panel)
    self._root.add_component(self.nav_panel)
    self._root.add_component(self.main_content_host)

  def _get_root_container(self):
    if hasattr(self, "content_panel"):
      return self.content_panel
    if hasattr(self, "column_panel_1"):
      return self.column_panel_1
    if hasattr(self, "linear_panel_1"):
      return self.linear_panel_1

    container = ColumnPanel()
    self.add_component(container)
    return container

  def _ensure_logged_in(self):
    user = anvil.users.get_user()
    if user is None:
      user = anvil.users.login_with_google()
    return user

  def _bootstrap_user(self):
    self.bootstrap_payload = anvil.server.call("get_bootstrap_payload")

  def _show_child_form(self, form_cls, **kwargs):
    if hasattr(self.main_content_host, "clear"):
      self.main_content_host.clear()

    self.active_form = form_cls(**kwargs)
    self.main_content_host.add_component(self.active_form, full_width_row=True)

  def _set_nav_state(self, selected):
    self.current_button.role = "filled-button" if selected == "current" else None
    self.history_button.role = "filled-button" if selected == "history" else None
    self.account_button.role = "filled-button" if selected == "account" else None

  def show_current_workout(self):
    self._set_nav_state("current")
    initial_payload = (self.bootstrap_payload or {}).get("workout")
    self._show_child_form(CurrentWorkoutForm, initial_payload=initial_payload)

  def show_history(self):
    self._set_nav_state("history")
    self._show_child_form(HistoryForm)

  def show_account(self):
    self._set_nav_state("account")
    initial_user = (self.bootstrap_payload or {}).get("user")
    self._show_child_form(AccountForm, initial_user=initial_user)

  def current_button_click(self, **event_args):
    self.show_current_workout()

  def history_button_click(self, **event_args):
    self.show_history()

  def account_button_click(self, **event_args):
    self.show_account()