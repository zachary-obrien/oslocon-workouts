import anvil.server
import anvil.users

from anvil import BlobMedia
from anvil.files import data_files
from anvil.tables import app_tables
from datetime import datetime

import json
import mimetypes
import os
import re
import uuid
import zipfile


DEFAULT_ADMIN_EMAIL = "zachary.a.ob@gmail.com"
DEFAULT_SOURCE = "import"
DEFAULT_SOURCE_VERSION = "free-exercise-db"

DEFAULT_EXERCISE_BATCH_SIZE = 20
DEFAULT_IMAGE_BATCH_SIZE = 1
SESSION_KEY = "exercise_import_ctx"

USER_COLUMN_DEFAULTS = {
  "display_name": "Bootstrap User",
  "progress_every_n_qualifying_workouts": 3,
  "timezone": "America/Chicago",
  "role": "user",
  "is_admin": False,
  "onboarding_complete": False,
  "created_via": "google",
  "stripe_customer_id": "",
  "plan_tier": "free",
}


def _now():
  return datetime.now()


def _require_table(table_name):
  try:
    return getattr(app_tables, table_name)
  except AttributeError:
    raise Exception(f"Missing Data Table: {table_name}")


def _safe_text(value):
  return "" if value is None else str(value)


def _safe_list(value):
  if isinstance(value, list):
    return [str(x) for x in value]
  return []


def _normalize_name(name):
  return re.sub(r"\s+", " ", (name or "").strip().lower())


def _derive_group_size(exercise_dict):
  primary = {m.lower() for m in _safe_list(exercise_dict.get("primaryMuscles"))}
  large_groups = {
    "chest",
    "lats",
    "middle back",
    "lower back",
    "back",
    "quadriceps",
    "hamstrings",
    "glutes",
    "abdominals",
    "shoulders",
    "traps",
  }
  return "Large" if primary & large_groups else "Small"


def _uses_bodyweight_default(exercise_dict):
  equipment = _safe_text(exercise_dict.get("equipment")).strip().lower()
  return equipment == "body only"


def _set_row_values(row, values):
  for key, value in values.items():
    row[key] = value


def _find_user_by_email(email):
  target = (email or "").strip().lower()
  if not target:
    return None

  for row in app_tables.users.search():
    row_email = (row["email"] or "").strip().lower()
    if row_email == target:
      return row

  return None


def _ensure_admin_user(email=DEFAULT_ADMIN_EMAIL):
  user = _find_user_by_email(email)
  if user is None:
    raise Exception(
      f"No Users row found for {email}. "
      f"Sign in once with that Google account first, or change ADMIN_EMAIL."
    )

  updates = {}

  if not user["display_name"]:
    updates["display_name"] = (email.split("@")[0] or "Admin").replace(".", " ").title()

  if user["progress_every_n_qualifying_workouts"] is None:
    updates["progress_every_n_qualifying_workouts"] = 3

  if not user["timezone"]:
    updates["timezone"] = "America/Chicago"

  if not user["role"]:
    updates["role"] = "admin"

  if not user["created_via"]:
    updates["created_via"] = "google"

  if not user["plan_tier"]:
    updates["plan_tier"] = "free"

  if user["is_admin"] is not True:
    updates["is_admin"] = True

  if user["onboarding_complete"] is not True:
    updates["onboarding_complete"] = True

  _set_row_values(user, updates)
  return user


def _ensure_completion_messages():
  defaults = [
    ("skipped", "Any progress is great progress. It all adds up.", True, 1),
    ("skipped", "Off days happen. What matters is you still showed up.", True, 2),
    ("standard", "Great work. Another workout in the bank.", True, 1),
    ("standard", "Solid work today. Keep stacking them.", True, 2),
    ("exceeded", "You pushed beyond the plan today. That extra effort matters.", True, 1),
    ("exceeded", "You beat the target today. Keep that momentum rolling.", True, 2),
  ]

  existing = set()
  for row in app_tables.completion_messages.search():
    existing.add((_safe_text(row["bucket"]), _safe_text(row["message"])))

  created = 0
  for bucket, message, active, sort_order in defaults:
    if (bucket, message) in existing:
      continue

    app_tables.completion_messages.add_row(
      bucket=bucket,
      message=message,
      active=active,
      sort_order=sort_order,
    )
    created += 1

  return created


def _cleanup_old_context():
  ctx = anvil.server.session.get(SESSION_KEY)
  if not ctx:
    return

  for key in ("exercises_path", "image_plan_path"):
    path = ctx.get(key)
    if path and os.path.exists(path):
      try:
        os.remove(path)
      except Exception:
        pass

  anvil.server.session.pop(SESSION_KEY, None)


def _write_json_to_tmp(prefix, obj):
  path = f"/tmp/{prefix}_{uuid.uuid4().hex}.json"
  with open(path, "w", encoding="utf-8") as f:
    json.dump(obj, f)
  return path


