from ._anvil_designer import SetRowTemplate
from anvil import *

TEXT = "#f3f6fb"
MUTED = "#9fb1c5"
BORDER = "1px solid #24354d"
BTN_BG = "#12253b"
ROW_BG = "#0f1b2b"
CHECK_BG = "#16a06c"


def _weight_options(uses_bodyweight):
  if uses_bodyweight:
    return [("BW", None)]
  opts = []
  val = 5.0
  while val <= 300:
    label = f"{int(val) if float(val).is_integer() else val:g}"
    opts.append((label, val))
    val += 2.5
  return opts


def _rep_options():
  return [(str(i), i) for i in range(3, 31)]


class SetRow(SetRowTemplate):
  def __init__(self, exercise_index=0, set_index=0, set_data=None, uses_bodyweight=False, **properties):
    self.init_components(**properties)
    self.exercise_index = exercise_index
    self.set_index = set_index
    self.set_data = dict(set_data or {})
    self.uses_bodyweight = uses_bodyweight
    self._build_ui()
    self._render()

  def _build_ui(self):
    self.panel = GridPanel(background=ROW_BG, foreground=TEXT, border=BORDER)
    self.add_component(self.panel)

    self.menu_btn = Button(text="⋯", width=40, background=BTN_BG, foreground=TEXT)
    self.weight_dd = DropDown(include_placeholder=False, width=86, items=_weight_options(self.uses_bodyweight), background=BTN_BG, foreground=TEXT)
    self.weight_lbl = Label(text="lb", foreground=MUTED)
    self.reps_dd = DropDown(include_placeholder=False, width=72, items=_rep_options(), background=BTN_BG, foreground=TEXT)
    self.reps_lbl = Label(text="reps", foreground=MUTED)
    self.done_btn = Button(text="", width=36, background=BTN_BG, foreground=TEXT)

    weight_wrap = FlowPanel(gap="tiny")
    weight_wrap.add_component(self.weight_dd)
    weight_wrap.add_component(self.weight_lbl)
    reps_wrap = FlowPanel(gap="tiny")
    reps_wrap.add_component(self.reps_dd)
    reps_wrap.add_component(self.reps_lbl)

    self.panel.add_component(self.menu_btn, row="A", col_xs=0, width_xs=2)
    self.panel.add_component(weight_wrap, row="A", col_xs=2, width_xs=4)
    self.panel.add_component(reps_wrap, row="A", col_xs=6, width_xs=4)
    self.panel.add_component(self.done_btn, row="A", col_xs=10, width_xs=2)

    self.menu_btn.set_event_handler("click", self.menu_btn_click)
    self.weight_dd.set_event_handler("change", self.value_changed)
    self.reps_dd.set_event_handler("change", self.value_changed)
    self.done_btn.set_event_handler("click", self.toggle_done)

  def _render(self):
    self.weight_lbl.visible = not self.uses_bodyweight
    self.weight_dd.items = _weight_options(self.uses_bodyweight)
    self.weight_dd.selected_value = self.set_data.get("weight")
    self.reps_dd.selected_value = self.set_data.get("reps")
    self._render_done_btn()

  def _render_done_btn(self):
    if self.set_data.get("performed"):
      self.done_btn.text = "✓"
      self.done_btn.background = CHECK_BG
    else:
      self.done_btn.text = ""
      self.done_btn.background = BTN_BG

  def _emit_changed(self):
    self.raise_event(
      "x-set-changed",
      exercise_index=self.exercise_index,
      set_index=self.set_index,
      set_data=dict(self.set_data),
    )

  def value_changed(self, **event_args):
    self.set_data["weight"] = self.weight_dd.selected_value
    self.set_data["reps"] = self.reps_dd.selected_value
    self._emit_changed()

  def toggle_done(self, **event_args):
    self.set_data["performed"] = not self.set_data.get("performed")
    self._render_done_btn()
    self.raise_event(
      "x-set-check-toggled",
      exercise_index=self.exercise_index,
      set_index=self.set_index,
      set_data=dict(self.set_data),
    )

  def menu_btn_click(self, **event_args):
    result = alert(
      title=f"Set {self.set_index + 1}",
      content="Choose an action",
      buttons=[("Add Set Below", "add"), ("Delete Set", "delete"), ("Cancel", None)],
      dismissible=True,
    )
    if result == "add":
      self.raise_event("x-add-set-below", exercise_index=self.exercise_index, set_index=self.set_index)
    elif result == "delete":
      self.raise_event("x-delete-set", exercise_index=self.exercise_index, set_index=self.set_index)
