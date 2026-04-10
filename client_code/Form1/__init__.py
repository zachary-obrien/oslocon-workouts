from ._anvil_designer import Form1Template
from anvil import *
import anvil.server
import anvil.users


class Form1(Form1Template):
  def __init__(self, **properties):
    self.init_components(**properties)

    if anvil.users.get_user() is None:
      anvil.users.login_with_google()

    self._ensure_ui()
    self.status_label.text = "Ready. Click to seed completion messages."
    self.bootstrap_button.text = "Seed Completion Messages"

  def _ensure_ui(self):
    if not hasattr(self, "bootstrap_button"):
      self.bootstrap_button = Button(
        text="Seed Completion Messages",
        role="filled-button"
      )
      self.add_component(self.bootstrap_button)

    if not hasattr(self, "status_label"):
      self.status_label = Label(text="")
      self.add_component(self.status_label)

    self.bootstrap_button.set_event_handler("click", self.bootstrap_button_click)

  def bootstrap_button_click(self, **event_args):
    self.bootstrap_button.enabled = False
    self.status_label.text = "Seeding completion messages..."

    try:
      result = anvil.server.call("seed_completion_messages_full", False)

      added = result["added"]
      totals = result["totals"]

      self.status_label.text = (
        f"Done. Totals — skipped: {totals['skipped']}, "
        f"standard: {totals['standard']}, "
        f"exceeded: {totals['exceeded']}"
      )

      alert(
        f"Messages added — skipped: {added['skipped']}, "
        f"standard: {added['standard']}, "
        f"exceeded: {added['exceeded']}\n\n"
        f"Totals — skipped: {totals['skipped']}, "
        f"standard: {totals['standard']}, "
        f"exceeded: {totals['exceeded']}",
        title="Completion Messages Seeded"
      )

    except Exception as e:
      self.status_label.text = f"Seeding failed: {e}"
      alert(f"Seeding failed:\n\n{e}")

    finally:
      self.bootstrap_button.enabled = True