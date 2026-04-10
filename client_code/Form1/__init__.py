from ._anvil_designer import Form1Template
from anvil import *
import anvil.server
import anvil.users

ADMIN_EMAIL = "zachary.a.ob@gmail.com"
IMAGE_BATCH_SIZE = 5


class Form1(Form1Template):
  def __init__(self, **properties):
    self.init_components(**properties)

    if anvil.users.get_user() is None:
      anvil.users.login_with_google()

    self._ensure_ui()

    self.import_in_progress = False
    self.import_zip = None
    self.next_index = 0
    self.batch_number = 0
    self.total_images = 0
    self.imported_total = 0
    self.skipped_total = 0
    self.failed_total = 0
    self.all_errors = []
    self.catalog_result = None
    self.seed_result = None

    self.status_label.text = "Ready. Choose the exercise zip, then click the button."
    self.bootstrap_button.text = "Import Exercise Database"

  def _ensure_ui(self):
    if not hasattr(self, "file_loader_1"):
      self.file_loader_1 = FileLoader(text="Choose exercise zip")
      self.add_component(self.file_loader_1)

    if not hasattr(self, "bootstrap_button"):
      self.bootstrap_button = Button(text="Import Exercise Database", role="filled-button")
      self.add_component(self.bootstrap_button)

    if not hasattr(self, "status_label"):
      self.status_label = Label(text="")
      self.add_component(self.status_label)

    if not hasattr(self, "import_timer"):
      self.import_timer = Timer(interval=0)
      self.add_component(self.import_timer)

    self.bootstrap_button.set_event_handler("click", self.bootstrap_button_click)
    self.import_timer.set_event_handler("tick", self.import_timer_tick)

  def bootstrap_button_click(self, **event_args):
    if self.import_in_progress:
      return

    if not self.file_loader_1.file:
      alert("Choose the exercise zip first.")
      return

    self.bootstrap_button.enabled = False
    self.file_loader_1.enabled = False
    self.status_label.text = "Starting import..."

    try:
      self.import_zip = self.file_loader_1.file

      self.status_label.text = "Seeding admin + messages..."
      self.seed_result = anvil.server.call("seed_reference_data", ADMIN_EMAIL)

      self.status_label.text = "Importing exercise rows..."
      self.catalog_result = anvil.server.call("import_exercise_catalog", self.import_zip, ADMIN_EMAIL)

      self.total_images = self.catalog_result.get("image_refs_in_json", 0)
      self.next_index = 0
      self.batch_number = 0
      self.imported_total = 0
      self.skipped_total = 0
      self.failed_total = 0
      self.all_errors = []

      self.import_in_progress = True
      self.import_timer.interval = 0.2
      self.status_label.text = f"Queued image import. Total image refs: {self.total_images}"

    except Exception as e:
      self.status_label.text = f"Import failed: {e}"
      self.bootstrap_button.enabled = True
      self.file_loader_1.enabled = True
      alert(f"Import failed:\n\n{e}")

  def import_timer_tick(self, **event_args):
    if not self.import_in_progress:
      self.import_timer.interval = 0
      return

    self.import_timer.interval = 0
    self.batch_number += 1

    try:
      self.status_label.text = (
        f"Importing images... batch {self.batch_number} "
        f"({self.imported_total + self.skipped_total + self.failed_total}/{self.total_images})"
      )

      result = anvil.server.call(
        "import_exercise_images_batch",
        self.import_zip,
        self.next_index,
        IMAGE_BATCH_SIZE,
        True
      )

      self.imported_total += result.get("imported", 0)
      self.skipped_total += result.get("skipped", 0)
      self.failed_total += result.get("failed", 0)
      self.all_errors.extend(result.get("errors", []))

      if result.get("done"):
        self.import_in_progress = False
        self._finish_import()
        return

      self.next_index = result.get("next_index", self.next_index + IMAGE_BATCH_SIZE)
      self.import_timer.interval = 0.2

    except Exception as e:
      self.import_in_progress = False
      self.import_timer.interval = 0
      self.bootstrap_button.enabled = True
      self.file_loader_1.enabled = True
      self.status_label.text = f"Import failed on image batch {self.batch_number}: {e}"
      alert(f"Import failed on image batch {self.batch_number}:\n\n{e}")

  def _finish_import(self):
    self.bootstrap_button.enabled = True
    self.file_loader_1.enabled = True
    self.import_timer.interval = 0

    self.status_label.text = (
      f"Done. Exercises created: {self.catalog_result.get('created', 0)}, "
      f"updated: {self.catalog_result.get('updated', 0)}, "
      f"images imported: {self.imported_total}, skipped: {self.skipped_total}, failed: {self.failed_total}."
    )

    summary = (
      f"Admin user: {self.seed_result.get('admin_email')}\n"
      f"Completion messages created: {self.seed_result.get('completion_messages_created', 0)}\n\n"
      f"Exercises in zip: {self.catalog_result.get('exercises_total_in_zip', 0)}\n"
      f"Exercises created: {self.catalog_result.get('created', 0)}\n"
      f"Exercises updated: {self.catalog_result.get('updated', 0)}\n"
      f"Image refs in JSON: {self.catalog_result.get('image_refs_in_json', 0)}\n"
      f"Images imported: {self.imported_total}\n"
      f"Images skipped: {self.skipped_total}\n"
      f"Images failed: {self.failed_total}"
    )

    if self.all_errors:
      summary += "\n\nFirst errors:\n" + "\n".join(self.all_errors[:10])

    alert(summary, title="Import Complete")