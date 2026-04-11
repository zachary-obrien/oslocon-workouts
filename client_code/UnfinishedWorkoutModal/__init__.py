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
    head.add_component(
      Label(
        text="Some sets are unfinished" if not self.sets_autocompleted else "Ready to complete",
        role="exercise-title",
        spacing_above="none",
        spacing_below="none",
      )
    )
    close = Button(text="✕", role="icon-button")
    close.set_event_handler("click", lambda **e: self.raise_event("x-close-modal"))
    head.add_component(close)
    self.root.add_component(head)

    body = "You can go back, complete anyway, or finish the remaining sets automatically." if not self.sets_autocompleted else "Remaining sets auto-completed."
    self.root.add_component(Label(text=body, role="muted"))

    grid = GridPanel()
    go_back = Button(text="Go Back", role="button-secondary")
    main = Button(text="Complete Workout" if self.sets_autocompleted else "Complete Anyway", role="button-primary")
    go_back.set_event_handler("click", lambda **e: self.raise_event("x-go-back"))
    if self.sets_autocompleted:
      main.set_event_handler("click", lambda **e: self.raise_event("x-complete-after-finish"))
    else:
      main.set_event_handler("click", lambda **e: self.raise_event("x-complete-anyway"))
    grid.add_component(go_back, row="A", col_xs=1, width_xs=4)
    grid.add_component(main, row="A", col_xs=7, width_xs=4)
    self.root.add_component(grid, full_width_row=True)

    if not self.sets_autocompleted:
      finish_grid = GridPanel()
      finish = Button(text="Finish Remaining Sets", role="button-subtle")
      finish.set_event_handler("click", lambda **e: self.raise_event("x-finish-remaining"))
      finish_grid.add_component(finish, row="A", col_xs=3, width_xs=6)
      self.root.add_component(finish_grid, full_width_row=True)