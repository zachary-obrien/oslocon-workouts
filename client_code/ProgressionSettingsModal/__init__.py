from ._anvil_designer import ProgressionSettingsModalTemplate
from anvil import *


class ProgressionSettingsModal(ProgressionSettingsModalTemplate):
    def __init__(self, current_value=3, **properties):
        self.init_components(**properties)
        self.current_value = int(current_value or 3)
        self._build_ui()

    def _build_ui(self):
        self.root = LinearPanel()
        self.add_component(self.root)
        self.root.add_component(Label(text="Progression Settings", bold=True, font_size=20))
        self.root.add_component(Label(text="Increase weight after this many qualifying workouts:"))
        self.dropdown = DropDown(items=[(str(i), i) for i in range(1, 7)], selected_value=self.current_value)
        self.root.add_component(self.dropdown)
        self.save_btn = Button(text="Save", role="filled-button")
        self.root.add_component(self.save_btn)
        self.save_btn.set_event_handler("click", self.save_clicked)

    def save_clicked(self, **event_args):
        self.raise_event("x-close-alert", value={"action": "save", "value": self.dropdown.selected_value})
