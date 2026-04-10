from ._anvil_designer import Form1Template
from anvil import *
import anvil.users

from ..CurrentWorkoutForm import CurrentWorkoutForm


class Form1(Form1Template):
  def __init__(self, **properties):
    self.init_components(**properties)

    if anvil.users.get_user() is None:
      anvil.users.login_with_google()

    root = self._get_root_container()
    if hasattr(root, "clear"):
      root.clear()
    root.background = "#08111b"
    root.foreground = "#f3f6fb"

    self.current_form = CurrentWorkoutForm()
    root.add_component(self.current_form, full_width_row=True)

  def _get_root_container(self):
    if hasattr(self, "content_panel"):
      return self.content_panel
    if hasattr(self, "column_panel_1"):
      return self.column_panel_1
    container = ColumnPanel(background="#08111b", foreground="#f3f6fb")
    self.add_component(container)
    return container
