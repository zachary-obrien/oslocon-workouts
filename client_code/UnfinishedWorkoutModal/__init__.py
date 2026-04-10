from ._anvil_designer import UnfinishedWorkoutModalTemplate
from anvil import *


class UnfinishedWorkoutModal(UnfinishedWorkoutModalTemplate):
    def __init__(self, **properties):
        self.init_components(**properties)
        self._build_ui()

    def _build_ui(self):
        self.root = LinearPanel()
        self.add_component(self.root)
        self.root.add_component(Label(text="Some sets are still unfinished", bold=True, font_size=20))
        self.root.add_component(Label(text="You can go back, complete anyway, or finish the remaining sets automatically."))

        row = FlowPanel(align="left", spacing="medium")
        self.root.add_component(row)
        go_back = Button(text="Go Back")
        complete_anyway = Button(text="Complete Anyway", role="filled-button")
        row.add_component(go_back)
        row.add_component(complete_anyway)

        finish_btn = Button(text="Finish Remaining Sets")
        self.root.add_component(finish_btn)

        go_back.set_event_handler("click", lambda **e: self.raise_event("x-close-alert", value="go_back"))
        complete_anyway.set_event_handler("click", lambda **e: self.raise_event("x-close-alert", value="complete_anyway"))
        finish_btn.set_event_handler("click", lambda **e: self.raise_event("x-close-alert", value="finish_remaining"))
