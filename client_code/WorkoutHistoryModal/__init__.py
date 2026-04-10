from ._anvil_designer import WorkoutHistoryModalTemplate
from anvil import *


class WorkoutHistoryModal(WorkoutHistoryModalTemplate):
    def __init__(self, exercise_name="", history_items=None, **properties):
        self.init_components(**properties)
        self.exercise_name = exercise_name
        self.history_items = history_items or []
        self._build_ui()

    def _build_ui(self):
        self.root = LinearPanel()
        self.add_component(self.root)
        self.root.add_component(Label(text=self.exercise_name, bold=True, font_size=20))
        if not self.history_items:
            self.root.add_component(Label(text="No history yet."))
            return

        for item in self.history_items:
            card = ColumnPanel(background="#141c26", foreground="#f3f6fb", border="1px solid #283548")
            card.add_component(Label(text=f"Day {item['day_code']} • {item['completed_at']}", bold=True))
            card.add_component(Label(text=f"Status: {item['status']}"))
            summary = ", ".join([f"{s['weight']} x {s['reps']}" for s in item.get("sets", [])])
            card.add_component(Label(text=summary or "No set data"))
            self.root.add_component(card, full_width_row=True)
