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
    self.root = LinearPanel(spacing="small", background="#0b0f14", foreground="#f3f6fb")
    self.add_component(self.root)

    self.hero = ColumnPanel(background="#141c26", foreground="#f3f6fb", border="1px solid #283548")
    self.root.add_component(self.hero, full_width_row=True)

    top_row = GridPanel()
    self.hero.add_component(top_row, full_width_row=True)

    self.user_label = Label(text="", bold=True, font_size=18)
    self.day_helper = Label(text="", foreground="#97a5b7")
    self.day_dd = DropDown(include_placeholder=False, width=120)
    self.top_menu_btn = Button(text="⋯", width=40)

    top_row.add_component(self.user_label, row="A", col_xs=0, width_xs=5)
    top_row.add_component(self.day_helper, row="A", col_xs=5, width_xs=3)
    top_row.add_component(self.day_dd, row="A", col_xs=8, width_xs=2)
    top_row.add_component(self.top_menu_btn, row="A", col_xs=10, width_xs=2)

    self.progress_label = Label(text="", foreground="#97a5b7")
    self.hero.add_component(self.progress_label)

    self.exercise_panel = LinearPanel(spacing="small")
    self.root.add_component(self.exercise_panel, full_width_row=True)

    footer = ColumnPanel(background="#141c26", foreground="#f3f6fb", border="1px solid #283548")
    self.root.add_component(footer, full_width_row=True)
    self.complete_btn = Button(text="Workout Complete", role="filled-button")
    self.submit_msg = Label(text="", foreground="#97a5b7")
    footer.add_component(self.complete_btn)
    footer.add_component(self.submit_msg)
    footer.add_component(Label(text="Created by Agreadda", foreground="#738195"))

    self.day_dd.set_event_handler("change", self.day_dd_change)
    self.top_menu_btn.set_event_handler("click", self.top_menu_btn_click)
    self.complete_btn.set_event_handler("click", self.complete_btn_click)

  def _normalize_payload(self, payload):
    p = dict(payload or {})

    resolved_user = dict(p.get("resolvedUser") or {})
    resolved_user.setdefault("display_name", "User")
    resolved_user.setdefault("email", "")

    progression = dict(p.get("progression_settings") or {})
    progression.setdefault("progress_every_n_qualifying_workouts", 3)

    normalized = {
      "resolvedUser": resolved_user,
      "current_day": p.get("current_day") or "",
      "next_scheduled_day": p.get("next_scheduled_day") or (p.get("current_day") or ""),
      "day_options": list(p.get("day_options") or []),
      "can_remove_current_day": bool(p.get("can_remove_current_day")),
      "exercises": list(p.get("exercises") or []),
      "progression_settings": progression,
    }
    return normalized

  def _unwrap_workout_payload(self, result):
    if isinstance(result, dict) and "workout" in result:
      return self._normalize_payload(result.get("workout"))
    return self._normalize_payload(result)

  def refresh_payload(self, day_code):
    result = anvil.server.call("load_workout_day", day_code)
    self.payload = self._unwrap_workout_payload(result)
    self.render()

  def render(self):
    p = self._normalize_payload(self.payload)
    self.payload = p

    user = p.get("resolvedUser") or {}
    self.user_label.text = user.get("display_name") or "User"

    current_day = p.get("current_day") or ""
    next_day = p.get("next_scheduled_day") or current_day

    if current_day:
      self.day_helper.text = f"Displayed Workout: Day {current_day} • Next scheduled: Day {next_day}"
    else:
      self.day_helper.text = "No workout day available yet."

    day_options = list(p.get("day_options") or [])
    self.day_dd.items = [(f"Day {d.get('day_code')}", d.get("day_code")) for d in day_options if d.get("day_code")]
    self.day_dd.selected_value = current_day if current_day else None
    self.day_dd.enabled = bool(day_options)

    self.complete_btn.enabled = bool(current_day)
    self.top_menu_btn.enabled = True

    self._render_progress()
    self._render_exercises()

  def _render_progress(self):
    exercises = [e for e in self.payload.get("exercises", []) if not e.get("is_unassigned")]
    total = len(exercises)
    completed = len([e for e in exercises if e.get("status") == "completed"])
    skipped = len([e for e in exercises if e.get("status") == "skipped"])
    remaining = max(total - completed - skipped, 0)
    rule = (self.payload.get("progression_settings") or {}).get("progress_every_n_qualifying_workouts", 3)

    if total == 0:
      self.progress_label.text = f"0 / 0 complete • 0 skipped • 0 remaining • Progress after {rule} qualifying workouts"
    else:
      self.progress_label.text = f"{completed} / {total} complete • {skipped} skipped • {remaining} remaining • Progress after {rule} qualifying workouts"

  def _render_exercises(self):
    self.exercise_panel.clear()
    exercises = self.payload.get("exercises", [])

    if not exercises:
      self.exercise_panel.add_component(Label(text="No exercises on this day yet.", foreground="#97a5b7"))
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
    selected = self.day_dd.selected_value
    self.refresh_payload(selected)

  def top_menu_btn_click(self, **event_args):
    current_day = self.payload.get("current_day")
    if not current_day:
      return

    buttons = [
      ("Add Exercise", "add_ex"),
      ("Progression Settings", "progress"),
      ("Workout History", "history"),
      ("Add Workout Day", "add_day"),
    ]
    if self.payload.get("can_remove_current_day"):
      buttons.append(("Remove Current Day", "remove_day"))
    buttons.append(("Cancel", None))

    result = alert(title="Workout Menu", content="Choose an action", buttons=buttons, dismissible=True)

    if result == "add_ex":
      self.payload = self._unwrap_workout_payload(anvil.server.call("add_exercise_slot", current_day))
      self.render()
    elif result == "progress":
      current_value = (self.payload.get("progression_settings") or {}).get("progress_every_n_qualifying_workouts", 3)
      modal = ProgressionSettingsModal(current_value)
      res = alert(content=modal, title="Progression Settings", buttons=[], dismissible=True)
      if isinstance(res, dict) and res.get("action") == "save":
        self.payload = self._unwrap_workout_payload(anvil.server.call("update_progression_setting", res.get("value")))
        self.render()
    elif result == "history":
      from ..HistoryForm import HistoryForm
      alert(content=HistoryForm(), title="Workout History", large=True, buttons=[("Close", True)])
    elif result == "add_day":
      self.payload = self._unwrap_workout_payload(anvil.server.call("add_workout_day"))
      self.render()
    elif result == "remove_day":
      self.payload = self._unwrap_workout_payload(anvil.server.call("remove_workout_day", current_day))
      self.render()

  def exercise_view_history(self, exercise_index=None, exercise_data=None, **event_args):
    exercise_id = (exercise_data or {}).get("exercise_id")
    if not exercise_id:
      return

    items = anvil.server.call("get_exercise_history", exercise_id)
    modal = WorkoutHistoryModal(
      exercise_name=(exercise_data or {}).get("exercise_label") or "Exercise",
      history_items=items or [],
    )
    alert(content=modal, title="Exercise History", large=True, buttons=[("Close", True)])

  def exercise_change(self, exercise_index=None, exercise_data=None, **event_args):
    current_name = (exercise_data or {}).get("exercise_label") or ""
    slot_number = (exercise_data or {}).get("slot_number")
    current_day = self.payload.get("current_day")

    if slot_number is None or not current_day:
      return

    modal = ChangeExerciseModal(current_name=current_name)
    res = alert(content=modal, title="Change Exercise", large=True, buttons=[], dismissible=True)
    if isinstance(res, dict) and res.get("action") == "choose":
      self.payload = self._unwrap_workout_payload(
        anvil.server.call("assign_slot_exercise", current_day, slot_number, res.get("exercise_id"))
      )
      self.render()

  def exercise_move(self, exercise_index=None, direction=None, exercise_data=None, **event_args):
    slot_number = (exercise_data or {}).get("slot_number")
    current_day = self.payload.get("current_day")
    if slot_number is None or not current_day:
      return

    self.payload = self._unwrap_workout_payload(
      anvil.server.call("move_exercise_slot", current_day, slot_number, direction)
    )
    self.render()

  def exercise_remove(self, exercise_index=None, exercise_data=None, **event_args):
    slot_number = (exercise_data or {}).get("slot_number")
    current_day = self.payload.get("current_day")
    if slot_number is None or not current_day:
      return

    if confirm("Remove this exercise slot?"):
      self.payload = self._unwrap_workout_payload(
        anvil.server.call("remove_exercise_slot", current_day, slot_number)
      )
      self.render()

  def exercise_updated(self, exercise_index=None, exercise_data=None, **event_args):
    exercises = self.payload.get("exercises", [])
    if exercise_index is None or exercise_index < 0 or exercise_index >= len(exercises):
      return

    exercises[exercise_index] = exercise_data or {}
    self._render_progress()
    self._render_exercises()
    self._check_auto_complete_prompt()

  def _has_skipped_exercises(self):
    return any(e.get("status") == "skipped" for e in self.payload.get("exercises", []) if not e.get("is_unassigned"))

  def _all_required_complete(self):
    relevant = [e for e in self.payload.get("exercises", []) if not e.get("is_unassigned")]
    if not relevant:
      return False

    for ex in relevant:
      if ex.get("status") == "skipped":
        continue
      if not all(s.get("performed") for s in ex.get("sets", [])):
        return False
    return True

  def _first_unfinished_exercise_index(self):
    for idx, ex in enumerate(self.payload.get("exercises", [])):
      if ex.get("is_unassigned") or ex.get("status") == "skipped":
        continue
      if any(not s.get("performed") for s in ex.get("sets", [])):
        return idx
    return None

  def _check_auto_complete_prompt(self):
    if self.auto_prompted:
      return

    if self._all_required_complete():
      res = alert(
        content=AutoCompleteWorkoutModal(has_skipped=self._has_skipped_exercises()),
        title="Workout complete?",
        buttons=[],
        dismissible=True
      )
      self.auto_prompted = True
      if res is True:
        self._submit_workout()
      else:
        self.auto_prompted = False

  def complete_btn_click(self, **event_args):
    if not self.payload.get("current_day"):
      return

    if self._all_required_complete():
      self._submit_workout()
      return

    res = alert(
      content=UnfinishedWorkoutModal(),
      title="Some sets are unfinished",
      buttons=[],
      dismissible=True
    )

    if res == "go_back":
      idx = self._first_unfinished_exercise_index()
      if idx is not None:
        ex_name = (self.payload.get("exercises", [])[idx] or {}).get("exercise_label") or "that exercise"
        Notification(f"Go back to {ex_name}", style="info").show()
    elif res == "finish_remaining":
      for ex in self.payload.get("exercises", []):
        if ex.get("is_unassigned") or ex.get("status") == "skipped":
          continue
        for s in ex.get("sets", []):
          s["performed"] = True
          s["auto_completed"] = True
        ex["status"] = "completed"
        ex["collapsed"] = True
      self._render_exercises()
      self._render_progress()
      self._submit_workout()
    elif res == "complete_anyway":
      self._submit_workout()

  def _submit_workout(self):
    current_day = self.payload.get("current_day")
    if not current_day:
      raise Exception("No workout day selected.")

    payload = {"day_code": current_day, "exercises": []}
    for ex in self.payload.get("exercises", []):
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
    self.submit_msg.text = "Saved."

    summary = (result or {}).get("completion_summary") or {}
    alert(
      content=WorkoutCompleteModal(summary=summary),
      title="Workout Complete",
      large=True,
      buttons=[],
      dismissible=True
    )

    self.payload = self._unwrap_workout_payload((result or {}).get("workout") or {})
    self.auto_prompted = False
    self.render()