import anvil.server
import anvil.users
import anvil.http

from anvil import BlobMedia
from anvil.tables import app_tables
from datetime import datetime

import io
import json
import mimetypes
import re
import zipfile


RAW_IMAGE_PREFIX = "https://raw.githubusercontent.com/yuhonas/free-exercise-db/main/exercises/"
DEFAULT_ADMIN_EMAIL = "zachary.a.ob@gmail.com"
DEFAULT_SOURCE = "import"
DEFAULT_SOURCE_VERSION = "free-exercise-db"


def _now():
  return datetime.now()


def _require_table(table_name):
  try:
    return getattr(app_tables, table_name)
  except AttributeError:
    raise Exception(f"Missing Data Table: {table_name}")


def _normalize_name(name):
  return re.sub(r"\s+", " ", (name or "").strip().lower())


def _safe_text(value):
  return "" if value is None else str(value)


def _safe_list(value):
  if isinstance(value, list):
    return [str(x) for x in value]
  return []


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
    raise Exception(f"No Users row found for {email}. Sign in with Google once first.")

  updates = {}

  if not user["display_name"]:
    local_name = (email.split("@")[0] or "Admin").replace(".", " ").title()
    updates["display_name"] = local_name

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

  if updates:
    user.update(**updates)

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


def _open_zip_media(zip_media):
  if zip_media is None:
    raise Exception("Provide the exercise zip as a Media object.")
  return zipfile.ZipFile(io.BytesIO(zip_media.get_bytes()), "r")


def _find_json_member(zip_file):
  for name in zip_file.namelist():
    if name.endswith("dist/exercises.json"):
      return name
  raise Exception("Could not find dist/exercises.json in the uploaded zip.")


def _get_zip_root_prefix(zip_file):
  json_member = _find_json_member(zip_file)
  return json_member[:-len("dist/exercises.json")]


def _load_exercises_json(zip_file):
  json_member = _find_json_member(zip_file)
  raw = zip_file.read(json_member).decode("utf-8")
  data = json.loads(raw)
  if not isinstance(data, list):
    raise Exception("dist/exercises.json did not contain a list.")
  return data


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


def _upsert_exercise(exercise_dict):
  by_external_id, by_normalized_name = _build_existing_exercise_maps()

  ext_id = _safe_text(exercise_dict.get("id")).strip()
  name = _safe_text(exercise_dict.get("name")).strip()
  normalized_name = _normalize_name(name)

  row = None
  if ext_id and ext_id in by_external_id:
    row = by_external_id[ext_id]
  elif normalized_name and normalized_name in by_normalized_name:
    row = by_normalized_name[normalized_name]

  values = dict(
    external_id=ext_id,
    source=DEFAULT_SOURCE,
    source_version=DEFAULT_SOURCE_VERSION,
    name=name,
    normalized_name=normalized_name,
    category=_safe_text(exercise_dict.get("category")),
    force=_safe_text(exercise_dict.get("force")),
    level=_safe_text(exercise_dict.get("level")),
    mechanic=_safe_text(exercise_dict.get("mechanic")),
    equipment=_safe_text(exercise_dict.get("equipment")),
    primary_muscles=_safe_list(exercise_dict.get("primaryMuscles")),
    secondary_muscles=_safe_list(exercise_dict.get("secondaryMuscles")),
    instructions=_safe_list(exercise_dict.get("instructions")),
    group_size=_derive_group_size(exercise_dict),
    uses_bodyweight_default=_uses_bodyweight_default(exercise_dict),
    is_active=True,
    created_by_user=None,
    updated_at=_now(),
  )

  if row:
    row.update(**values)
    return row, "updated"

  values["created_at"] = _now()
  new_row = app_tables.exercises.add_row(**values)
  return new_row, "created"


def _build_image_plan(exercises_data):
  plan = []
  for exercise_dict in exercises_data:
    ext_id = _safe_text(exercise_dict.get("id")).strip()
    for idx, rel_path in enumerate(_safe_list(exercise_dict.get("images"))):
      plan.append({
        "external_id": ext_id,
        "relative_path": rel_path,
        "sort_order": idx + 1,
        "label": str(idx + 1),
      })
  return plan


