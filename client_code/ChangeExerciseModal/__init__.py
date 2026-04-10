from ._anvil_designer import ChangeExerciseModalTemplate
from anvil import *
import anvil.server

BG = "#0f1b2b"
TEXT = "#f3f6fb"
MUTED = "#9fb1c5"
BORDER = "1px solid #24354d"
BTN = "#12253b"


class ChangeExerciseModal(ChangeExerciseModalTemplate):
  def __init__(self, current_name="", **properties):
    self.init_components(**properties)
    self.current_name = current_name or ""
    self._build_ui()
    self.search_box.text = self.current_name
    self.search()

  def _build_ui(self):
    self.root = ColumnPanel(background=BG, foreground=TEXT)
    self.add_component(self.root)
    self.root.add_component(Label(text="Change Exercise", bold=True, font_size=20, foreground=TEXT))
    self.root.add_component(Label(text="Search the exercise database", foreground=MUTED))

    row = FlowPanel(align="left")
    self.root.add_component(row)
    self.search_box = TextBox(placeholder="Search exercises...", background=BTN, foreground=TEXT)
    self.search_btn = Button(text="Search", role="filled-button", background="#d97f37", foreground="#ffffff")
    row.add_component(self.search_box)
    row.add_component(self.search_btn)

    self.results_panel = LinearPanel(spacing="small")
    self.root.add_component(self.results_panel)

    self.search_btn.set_event_handler("click", self.search)
    self.search_box.set_event_handler("pressed_enter", self.search)

  def search(self, **event_args):
    results = anvil.server.call("search_exercise_options", self.search_box.text or "")
    self.results_panel.clear()
    for result in results:
      card = ColumnPanel(background=BG, foreground=TEXT, border=BORDER)
      btn = Button(text=result['name'], align="left", background=BTN, foreground=TEXT)
      btn.tag.exercise_id = result["exercise_id"]
      btn.set_event_handler("click", self.choose_result)
      card.add_component(btn)
      primary = result.get("primary_muscles") or []
      if primary:
        card.add_component(Label(text=" • ".join([str(x).title() for x in primary[:2]]), foreground=MUTED))
      self.results_panel.add_component(card, full_width_row=True)

  def choose_result(self, **event_args):
    self.raise_event("x-close-alert", value={"action": "choose", "exercise_id": event_args['sender'].tag.exercise_id})
