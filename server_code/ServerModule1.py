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
DEFAULT_IMAGE_BATCH_SIZE = 5

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


def _set_row_values(row, values):
  for key, value in values.items():
    row[key] = value


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


def _find_user_by_email(email):
  target = (email or "").strip().lower()
  if not target:
    return None

  for row in app_tables.users.search():
    row_email = (row["email"] or "").strip().lower()
    if row_email == target:
      return row

  return None


def _get_bootstrap_user():
  user = anvil.users.get_user()
  if user is not None:
    return user

  users_iter = iter(app_tables.users.search())
  return next(users_iter, None)


def _seed_user_columns(user):
  for key, value in USER_COLUMN_DEFAULTS.items():
    try:
      current = user[key]
    except Exception:
      current = None

    if current is None or current == "":
      user[key] = value


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
    by_external_id[ext_id] = row
    by_normalized_name[normalized_name] = row
    return row, "updated"

  values["created_at"] = _now()
  new_row = app_tables.exercises.add_row(**values)
  if ext_id:
    by_external_id[ext_id] = new_row
  if normalized_name:
    by_normalized_name[normalized_name] = new_row
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
def bootstrap_schema():
  required_tables = [
    "exercises",
    "exercise_images",
    "workout_days",
    "workout_slots",
    "workout_sessions",
    "workout_session_exercises",
    "workout_session_sets",
    "user_exercise_state",
    "completion_messages",
  ]

  for table_name in required_tables:
    _require_table(table_name)

  subscriptions_table_exists = hasattr(app_tables, "subscriptions")

  user = _get_bootstrap_user()
  if user is None:
    raise Exception("Sign in with Google once first so the Users table has at least one row.")

  _seed_user_columns(user)

  now = _now()
  created_rows = []

  try:
    exercise_row = app_tables.exercises.add_row(
      external_id="bootstrap-exercise-1",
      source="import",
      source_version="bootstrap",
      name="Bootstrap Bench Press",
      normalized_name="bootstrap bench press",
      category="strength",
      force="push",
      level="beginner",
      mechanic="compound",
      equipment="barbell",
      primary_muscles=["chest"],
      secondary_muscles=["triceps", "shoulders"],
      instructions=["Unrack the bar", "Lower to chest", "Press to lockout"],
      group_size="Large",
      uses_bodyweight_default=False,
      is_active=True,
      created_by_user=user,
      created_at=now,
      updated_at=now,
    )
    created_rows.append(exercise_row)

    image_row = app_tables.exercise_images.add_row(
      exercise=exercise_row,
      image=BlobMedia(content_type="text/plain", content=b"bootstrap", name="bootstrap.txt"),
      sort_order=1,
      label="start",
      source_filename="bootstrap.txt",
      created_at=now,
    )
    created_rows.append(image_row)

    workout_day_row = app_tables.workout_days.add_row(
      user=user,
      day_code="A",
      display_order=1,
      is_active=True,
      created_at=now,
      updated_at=now,
      archived_at=now,
    )
    created_rows.append(workout_day_row)

    workout_slot_row = app_tables.workout_slots.add_row(
      user=user,
      workout_day=workout_day_row,
      slot_number=1,
      display_order=1,
      exercise=exercise_row,
      is_active=True,
      base_target_weight=135,
      base_target_reps=10,
      default_sets=5,
      uses_bodyweight=False,
      notes="bootstrap",
      created_at=now,
      updated_at=now,
      archived_at=now,
    )
    created_rows.append(workout_slot_row)

    workout_session_row = app_tables.workout_sessions.add_row(
      user=user,
      workout_day=workout_day_row,
      day_code_snapshot="A",
      started_at=now,
      completed_at=now,
      completion_bucket="standard",
      share_text="Oslocon Workout!\n01-01-2026 9:00 AM\n🟩",
      notes="bootstrap",
    )
    created_rows.append(workout_session_row)

    session_exercise_row = app_tables.workout_session_exercises.add_row(
      workout_session=workout_session_row,
      user=user,
      workout_slot=workout_slot_row,
      exercise=exercise_row,
      exercise_name_snapshot="Bootstrap Bench Press",
      muscle_group_snapshot="chest",
      group_size_snapshot="Large",
      display_order_snapshot=1,
      planned_weight=135,
      planned_reps=10,
      planned_sets=5,
      uses_bodyweight=False,
      exercise_status="completed",
      tile_state="green",
      exercise_changed=False,
      exceeded_plan=False,
      had_skipped_sets=False,
      created_at=now,
    )
    created_rows.append(session_exercise_row)

    session_set_row = app_tables.workout_session_sets.add_row(
      workout_session_exercise=session_exercise_row,
      set_index=1,
      planned_weight=135,
      planned_reps=10,
      planned_uses_bodyweight=False,
      actual_weight=135,
      actual_reps=10,
      actual_uses_bodyweight=False,
      performed=True,
      auto_completed=False,
      estimated_1rm=180,
      set_score=1350,
    )
    created_rows.append(session_set_row)

    state_row = app_tables.user_exercise_state.add_row(
      user=user,
      exercise=exercise_row,
      current_target_weight=135,
      current_target_reps=10,
      current_uses_bodyweight=False,
      qualifying_streak=1,
      last_completed_at=now,
      last_workout_session_exercise=session_exercise_row,
      strongest_estimated_1rm=180,
      strongest_set_score=1350,
      updated_at=now,
    )
    created_rows.append(state_row)

    if subscriptions_table_exists:
      subscription_row = app_tables.subscriptions.add_row(
        user=user,
        stripe_customer_id="cus_bootstrap",
        stripe_subscription_id="sub_bootstrap",
        plan_code="free",
        status="inactive",
        current_period_end=now,
        cancel_at_period_end=False,
        created_at=now,
        updated_at=now,
      )
      created_rows.append(subscription_row)

    _ensure_completion_messages()

  finally:
    for row in reversed(created_rows):
      try:
        row.delete()
      except Exception:
        pass

  return "Bootstrap complete. Columns should now be auto-created."


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

  by_external_id, by_normalized_name = _build_existing_exercise_maps()

  created = 0
  updated = 0

  for exercise_dict in exercises_data:
    _, action = _upsert_exercise_with_maps(exercise_dict, by_external_id, by_normalized_name)
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
def import_exercise_images_batch(zip_media, start_index=0, batch_size=DEFAULT_IMAGE_BATCH_SIZE, allow_github_fallback=True):
  _require_table("exercises")
  _require_table("exercise_images")

  zip_file = _open_zip_media(zip_media)
  exercises_data = _load_exercises_json(zip_file)
  plan = _build_image_plan(exercises_data)

  start_index = int(start_index or 0)
  batch_size = int(batch_size or DEFAULT_IMAGE_BATCH_SIZE)

  if start_index < 0:
    start_index = 0
  if batch_size < 1:
    batch_size = DEFAULT_IMAGE_BATCH_SIZE

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
      media = _load_image_media(zip_file, rel_path, allow_github_fallback)
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