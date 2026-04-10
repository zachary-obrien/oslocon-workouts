from ._anvil_designer import SetRowTemplate
from anvil import *


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
        self.panel = GridPanel(background="#141c26", foreground="#f3f6fb", border="1px solid #283548")
        self.add_component(self.panel)

        self.menu_btn = Button(text="⋯", width=36)
        self.weight_dd = DropDown(include_placeholder=False, width=110, items=_weight_options(self.uses_bodyweight))
        self.reps_dd = DropDown(include_placeholder=False, width=110, items=_rep_options())
        self.check_box = CheckBox(text="Done")

        self.panel.add_component(self.menu_btn, row="A", col_xs=0, width_xs=2)
        self.panel.add_component(self.weight_dd, row="A", col_xs=2, width_xs=4)
        self.panel.add_component(self.reps_dd, row="A", col_xs=6, width_xs=3)
        self.panel.add_component(self.check_box, row="A", col_xs=9, width_xs=3)

        self.menu_btn.set_event_handler("click", self.menu_btn_click)
        self.weight_dd.set_event_handler("change", self.value_changed)
        self.reps_dd.set_event_handler("change", self.value_changed)
        self.check_box.set_event_handler("change", self.check_box_change)

    def _render(self):
        self.weight_dd.selected_value = self.set_data.get("weight")
        self.reps_dd.selected_value = self.set_data.get("reps")
        self.check_box.checked = bool(self.set_data.get("performed"))
        self.background = "#1a2431" if self.set_data.get("performed") else "#141c26"

    def value_changed(self, **event_args):
        self.set_data["weight"] = self.weight_dd.selected_value
        self.set_data["reps"] = self.reps_dd.selected_value
        self.raise_event("x-set-changed", exercise_index=self.exercise_index, set_index=self.set_index, set_data=self.set_data)

    def check_box_change(self, **event_args):
        self.set_data["performed"] = bool(self.check_box.checked)
        self._render()
        self.raise_event("x-set-changed", exercise_index=self.exercise_index, set_index=self.set_index, set_data=self.set_data)
        self.raise_event("x-set-check-toggled", exercise_index=self.exercise_index, set_index=self.set_index, set_data=self.set_data)

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
