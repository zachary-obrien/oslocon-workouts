from ._anvil_designer import CurrentWorkoutFormTemplate
from anvil import *
import anvil.server

from ..ExerciseCard import ExerciseCard
from ..ChangeExerciseModal import ChangeExerciseModal
from ..WorkoutHistoryModal import WorkoutHistoryModal
from ..ProgressionSettingsModal import ProgressionSettingsModal
from ..UnfinishedWorkoutModal import UnfinishedWorkoutModal
from ..AutoCompleteWorkoutModal import AutoCompleteWorkoutModal
from ..WorkoutCompleteModal import WorkoutCompleteModal
from ..HistoryForm import HistoryForm
from ..AccountForm import AccountForm

CARD_BG = "#0f1b2b"
ROOT_BG = "#08111b"
TEXT = "#f3f6fb"
MUTED = "#9fb1c5"
BORDER = "1px solid #24354d"
ACCENT = "#d97f37"


class CurrentWorkoutForm(CurrentWorkoutFormTemplate):
  def __init__(self, initial_payload=None, **properties):
    self.init_components(**properties)
    self.payload = None
    self.auto_prompted = False
    self._build_ui()

    if initial_payload:
      self.payload = self._normalize_payload(initial_payload)
      self.render()
    else:
      self.refresh_payload(None)

  def _build_ui(self):
    self.background = ROOT_BG
    self.foreground = TEXT

    self.root = ColumnPanel(background=ROOT_BG, foreground=TEXT)
    self.add_component(self.root)

    self.hero = ColumnPanel(background=CARD_BG, foreground=TEXT, border=BORDER)
    self.root.add_component(self.hero, full_width_row=True)

    top = GridPanel(background=CARD_BG)
    self.hero.add_component(top, full_width_row=True)

    self.user_label = Label(text="", bold=True, font_size=22, foreground=TEXT)
    self.sub_label = Label(text="", foreground=MUTED)
    self.progress_label = Label(text="", foreground=MUTED)

    left = ColumnPanel(background=CARD_BG)
    left.add_component(self.user_label)
    left.add_component(self.sub_label)
    left.add_component(self.progress_label)

    self.day_dd = DropDown(include_placeholder=False, width=110)
    self.day_dd.background = "#12253b"
    self.day_dd.foreground = TEXT
    self.top_menu_btn = Button(text="⋯", width=44, role=None, background="#12253b", foreground=TEXT)

    right = FlowPanel(align="right")
    right.add_component(self.day_dd)
    right.add_component(self.top_menu_btn)

    top.add_component(left, row="A", col_xs=0, width_xs=8)
    top.add_component(right, row="A", col_xs=8, width_xs=4)

    self.exercise_panel = LinearPanel(spacing="small", background=ROOT_BG)
    self.root.add_component(self.exercise_panel, full_width_row=True)

    footer = ColumnPanel(background=CARD_BG, foreground=TEXT, border=BORDER)
    self.root.add_component(footer, full_width_row=True)
    self.complete_btn = Button(text="Workout Complete", role="filled-button")
    self.complete_btn.background = ACCENT
    self.complete_btn.foreground = "#ffffff"
    self.submit_msg = Label(text="", foreground=MUTED)
    self.credit = Label(text="Created by Agreadda", foreground="#7f93ab", align="right")
    footer.add_component(self.complete_btn)
    footer.add_component(self.submit_msg)
    footer.add_component(self.credit)

    self.day_dd.set_event_handler("change", self.day_dd_change)
    self.top_menu_btn.set_event_handler("click", self.top_menu_btn_click)
    self.complete_btn.set_event_handler("click", self.complete_btn_click)

  def _normalize_payload(self, payload):
    p = dict(payload or {})
    resolved_user = dict(p.get("resolvedUser") or {})
    resolved_user.setdefault("display_name", "User")
    resolved_user.setdefault("email", "")
    prog = dict(p.get("progression_settings") or {})
    prog.setdefault("progress_every_n_qualifying_workouts", 3)
    return {
      "resolvedUser": resolved_user,
      "current_day": p.get("current_day") or "",
      "next_scheduled_day": p.get("next_scheduled_day") or p.get("current_day") or "",
      "day_options": list(p.get("day_options") or []),
      "can_remove_current_day": bool(p.get("can_remove_current_day")),
      "exercises": list(p.get("exercises") or []),
      "progression_settings": prog,
    }

  def _unwrap(self, result):
    if isinstance(result, dict) and "workout" in result:
      return self._normalize_payload(result["workout"])
    return self._normalize_payload(result)

  def refresh_payload(self, day_code):
    self.payload = self._unwrap(anvil.server.call("load_workout_day", day_code))
    self.render()

  def render(self):
    p = self.payload
    user = p["resolvedUser"]
    self.user_label.text = user["display_name"]
    self.sub_label.text = f"Logged in as {user['display_name']} • {user['email']}"
    self.progress_label.text = self._progress_text()

    current_day = p["current_day"]
    self.day_dd.items = [(f"Day {d['day_code']}", d["day_code"]) for d in p["day_options"]]
    self.day_dd.selected_value = current_day
    self._render_exercises()

  def _progress_text(self):
    exercises = [e for e in self.payload["exercises"] if not e.get("is_unassigned")]
    total = len(exercises)
    completed = len([e for e in exercises if e.get("status") == "completed"])
    skipped = len([e for e in exercises if e.get("status") == "skipped"])
    remaining = max(total - completed - skipped, 0)
    rule = self.payload["progression_settings"]["progress_every_n_qualifying_workouts"]
    return f"{completed} / {total} complete • {skipped} skipped • {remaining} remaining • Progress after {rule} qualifying workouts"

  def _render_exercises(self):
    self.exercise_panel.clear()
    exercises = self.payload["exercises"]
    if not exercises:
      self.exercise_panel.add_component(Label(text="No exercises on this day yet.", foreground=MUTED))
      return
    for idx, ex in enumerate(exercises):
      card = ExerciseCard(exercise_index=idx, exercise_data=ex)
      card.set_event_handler("x-view-history", self.exercise_view_history)
      card.set_event_handler("x-change-exercise", self.exercise_change)
      card.set_event_handler("x-move-slot", self.exercise_move)
      card.set_event_handler("x-remove-slot", self.exercise_remove)
      card.set_event_handler("x-exercise-updated", self.exercise_updated)
      self.exercise_panel.add_component(card, full_width_row=True)

  def day_dd_change(self, **event_args):
    self.refresh_payload(self.day_dd.selected_value)

  def top_menu_btn_click(self, **event_args):
    buttons = [
      ("Workout History", "history"),
      ("Progression Settings", "progress"),
      ("Account", "account"),
      ("Add Exercise", "add_ex"),
      ("Add Workout Day", "add_day"),
    ]
    if self.payload.get("can_remove_current_day"):
      buttons.append(("Remove Current Day", "remove_day"))
    buttons.append(("Cancel", None))
    result = alert(title="Workout Menu", content="Choose an action", buttons=buttons, dismissible=True)
    if result == "history":
      alert(content=HistoryForm(), title="Workout History", large=True, buttons=[("Close", True)])
    elif result == "progress":
      modal = ProgressionSettingsModal(self.payload["progression_settings"]["progress_every_n_qualifying_workouts"])
      res = alert(content=modal, title="Progression Settings", buttons=[], dismissible=True)
      if isinstance(res, dict) and res.get("action") == "save":
        self.payload = self._unwrap(anvil.server.call("update_progression_setting", res["value"]))
        self.render()
    elif result == "account":
      alert(content=AccountForm(), title="Account", large=True, buttons=[("Close", True)])
    elif result == "add_ex":
      self.payload = self._unwrap(anvil.server.call("add_exercise_slot", self.payload["current_day"]))
      self.render()
    elif result == "add_day":
      self.payload = self._unwrap(anvil.server.call("add_workout_day"))
      self.render()
    elif result == "remove_day":
      self.payload = self._unwrap(anvil.server.call("remove_workout_day", self.payload["current_day"]))
      self.render()

  def exercise_view_history(self, exercise_index=None, exercise_data=None, **event_args):
    if not exercise_data or not exercise_data.get("exercise_id"):
      return
    items = anvil.server.call("get_exercise_history", exercise_data["exercise_id"])
    modal = WorkoutHistoryModal(exercise_name=exercise_data.get("exercise_label") or "Exercise", history_items=items or [])
    alert(content=modal, title="Exercise History", large=True, buttons=[("Close", True)])

  def exercise_change(self, exercise_index=None, exercise_data=None, **event_args):
    modal = ChangeExerciseModal(current_name=exercise_data.get("exercise_label") or "")
    res = alert(content=modal, title="Change Exercise", large=True, buttons=[], dismissible=True)
    if isinstance(res, dict) and res.get("action") == "choose":
      self.payload = self._unwrap(anvil.server.call("assign_slot_exercise", self.payload["current_day"], exercise_data["slot_number"], res["exercise_id"]))
      self.render()

  def exercise_move(self, exercise_index=None, direction=None, exercise_data=None, **event_args):
    self.payload = self._unwrap(anvil.server.call("move_exercise_slot", self.payload["current_day"], exercise_data["slot_number"], direction))
    self.render()

  def exercise_remove(self, exercise_index=None, exercise_data=None, **event_args):
    if confirm("Remove this exercise?", buttons=[("Cancel", False), ("Remove", True)]):
      self.payload = self._unwrap(anvil.server.call("remove_exercise_slot", self.payload["current_day"], exercise_data["slot_number"]))
      self.render()

  def exercise_updated(self, exercise_index=None, exercise_data=None, **event_args):
    self.payload["exercises"][exercise_index] = exercise_data
    self._render_exercises()
    self.progress_label.text = self._progress_text()
    self._check_auto_complete_prompt()

  def _has_skipped_exercises(self):
    return any(e.get("status") == "skipped" for e in self.payload["exercises"] if not e.get("is_unassigned"))

  def _all_required_complete(self):
    relevant = [e for e in self.payload["exercises"] if not e.get("is_unassigned")]
    if not relevant:
      return False
    for ex in relevant:
      if ex.get("status") == "skipped":
        continue
      if not all(s.get("performed") for s in ex.get("sets", [])):
        return False
    return True

  def _first_unfinished_exercise_index(self):
    for idx, ex in enumerate(self.payload["exercises"]):
      if ex.get("is_unassigned") or ex.get("status") == "skipped":
        continue
      if any(not s.get("performed") for s in ex.get("sets", [])):
        return idx
    return None

  def _check_auto_complete_prompt(self):
    if self.auto_prompted:
      return
    if self._all_required_complete():
      res = alert(content=AutoCompleteWorkoutModal(has_skipped=self._has_skipped_exercises()), title="Workout complete?", buttons=[], dismissible=True)
      self.auto_prompted = True
      if res is True:
        self._submit_workout()
      else:
        self.auto_prompted = False

  def complete_btn_click(self, **event_args):
    if self._all_required_complete():
      self._submit_workout()
      return
    res = alert(content=UnfinishedWorkoutModal(), title="Some sets are unfinished", buttons=[], dismissible=True)
    if res == "go_back":
      idx = self._first_unfinished_exercise_index()
      if idx is not None:
        Notification(f"Go back to {self.payload['exercises'][idx]['exercise_label']}", style="info").show()
    elif res == "finish_remaining":
      for ex in self.payload["exercises"]:
        if ex.get("is_unassigned") or ex.get("status") == "skipped":
          continue
        for s in ex.get("sets", []):
          s["performed"] = True
          s["auto_completed"] = True
        ex["status"] = "completed"
        ex["collapsed"] = True
      self._render_exercises()
      self.progress_label.text = self._progress_text()
      self._submit_workout()
    elif res == "complete_anyway":
      self._submit_workout()

  def _submit_workout(self):
    payload = {"day_code": self.payload["current_day"], "exercises": []}
    for ex in self.payload["exercises"]:
      if ex.get("is_unassigned") or not ex.get("exercise_id"):
        continue
      payload["exercises"].append({
        "slot_number": ex.get("slot_number"),
        "exercise_id": ex.get("exercise_id"),
        "uses_bodyweight": ex.get("uses_bodyweight"),
        "recommended_weight": ex.get("recommended_weight"),
        "recommended_reps": ex.get("recommended_reps"),
        "status": "skipped" if ex.get("status") == "skipped" else "completed",
        "sets": ex.get("sets", []),
      })
    self.submit_msg.text = "Saving..."
    result = anvil.server.call("submit_workout", payload)
    self.submit_msg.text = "Saved. Loaded next workout."
    summary = (result or {}).get("completion_summary") or {}
    alert(content=WorkoutCompleteModal(summary=summary), title="Workout Complete", large=True, buttons=[], dismissible=True)
    self.payload = self._unwrap((result or {}).get("workout") or {})
    self.auto_prompted = False
    self.render()