def _find_zip_image_member(zip_file, rel_path):
  root_prefix = _get_zip_root_prefix(zip_file)
  candidates = [
    rel_path,
    f"exercises/{rel_path}",
    f"{root_prefix}exercises/{rel_path}",
  ]

  names = set(zip_file.namelist())
  for candidate in candidates:
    if candidate in names:
      return candidate

  return None


def _blob_media_from_bytes(file_bytes, rel_path, content_type=None):
  file_name = rel_path.split("/")[-1]
  ctype = content_type or mimetypes.guess_type(file_name)[0] or "application/octet-stream"
  return BlobMedia(content_type=ctype, content=file_bytes, name=file_name)


def _load_image_media(zip_file, rel_path, allow_github_fallback=True):
  if zip_file is not None:
    member = _find_zip_image_member(zip_file, rel_path)
    if member:
      return _blob_media_from_bytes(zip_file.read(member), rel_path)

  if allow_github_fallback:
    url = RAW_IMAGE_PREFIX + rel_path
    remote_media = anvil.http.request(url=url, method="GET", timeout=30)
    return _blob_media_from_bytes(
      remote_media.get_bytes(),
      rel_path,
      content_type=remote_media.content_type,
    )

  raise Exception(f"Image not found in zip: {rel_path}")


def _get_exercise_row_by_external_id(ext_id):
  return app_tables.exercises.get(external_id=ext_id)


@anvil.server.callable
def seed_reference_data(admin_email=DEFAULT_ADMIN_EMAIL):
  _require_table("completion_messages")
  admin_user = _ensure_admin_user(admin_email)
  created_messages = _ensure_completion_messages()

  return {
    "admin_email": admin_user["email"],
    "display_name": admin_user["display_name"],
    "is_admin": admin_user["is_admin"],
    "role": admin_user["role"],
    "completion_messages_created": created_messages,
  }


@anvil.server.callable
def import_exercise_catalog(zip_media, admin_email=DEFAULT_ADMIN_EMAIL):
  _require_table("exercises")
  _require_table("completion_messages")

  _ensure_admin_user(admin_email)
  _ensure_completion_messages()

  zip_file = _open_zip_media(zip_media)
  exercises_data = _load_exercises_json(zip_file)

  created = 0
  updated = 0

  for exercise_dict in exercises_data:
    _, action = _upsert_exercise(exercise_dict)
    if action == "created":
      created += 1
    else:
      updated += 1

  total_image_refs = sum(len(_safe_list(x.get("images"))) for x in exercises_data)

  return {
    "exercises_total_in_zip": len(exercises_data),
    "created": created,
    "updated": updated,
    "image_refs_in_json": total_image_refs,
  }


@anvil.server.callable
def import_exercise_images_batch(zip_media, start_index=0, batch_size=50, allow_github_fallback=True):
  _require_table("exercises")
  _require_table("exercise_images")

  zip_file = _open_zip_media(zip_media)
  exercises_data = _load_exercises_json(zip_file)
  plan = _build_image_plan(exercises_data)

  start_index = int(start_index or 0)
  batch_size = int(batch_size or 50)

  if start_index < 0:
    start_index = 0
  if batch_size < 1:
    batch_size = 1

  batch = plan[start_index:start_index + batch_size]

  imported = 0
  skipped = 0
  failed = 0
  errors = []

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
      media = _load_image_media(
        zip_file=zip_file,
        rel_path=rel_path,
        allow_github_fallback=allow_github_fallback
      )

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
  done = next_index >= len(plan)

  return {
    "start_index": start_index,
    "batch_size": batch_size,
    "processed": len(batch),
    "imported": imported,
    "skipped": skipped,
    "failed": failed,
    "next_index": None if done else next_index,
    "done": done,
    "total_images_in_plan": len(plan),
    "errors": errors[:20],
  }


@anvil.server.callable
def set_user_admin_by_email(email=DEFAULT_ADMIN_EMAIL):
  user = _ensure_admin_user(email)
  return {
    "email": user["email"],
    "display_name": user["display_name"],
    "is_admin": user["is_admin"],
    "role": user["role"],
    "plan_tier": user["plan_tier"],
  }