import anvil.server
import anvil.users

from table_helpers import ensure_user_defaults
from routine_service import ensure_preset_routine
from workout_service import build_workout_payload


@anvil.server.callable
def get_bootstrap_payload():
    user = anvil.users.get_user()
    if user is None:
        try:
            user = anvil.users.login_with_google()
        except Exception as e:
            raise Exception(f"Google login is required. {e}")
    ensure_user_defaults(user)
    ensure_preset_routine(user)
    payload = build_workout_payload(user, None)
    return {
        "user": {
            "email": user["email"],
            "display_name": user["display_name"] or user["email"].split("@")[0].title(),
            "progress_every_n_qualifying_workouts": user["progress_every_n_qualifying_workouts"] or 3,
            "is_admin": bool(user["is_admin"]),
        },
        "workout": payload,
    }
