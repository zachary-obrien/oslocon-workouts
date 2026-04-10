import anvil.server
import anvil.users

from table_helpers import ensure_user_defaults
from routine_service import ensure_preset_routine
from workout_service import build_workout_payload


def _require_logged_in_user():
  user = anvil.users.get_user()
  if user is None:
    try:
      user = anvil.users.login_with_google()
    except Exception as e:
      raise Exception(f"Google login is required. {e}")
  return user


def _build_user_payload(user):
  email = user["email"] or ""
  display_name = user["display_name"] or (email.split("@")[0].title() if email else "User")
  return {
    "email": email,
    "display_name": display_name,
    "progress_every_n_qualifying_workouts": int(user["progress_every_n_qualifying_workouts"] or 3),
    "is_admin": bool(user["is_admin"]),
  }


@anvil.server.callable
def get_bootstrap_payload():
  user = _require_logged_in_user()
  ensure_user_defaults(user)
  ensure_preset_routine(user)

  workout = build_workout_payload(user, None)

  return {
    "user": _build_user_payload(user),
    "workout": workout,
  }


@anvil.server.callable
def ensure_user_bootstrap():
  user = _require_logged_in_user()
  ensure_user_defaults(user)
  ensure_preset_routine(user)

  return {
    "ok": True,
    "user": _build_user_payload(user),
  }