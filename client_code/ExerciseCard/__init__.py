from ._anvil_designer import ExerciseCardTemplate
from anvil import *

from ..SetRow import SetRow

CARD_BG = "#0f1b2b"
CARD_GREEN = "#103528"
CARD_RED = "#381c22"
CARD_ORANGE = "#3a2812"
TEXT = "#f3f6fb"
MUTED = "#9fb1c5"
BORDER = "1px solid #24354d"
PILL_BG = "#1a293b"


class ExerciseCard(ExerciseCardTemplate):
  def __init__(self, exercise_index=0, exercise_data=None, **properties):
    self.init_components(**properties)
    self.exercise_index = exercise_index
    self.exercise_data = dict(exercise_data or {})
    self._build_ui()
    self.render()

  def _build_ui(self):
    self.root = ColumnPanel(background=CARD_BG, foreground=TEXT, border=BORDER)
    self.add_component(self.root)

    self.header = GridPanel(background=CARD_BG)
    self.root.add_component(self.header, full_width_row=True)

    self.title_label = Label(text="", bold=True, font_size=20, foreground=TEXT)
    self.pill_label = Label(text="", foreground=MUTED, background=PILL_BG, border="1px solid #2d4159")
    self.menu_btn = Button(text="⋯", width=44, background="#12253b", foreground=TEXT)
    self.edit_btn = Button(text="Edit", width=56, background="#12253b", foreground=TEXT, visible=False)

    self.header.add_component(self.title_label, row="A", col_xs=0, width_xs=6)
    self.header.add_component(self.pill_label, row="A", col_xs=6, width_xs=4)
    self.header.add_component(self.menu_btn, row="A", col_xs=10, width_xs=2)
    self.header.add_component(self.edit_btn, row="A", col_xs=10, width_xs=2)

    self.summary_label = Label(text="", foreground=MUTED, visible=False)
    self.root.add_component(self.summary_label)

    self.sets_panel = LinearPanel(spacing="small", background=CARD_BG)
    self.root.add_component(self.sets_panel, full_width_row=True)

    self.menu_btn.set_event_handler("click", self.menu_btn_click)
    self.edit_btn.set_event_handler("click", self.expand_card)

  def render(self):
    ex = self.exercise_data
    self.root.background = self._card_bg()
    self.header.background = self._card_bg()
    self.title_label.text = ex.get("exercise_label") or "Add Exercise"
    self.pill_label.text = self._pill_text(ex)
    self.summary_label.visible = False
    self.edit_btn.visible = False
    self.menu_btn.visible = True
    self.sets_panel.clear()

    if ex.get("is_unassigned"):
      self.summary_label.visible = True
      self.summary_label.text = "No exercise assigned yet. Tap Edit to choose one."
      return

    if ex.get("collapsed") and ex.get("status") in ("completed", "skipped"):
      self.summary_label.visible = True
      self.summary_label.text = self._collapsed_summary()
      self.edit_btn.visible = True
      self.menu_btn.visible = False
      return

    for idx, set_data in enumerate(ex.get("sets", [])):
      row = SetRow(exercise_index=self.exercise_index, set_index=idx, set_data=set_data, uses_bodyweight=bool(ex.get("uses_bodyweight")))
      row.set_event_handler("x-set-changed", self.set_row_changed)
      row.set_event_handler("x-set-check-toggled", self.set_row_check_toggled)
      row.set_event_handler("x-add-set-below", self.add_set_below)
      row.set_event_handler("x-delete-set", self.delete_set)
      self.sets_panel.add_component(row)

  def _pill_text(self, ex):
    mg = ex.get("muscle_group") or "Unassigned"
    return str(mg).title()

  def _card_bg(self):
    ex = self.exercise_data
    if ex.get("status") == "skipped":
      return CARD_RED
    if ex.get("status") == "completed":
      return CARD_GREEN
    if any(not s.get("performed") for s in ex.get("sets", [])) and any(s.get("performed") for s in ex.get("sets", [])):
      return CARD_ORANGE
    return CARD_BG

  def _collapsed_summary(self):
    ex = self.exercise_data
    if ex.get("status") == "skipped":
      return "Skipped for this workout"
    sets = ex.get("sets", [])
    checked = len([s for s in sets if s.get("performed")])
    if not sets:
      return "Completed"
    first = sets[0]
    weight_label = "BW" if ex.get("uses_bodyweight") else f"{first.get('weight')} lb"
    avg_reps = round(sum(int(s.get('reps') or 0) for s in sets) / len(sets)) if sets else 0
    return f"Completed • {checked}/{len(sets)} sets checked • {weight_label} • avg {avg_reps} reps"

  def _emit_update(self):
    self.raise_event("x-exercise-updated", exercise_index=self.exercise_index, exercise_data=self.exercise_data)

  def expand_card(self, **event_args):
    self.exercise_data["collapsed"] = False
    if self.exercise_data.get("status") == "skipped":
      self.exercise_data["status"] = "active"
    self._emit_update()

  def set_row_changed(self, exercise_index=None, set_index=None, set_data=None, **event_args):
    self.exercise_data["sets"][set_index] = dict(set_data)
    for idx in range(set_index + 1, len(self.exercise_data["sets"])):
      if self.exercise_data["sets"][idx].get("performed"):
        continue
      self.exercise_data["sets"][idx]["weight"] = set_data.get("weight")
      self.exercise_data["sets"][idx]["reps"] = set_data.get("reps")
    if all(s.get("performed") for s in self.exercise_data["sets"]):
      self.exercise_data["status"] = "completed"
      self.exercise_data["collapsed"] = True
    elif self.exercise_data.get("status") != "skipped":
      self.exercise_data["status"] = "active"
    self._emit_update()

  def set_row_check_toggled(self, **event_args):
    self.set_row_changed(**event_args)

  def add_set_below(self, exercise_index=None, set_index=None, **event_args):
    base = dict(self.exercise_data["sets"][set_index])
    base["performed"] = False
    base["auto_completed"] = False
    self.exercise_data["sets"].insert(set_index + 1, base)
    self._emit_update()

  def delete_set(self, exercise_index=None, set_index=None, **event_args):
    if len(self.exercise_data["sets"]) > 1:
      self.exercise_data["sets"].pop(set_index)
    else:
      self.exercise_data["sets"][0]["performed"] = False
      self.exercise_data["sets"][0]["auto_completed"] = False
    self._emit_update()

  def menu_btn_click(self, **event_args):
    ex = self.exercise_data
    buttons = [
      ("View History", "history"),
      ("Change Exercise", "change"),
      ("Move Up", "up"),
      ("Move Down", "down"),
      ("Remove Exercise", "remove"),
    ]
    if not ex.get("is_unassigned"):
      buttons.append(("Skip Exercise", "skip"))
    buttons.append(("Cancel", None))
    result = alert(title=ex.get("exercise_label") or "Exercise", content="Choose an action", buttons=buttons, dismissible=True)
    if result == "history":
      self.raise_event("x-view-history", exercise_index=self.exercise_index, exercise_data=ex)
    elif result == "change":
      self.raise_event("x-change-exercise", exercise_index=self.exercise_index, exercise_data=ex)
    elif result == "up":
      self.raise_event("x-move-slot", exercise_index=self.exercise_index, direction="up", exercise_data=ex)
    elif result == "down":
      self.raise_event("x-move-slot", exercise_index=self.exercise_index, direction="down", exercise_data=ex)
    elif result == "remove":
      self.raise_event("x-remove-slot", exercise_index=self.exercise_index, exercise_data=ex)
    elif result == "skip":
      ex["status"] = "skipped"
      ex["collapsed"] = True
      self._emit_update()