def _read_json_from_tmp(path):
  with open(path, "r", encoding="utf-8") as f:
    return json.load(f)


def _find_dist_json_member(zip_names):
  for name in zip_names:
    if name.endswith("dist/exercises.json"):
      return name
  return None


def _find_exercise_json_members(zip_names):
  pattern = re.compile(r"(^|.*/)exercises/[^/]+\.json$")
  return sorted([name for name in zip_names if pattern.search(name)])


def _load_exercises_data_and_prefix(zip_path):
  with zipfile.ZipFile(zip_path, "r") as zf:
    names = zf.namelist()

    dist_member = _find_dist_json_member(names)
    if dist_member:
      raw = zf.read(dist_member).decode("utf-8")
      data = json.loads(raw)
      if not isinstance(data, list):
        raise Exception("dist/exercises.json is not a list.")
      root_prefix = dist_member[:-len("dist/exercises.json")]
      return data, root_prefix

    json_members = _find_exercise_json_members(names)
    if not json_members:
      raise Exception("Could not find dist/exercises.json or exercises/<exercise>.json in the zip.")

    data = []
    root_prefix = None

    for member in json_members:
      raw = zf.read(member).decode("utf-8")
      obj = json.loads(raw)
      if isinstance(obj, dict):
        data.append(obj)
      if root_prefix is None:
        idx = member.rfind("exercises/")
        root_prefix = member[:idx] if idx >= 0 else ""

    return data, (root_prefix or "")


def _build_image_plan(exercises_data):
  plan = []
  for exercise_dict in exercises_data:
    ext_id = _safe_text(exercise_dict.get("id")).strip()
    images = _safe_list(exercise_dict.get("images"))
    for idx, rel_path in enumerate(images):
      plan.append({
        "external_id": ext_id,
        "relative_path": rel_path,
        "sort_order": idx + 1,
        "label": str(idx + 1),
      })
  return plan


def _get_import_context():
  ctx = anvil.server.session.get(SESSION_KEY)
  if not ctx:
    raise Exception("No active import context. Start the import again.")
  return ctx


def _build_existing_exercise_maps():
  by_external_id = {}
  by_normalized_name = {}

  for row in app_tables.exercises.search():
    ext_id = _safe_text(row["external_id"]).strip()
    if ext_id:
      by_external_id[ext_id] = row

    norm = _normalize_name(row["normalized_name"] or row["name"] or "")
    if norm:
      by_normalized_name[norm] = row

  return by_external_id, by_normalized_name


def _upsert_exercise_with_maps(exercise_dict, by_external_id, by_normalized_name):
  ext_id = _safe_text(exercise_dict.get("id")).strip()
  name = _safe_text(exercise_dict.get("name")).strip()
  normalized_name = _normalize_name(name)

  row = None
  if ext_id and ext_id in by_external_id:
    row = by_external_id[ext_id]
  elif normalized_name and normalized_name in by_normalized_name:
    row = by_normalized_name[normalized_name]

  values = {
    "external_id": ext_id,
    "source": DEFAULT_SOURCE,
    "source_version": DEFAULT_SOURCE_VERSION,
    "name": name,
    "normalized_name": normalized_name,
    "category": _safe_text(exercise_dict.get("category")),
    "force": _safe_text(exercise_dict.get("force")),
    "level": _safe_text(exercise_dict.get("level")),
    "mechanic": _safe_text(exercise_dict.get("mechanic")),
    "equipment": _safe_text(exercise_dict.get("equipment")),
    "primary_muscles": _safe_list(exercise_dict.get("primaryMuscles")),
    "secondary_muscles": _safe_list(exercise_dict.get("secondaryMuscles")),
    "instructions": _safe_list(exercise_dict.get("instructions")),
    "group_size": _derive_group_size(exercise_dict),
    "uses_bodyweight_default": _uses_bodyweight_default(exercise_dict),
    "is_active": True,
    "created_by_user": None,
    "updated_at": _now(),
  }

  if row is not None:
    _set_row_values(row, values)
    if ext_id:
      by_external_id[ext_id] = row
    if normalized_name:
      by_normalized_name[normalized_name] = row
    return "updated"

  values["created_at"] = _now()
  new_row = app_tables.exercises.add_row(**values)
  if ext_id:
    by_external_id[ext_id] = new_row
  if normalized_name:
    by_normalized_name[normalized_name] = new_row
  return "created"


def _get_exercise_row_by_external_id(ext_id):
  return app_tables.exercises.get(external_id=ext_id)


def _find_zip_image_member(zip_names, root_prefix, rel_path):
  candidates = [
    rel_path,
    f"exercises/{rel_path}",
    f"{root_prefix}exercises/{rel_path}",
  ]

  name_set = set(zip_names)
  for candidate in candidates:
    if candidate in name_set:
      return candidate

  return None


def _blob_media_from_bytes(file_bytes, rel_path):
  file_name = rel_path.split("/")[-1]
  ctype = mimetypes.guess_type(file_name)[0] or "application/octet-stream"
  return BlobMedia(content_type=ctype, content=file_bytes, name=file_name)


