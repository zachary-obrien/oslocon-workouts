from ._anvil_designer import Form1Template
from anvil import *
import anvil.server
import anvil.users

ADMIN_EMAIL = "zachary.a.ob@gmail.com"
IMAGE_BATCH_SIZE = 50


class Form1(Form1Template):
  def __init__(self, **properties):
    self.init_components(**properties)

    if anvil.users.get_user() is None:
      anvil.users.login_with_google()

    self._ensure_ui()

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

    self.bootstrap_button.set_event_handler("click", self.bootstrap_button_click)

  def bootstrap_button_click(self, **event_args):
    if not self.file_loader_1.file:
      alert("Choose the exercise zip first.")
      return

    self.bootstrap_button.enabled = False
    self.file_loader_1.enabled = False
    self.status_label.text = "Starting import..."

    try:
      self._run_full_import()
    except Exception as e:
      self.status_label.text = f"Import failed: {e}"
      alert(f"Import failed:\n\n{e}")
    finally:
      self.bootstrap_button.enabled = True
      self.file_loader_1.enabled = True

  def _run_full_import(self):
    zip_file = self.file_loader_1.file

    self.status_label.text = "Seeding admin + messages..."
    seed_result = anvil.server.call("seed_reference_data", ADMIN_EMAIL)

    self.status_label.text = "Importing exercise rows..."
    catalog_result = anvil.server.call("import_exercise_catalog", zip_file, ADMIN_EMAIL)

    total_images = catalog_result.get("image_refs_in_json", 0)
    imported_total = 0
    skipped_total = 0
    failed_total = 0
    all_errors = []

    start_index = 0
    batch_number = 1

    while True:
      self.status_label.text = f"Importing images... batch {batch_number} ({imported_total + skipped_total + failed_total}/{total_images})"

      batch_result = anvil.server.call(
        "import_exercise_images_batch",
        zip_file,
        start_index,
        IMAGE_BATCH_SIZE,
        True
      )

      imported_total += batch_result.get("imported", 0)
      skipped_total += batch_result.get("skipped", 0)
      failed_total += batch_result.get("failed", 0)
      all_errors.extend(batch_result.get("errors", []))

      if batch_result.get("done"):
        break

      start_index = batch_result.get("next_index", 0)
      batch_number += 1

    self.status_label.text = (
      f"Done. Exercises created: {catalog_result.get('created', 0)}, "
      f"updated: {catalog_result.get('updated', 0)}, "
      f"images imported: {imported_total}, skipped: {skipped_total}, failed: {failed_total}."
    )

    summary = (
      f"Admin user: {seed_result.get('admin_email')}\n"
      f"Completion messages created: {seed_result.get('completion_messages_created', 0)}\n\n"
      f"Exercises in zip: {catalog_result.get('exercises_total_in_zip', 0)}\n"
      f"Exercises created: {catalog_result.get('created', 0)}\n"
      f"Exercises updated: {catalog_result.get('updated', 0)}\n"
      f"Image refs in JSON: {catalog_result.get('image_refs_in_json', 0)}\n"
      f"Images imported: {imported_total}\n"
      f"Images skipped: {skipped_total}\n"
      f"Images failed: {failed_total}"
    )

    if all_errors:
      preview = "\n".join(all_errors[:10])
      summary += f"\n\nFirst errors:\n{preview}"

    alert(summary, title="Import Complete")