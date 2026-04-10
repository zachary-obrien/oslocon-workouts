from ._anvil_designer import HistoryFormTemplate
from anvil import *
import anvil.server


class HistoryForm(HistoryFormTemplate):
  def __init__(self, **properties):
    self.init_components(**properties)
    self._build_ui()
    self.refresh_history()

  def _build_ui(self):
    self.root = LinearPanel()
    self.add_component(self.root)
    self.root.add_component(Label(text="Workout History", bold=True, font_size=24))
    self.list_panel = LinearPanel(spacing="small")
    self.root.add_component(self.list_panel)

  def refresh_history(self):
    self.list_panel.clear()
    items = anvil.server.call("get_recent_history", 25) or []

    if not items:
      self.list_panel.add_component(Label(text="No completed workouts yet.", foreground="#97a5b7"))
      return

    for item in items:
      card = ColumnPanel(background="#141c26", foreground="#f3f6fb", border="1px solid #283548")
      day_code = item.get("day_code") or "—"
      completed_at = item.get("completed_at") or "—"
      bucket = item.get("completion_bucket") or "—"

      card.add_component(Label(text=f"Day {day_code} • {completed_at}", bold=True))
      card.add_component(Label(text=f"Bucket: {bucket}"))

      share_text = item.get("share_text")
      if share_text:
        card.add_component(Label(text=share_text))

      self.list_panel.add_component(card, full_width_row=True)