@anvil.server.callable
def prepare_exercise_import_from_data_file(zip_filename="exercises.zip", admin_email=DEFAULT_ADMIN_EMAIL):
  _require_table("exercises")
  _require_table("exercise_images")
  _require_table("completion_messages")

  _cleanup_old_context()

  zip_path = data_files[zip_filename]
  admin_user = _ensure_admin_user(admin_email)
  created_messages = _ensure_completion_messages()

  exercises_data, root_prefix = _load_exercises_data_and_prefix(zip_path)
  image_plan = _build_image_plan(exercises_data)

  exercises_path = _write_json_to_tmp("exercise_data", exercises_data)
  image_plan_path = _write_json_to_tmp("exercise_image_plan", image_plan)

  anvil.server.session[SESSION_KEY] = {
    "zip_path": str(zip_path),
    "zip_root_prefix": root_prefix,
    "exercises_path": exercises_path,
    "image_plan_path": image_plan_path,
    "zip_filename": zip_filename,
  }

  return {
    "admin_email": admin_user["email"],
    "completion_messages_created": created_messages,
    "exercise_count": len(exercises_data),
    "image_count": len(image_plan),
  }


@anvil.server.callable
def import_exercise_catalog_batch(start_index=0, batch_size=DEFAULT_EXERCISE_BATCH_SIZE):
  _require_table("exercises")
  ctx = _get_import_context()

  exercises_data = _read_json_from_tmp(ctx["exercises_path"])

  start_index = int(start_index or 0)
  batch_size = int(batch_size or DEFAULT_EXERCISE_BATCH_SIZE)

  if start_index < 0:
    start_index = 0
  if batch_size < 1:
    batch_size = DEFAULT_EXERCISE_BATCH_SIZE

  batch = exercises_data[start_index:start_index + batch_size]
  by_external_id, by_normalized_name = _build_existing_exercise_maps()

  created = 0
  updated = 0

  for exercise_dict in batch:
    action = _upsert_exercise_with_maps(exercise_dict, by_external_id, by_normalized_name)
    if action == "created":
      created += 1
    else:
      updated += 1

  next_index = start_index + len(batch)
  done = next_index >= len(exercises_data)

  return {
    "start_index": start_index,
    "batch_size": batch_size,
    "processed": len(batch),
    "created": created,
    "updated": updated,
    "next_index": None if done else next_index,
    "done": done,
    "total_exercises": len(exercises_data),
  }


@anvil.server.callable
def import_exercise_images_batch(start_index=0, batch_size=DEFAULT_IMAGE_BATCH_SIZE):
  _require_table("exercise_images")
  _require_table("exercises")

  ctx = _get_import_context()
  image_plan = _read_json_from_tmp(ctx["image_plan_path"])
  zip_path = ctx["zip_path"]
  root_prefix = ctx["zip_root_prefix"]

  start_index = int(start_index or 0)
  batch_size = int(batch_size or DEFAULT_IMAGE_BATCH_SIZE)

  if start_index < 0:
    start_index = 0
  if batch_size < 1:
    batch_size = DEFAULT_IMAGE_BATCH_SIZE

  batch = image_plan[start_index:start_index + batch_size]

  imported = 0
  skipped = 0
  failed = 0
  errors = []

  with zipfile.ZipFile(zip_path, "r") as zf:
    zip_names = zf.namelist()

    for item in batch:
      ext_id = item["external_id"]
      rel_path = item["relative_path"]
      sort_order = item["sort_order"]
      label = item["label"]

      exercise_row = _get_exercise_row_by_external_id(ext_id)
      if exercise_row is None:
        failed += 1
        errors.append(f"Missing exercise row for external_id={ext_id}")
        continue

      existing = app_tables.exercise_images.get(
        exercise=exercise_row,
        source_filename=rel_path
      )
      if existing:
        skipped += 1
        continue

      try:
        member = _find_zip_image_member(zip_names, root_prefix, rel_path)
        if not member:
          raise Exception("Image file not found inside zip")

        media = _blob_media_from_bytes(zf.read(member), rel_path)

        app_tables.exercise_images.add_row(
          exercise=exercise_row,
          image=media,
          sort_order=sort_order,
          label=label,
          source_filename=rel_path,
          created_at=_now(),
        )
        imported += 1
      except Exception as e:
        failed += 1
        errors.append(f"{rel_path}: {e}")

  next_index = start_index + len(batch)
  done = next_index >= len(image_plan)

  return {
    "start_index": start_index,
    "batch_size": batch_size,
    "processed": len(batch),
    "imported": imported,
    "skipped": skipped,
    "failed": failed,
    "next_index": None if done else next_index,
    "done": done,
    "total_images_in_plan": len(image_plan),
    "errors": errors[:20],
  }


@anvil.server.callable
def finish_exercise_import():
  _cleanup_old_context()
  return True