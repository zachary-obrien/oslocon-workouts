from ._anvil_designer import AutoCompleteWorkoutModalTemplate
from anvil import *


class AutoCompleteWorkoutModal(AutoCompleteWorkoutModalTemplate):
    def __init__(self, has_skipped=False, **properties):
        self.init_components(**properties)
        self.has_skipped = has_skipped
        self._build_ui()

    def _build_ui(self):
        self.root = LinearPanel()
        self.add_component(self.root)
        self.root.add_component(Label(text="Workout complete?", bold=True, font_size=20))
        suffix = " or skipped" if self.has_skipped else ""
        self.root.add_component(Label(text=f"All sets finished{suffix}. Want to log the workout?"))
        row = FlowPanel(spacing="medium")
        self.root.add_component(row)
        keep_btn = Button(text="Keep Editing")
        complete_btn = Button(text="Complete Workout", role="filled-button")
        row.add_component(keep_btn)
        row.add_component(complete_btn)
        keep_btn.set_event_handler("click", lambda **e: self.raise_event("x-close-alert", value=False))
        complete_btn.set_event_handler("click", lambda **e: self.raise_event("x-close-alert", value=True))
