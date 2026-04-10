from ._anvil_designer import Form1Template
from anvil import *
import anvil.server
import anvil.users

ADMIN_EMAIL = "zachary.a.ob@gmail.com"
ZIP_FILENAME = "exercises.zip"
EXERCISE_BATCH_SIZE = 20
IMAGE_BATCH_SIZE = 1


class Form1(Form1Template):
  def __init__(self, **properties):
    self.init_components(**properties)

    if anvil.users.get_user() is None:
      anvil.users.login_with_google()

    self._ensure_ui()

    self.phase = None
    self.import_in_progress = False

    self.manifest = None
    self.exercise_next_index = 0
    self.image_next_index = 0

    self.exercise_created_total = 0
    self.exercise_updated_total = 0
    self.image_imported_total = 0
    self.image_skipped_total = 0
    self.image_failed_total = 0
    self.all_errors = []

    self.status_label.text = f"Ready. Click to import from Data Files: {ZIP_FILENAME}"
    self.bootstrap_button.text = "Import Exercise Database"

  def _ensure_ui(self):
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

    self.bootstrap_button.enabled = False
    self.status_label.text = f"Preparing import from Data File: {ZIP_FILENAME}"

    try:
      self.manifest = anvil.server.call(
        "prepare_exercise_import_from_data_file",
        ZIP_FILENAME,
        ADMIN_EMAIL
      )

      self.phase = "exercise_catalog"
      self.import_in_progress = True
      self.exercise_next_index = 0
      self.image_next_index = 0
      self.exercise_created_total = 0
      self.exercise_updated_total = 0
      self.image_imported_total = 0
      self.image_skipped_total = 0
      self.image_failed_total = 0
      self.all_errors = []

      self.status_label.text = (
        f"Starting import. Exercises: {self.manifest['exercise_count']}, "
        f"Images: {self.manifest['image_count']}"
      )
      self.import_timer.interval = 0.2

    except Exception as e:
      self.import_in_progress = False
      self.import_timer.interval = 0
      self.bootstrap_button.enabled = True
      self.status_label.text = f"Import failed: {e}"
      alert(f"Import failed:\n\n{e}")

  def import_timer_tick(self, **event_args):
    if not self.import_in_progress:
      self.import_timer.interval = 0
      return

    self.import_timer.interval = 0

    try:
      if self.phase == "exercise_catalog":
        self._run_exercise_batch()
      elif self.phase == "exercise_images":
        self._run_image_batch()
      else:
        raise Exception(f"Unknown import phase: {self.phase}")

    except Exception as e:
      self.import_in_progress = False
      self.import_timer.interval = 0
      self.bootstrap_button.enabled = True
      try:
        anvil.server.call("finish_exercise_import")
      except Exception:
        pass
      self.status_label.text = f"Import failed: {e}"
      alert(f"Import failed:\n\n{e}")

  def _run_exercise_batch(self):
    total = self.manifest["exercise_count"]
    self.status_label.text = f"Importing exercises... ({self.exercise_next_index}/{total})"

    result = anvil.server.call(
      "import_exercise_catalog_batch",
      self.exercise_next_index,
      EXERCISE_BATCH_SIZE
    )

    self.exercise_created_total += result.get("created", 0)
    self.exercise_updated_total += result.get("updated", 0)

    if result.get("done"):
      self.phase = "exercise_images"
      self.image_next_index = 0
      self.import_timer.interval = 0.2
      return

    self.exercise_next_index = result.get("next_index", self.exercise_next_index + EXERCISE_BATCH_SIZE)
    self.import_timer.interval = 0.2

  def _run_image_batch(self):
    total = self.manifest["image_count"]
    self.status_label.text = f"Importing images... ({self.image_next_index}/{total})"

    result = anvil.server.call(
      "import_exercise_images_batch",
      self.image_next_index,
      IMAGE_BATCH_SIZE
    )

    self.image_imported_total += result.get("imported", 0)
    self.image_skipped_total += result.get("skipped", 0)
    self.image_failed_total += result.get("failed", 0)
    self.all_errors.extend(result.get("errors", []))

    if result.get("done"):
      self._finish_import()
      return

    self.image_next_index = result.get("next_index", self.image_next_index + IMAGE_BATCH_SIZE)
    self.import_timer.interval = 0.2

  def _finish_import(self):
    self.import_in_progress = False
    self.import_timer.interval = 0
    self.bootstrap_button.enabled = True

    try:
      anvil.server.call("finish_exercise_import")
    except Exception:
      pass

    self.status_label.text = (
      f"Done. Exercises created: {self.exercise_created_total}, "
      f"updated: {self.exercise_updated_total}, "
      f"images imported: {self.image_imported_total}, "
      f"skipped: {self.image_skipped_total}, "
      f"failed: {self.image_failed_total}."
    )

    summary = (
      f"Admin user: {self.manifest.get('admin_email')}\n"
      f"Completion messages created: {self.manifest.get('completion_messages_created', 0)}\n\n"
      f"Exercises in zip: {self.manifest.get('exercise_count', 0)}\n"
      f"Image refs in zip/json: {self.manifest.get('image_count', 0)}\n"
      f"Exercises created: {self.exercise_created_total}\n"
      f"Exercises updated: {self.exercise_updated_total}\n"
      f"Images imported: {self.image_imported_total}\n"
      f"Images skipped: {self.image_skipped_total}\n"
      f"Images failed: {self.image_failed_total}"
    )

    if self.all_errors:
      summary += "\n\nFirst errors:\n" + "\n".join(self.all_errors[:10])

    alert(summary, title="Import Complete")