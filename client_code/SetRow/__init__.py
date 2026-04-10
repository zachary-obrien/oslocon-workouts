from ._anvil_designer import SetRowTemplate
from anvil import *


def _weight_options(uses_bodyweight):
    if uses_bodyweight:
        return [("BW", "BW")]
    vals = []
    x = 5.0
    while x <= 300:
        label = f"{int(x) if float(x).is_integer() else x:g}"
        vals.append((label, x))
        x += 2.5
    return vals


def _rep_options():
    return [(str(i), i) for i in range(3, 31)]


class SetRow(SetRowTemplate):
    def __init__(self, exercise_index=0, set_index=0, set_data=None, uses_bodyweight=False, **properties):
        self.init_components(**properties)
        self.exercise_index = exercise_index
        self.set_index = set_index
        self.set_data = dict(set_data or {})
        self.uses_bodyweight = uses_bodyweight
        self.menu_open = False
        self._build_ui()
        self.render()

    def _build_ui(self):
        self.root = ColumnPanel(role="set-row")
        self.add_component(self.root)

        self.grid = GridPanel()
        self.root.add_component(self.grid, full_width_row=True)
        self.menu_btn = Button(text="⋯", role="icon-button")
        self.grid.add_component(self.menu_btn, row="A", col_xs=0, width_xs=1)

        self.controls = FlowPanel(align="center")
        self.weight_dd = DropDown(include_placeholder=False, role="select")
        self.weight_lbl = Label(text="lb", role="muted", spacing_above="none", spacing_below="none")
        self.reps_dd = DropDown(include_placeholder=False, role="select")
        self.reps_lbl = Label(text="reps", role="muted", spacing_above="none", spacing_below="none")
        self.controls.add_component(self.weight_dd)
        self.controls.add_component(self.weight_lbl)
        self.controls.add_component(self.reps_dd)
        self.controls.add_component(self.reps_lbl)
        self.grid.add_component(self.controls, row="A", col_xs=1, width_xs=10)

        self.check_btn = Button(text="✓", role="check-button")
        self.grid.add_component(self.check_btn, row="A", col_xs=11, width_xs=1)

        self.menu_panel = LinearPanel(role="inline-menu", visible=False, spacing="none")
        self.root.add_component(self.menu_panel, full_width_row=True)
        self.add_btn = Button(text="Add set below", role="menu-item")
        self.delete_btn = Button(text="Delete set", role="menu-item-danger")
        self.menu_panel.add_component(self.add_btn)
        self.menu_panel.add_component(self.delete_btn)

        self.menu_btn.set_event_handler("click", self.toggle_menu)
        self.weight_dd.set_event_handler("change", self.value_changed)
        self.reps_dd.set_event_handler("change", self.value_changed)
        self.check_btn.set_event_handler("click", self.toggle_done)
        self.add_btn.set_event_handler("click", self.add_below)
        self.delete_btn.set_event_handler("click", self.delete_self)

    def render(self):
        self.root.role = "set-row set-row-done" if self.set_data.get("performed") else "set-row"
        self.weight_dd.items = _weight_options(self.uses_bodyweight)
        self.reps_dd.items = _rep_options()
        self.weight_dd.selected_value = self.set_data.get("weight")
        self.reps_dd.selected_value = self.set_data.get("reps")
        self.weight_lbl.visible = not self.uses_bodyweight
        self.menu_panel.visible = self.menu_open
        self.check_btn.role = "check-button check-button-checked" if self.set_data.get("performed") else "check-button"
        self.check_btn.text = "✓" if self.set_data.get("performed") else ""

    def toggle_menu(self, **event_args):
        self.menu_open = not self.menu_open
        self.render()

    def value_changed(self, **event_args):
        self.set_data["weight"] = self.weight_dd.selected_value
        self.set_data["reps"] = self.reps_dd.selected_value
        self.raise_event("x-set-changed", exercise_index=self.exercise_index, set_index=self.set_index, set_data=dict(self.set_data))

    def toggle_done(self, **event_args):
        self.set_data["performed"] = not self.set_data.get("performed")
        self.render()
        self.raise_event("x-set-changed", exercise_index=self.exercise_index, set_index=self.set_index, set_data=dict(self.set_data))

    def add_below(self, **event_args):
        self.menu_open = False
        self.render()
        self.raise_event("x-add-set-below", set_index=self.set_index)

    def delete_self(self, **event_args):
        self.menu_open = False
        self.render()
        self.raise_event("x-delete-set", set_index=self.set_index)
