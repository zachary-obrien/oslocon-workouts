from ._anvil_designer import WorkoutCompleteModalTemplate
from anvil import *
import anvil.js


class WorkoutCompleteModal(WorkoutCompleteModalTemplate):
    def __init__(self, summary=None, **properties):
        self.init_components(**properties)
        self.summary = summary or {}
        self._build_ui()

    def _build_ui(self):
        self.root = LinearPanel()
        self.add_component(self.root)

        self.root.add_component(Label(text=self.summary.get("headline", "Great work"), bold=True, font_size=22))
        self.root.add_component(Label(text=self.summary.get("message", "")))
        self.root.add_component(Label(text="Oslocon Workout!", bold=True, font_size=18))
        self.root.add_component(Label(text=self.summary.get("date", "")))

        tile_row = FlowPanel(spacing="tiny")
        for state in self.summary.get("tile_states", []):
            color = {
                "green": "#1fa36a",
                "orange": "#d98d2b",
                "red": "#c65151",
                "gray": "#7d8796",
            }.get(state, "#7d8796")
            tile = Label(text="  ", background=color, border="1px solid rgba(255,255,255,0.1)")
            tile.width = 20
            tile_row.add_component(tile)
        self.root.add_component(tile_row)

        if self.summary.get("show_confetti"):
            self.root.add_component(Label(text="✨ 🎉 ✨", align="center", font_size=24))

        self.share_box = TextArea(text=self.summary.get("share_text", ""), height=120)
        self.root.add_component(self.share_box)

        row = FlowPanel(spacing="medium")
        self.root.add_component(row)
        copy_btn = Button(text="Copy", role="filled-button")
        close_btn = Button(text="Close")
        row.add_component(copy_btn)
        row.add_component(close_btn)

        copy_btn.set_event_handler("click", self.copy_clicked)
        close_btn.set_event_handler("click", lambda **e: self.raise_event("x-close-alert", value=True))

    def copy_clicked(self, **event_args):
        try:
            anvil.js.window.navigator.clipboard.writeText(self.share_box.text)
            Notification("Copied to clipboard.", style="success").show()
        except Exception:
            self.share_box.focus()
            self.share_box.select()
            Notification("Clipboard copy unavailable. Share text selected.", style="warning").show()
