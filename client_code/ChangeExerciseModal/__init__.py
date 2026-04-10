from ._anvil_designer import ChangeExerciseModalTemplate
from anvil import *
import anvil.server


class ChangeExerciseModal(ChangeExerciseModalTemplate):
    def __init__(self, current_name="", **properties):
        self.init_components(**properties)
        self.current_name = current_name or ""
        self._build_ui()
        self.search_box.text = self.current_name
        self.search()

    def _build_ui(self):
        self.root = LinearPanel()
        self.add_component(self.root)
        self.root.add_component(Label(text="Change Exercise", bold=True, font_size=20))

        search_row = FlowPanel(align="left", spacing="small")
        self.root.add_component(search_row)
        self.search_box = TextBox(placeholder="Search exercises...")
        self.search_btn = Button(text="Search", role="filled-button")
        search_row.add_component(self.search_box)
        search_row.add_component(self.search_btn)

        self.results_panel = LinearPanel(spacing="small")
        self.root.add_component(self.results_panel)

        self.search_btn.set_event_handler("click", self.search)
        self.search_box.set_event_handler("pressed_enter", self.search)

    def search(self, **event_args):
        results = anvil.server.call("search_exercise_options", self.search_box.text or "")
        self.results_panel.clear()
        for result in results:
            btn = Button(text=f"{result['name']} • {result['group_size']}", align="left")
            btn.tag.exercise_id = result["exercise_id"]
            btn.set_event_handler("click", self.choose_result)
            self.results_panel.add_component(btn)

    def choose_result(self, **event_args):
        exercise_id = event_args["sender"].tag.exercise_id
        self.raise_event("x-close-alert", value={"action": "choose", "exercise_id": exercise_id})
