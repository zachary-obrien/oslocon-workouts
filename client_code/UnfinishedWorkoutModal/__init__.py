from ._anvil_designer import UnfinishedWorkoutModalTemplate
from anvil import *


class UnfinishedWorkoutModal(UnfinishedWorkoutModalTemplate):
    def __init__(self, sets_autocompleted=False, **properties):
        self.init_components(**properties)
        self.sets_autocompleted = sets_autocompleted
        self._build_ui()

    def _build_ui(self):
        self.root = ColumnPanel(role="modal-card")
        self.add_component(self.root)
        head = FlowPanel(align="justify")
        head.add_component(Label(text="Some sets are unfinished", role="exercise-title", spacing_below="none"))
        close = Button(text="Close", role="button-secondary")
        close.set_event_handler("click", lambda **e: self.raise_event("x-close-modal"))
        head.add_component(close)
        self.root.add_component(head)
        title = "Ready to complete" if self.sets_autocompleted else "Some sets are still unfinished"
        body = "Remaining sets auto-completed." if self.sets_autocompleted else "You can go back, complete anyway, or finish the remaining sets automatically."
        self.root.add_component(Label(text=title, role="exercise-title", spacing_below="none"))
        self.root.add_component(Label(text=body, role="muted"))
        row = FlowPanel()
        go_back = Button(text="Go Back", role="button-secondary")
        main = Button(text="Complete Workout" if self.sets_autocompleted else "Complete Anyway", role="button-primary")
        row.add_component(go_back)
        row.add_component(main)
        self.root.add_component(row)
        if not self.sets_autocompleted:
            finish = Button(text="Finish Remaining Sets", role="menu-item")
            finish.set_event_handler("click", lambda **e: self.raise_event("x-finish-remaining"))
            self.root.add_component(finish)
            main.set_event_handler("click", lambda **e: self.raise_event("x-complete-anyway"))
        else:
            main.set_event_handler("click", lambda **e: self.raise_event("x-complete-after-finish"))
        go_back.set_event_handler("click", lambda **e: self.raise_event("x-go-back"))
