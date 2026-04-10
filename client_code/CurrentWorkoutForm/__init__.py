from ._anvil_designer import CurrentWorkoutFormTemplate
from anvil import *
import anvil.server
import anvil.js

from ..ExerciseCard import ExerciseCard
from ..ChangeExerciseModal import ChangeExerciseModal
from ..WorkoutHistoryModal import WorkoutHistoryModal
from ..ProgressionSettingsModal import ProgressionSettingsModal
from ..UnfinishedWorkoutModal import UnfinishedWorkoutModal
from ..AutoCompleteWorkoutModal import AutoCompleteWorkoutModal
from ..WorkoutCompleteModal import WorkoutCompleteModal


class CurrentWorkoutForm(CurrentWorkoutFormTemplate):
  def __init__(self, bootstrap_payload=None, **properties):
    self.init_components(**properties)
    self.bootstrap_payload = bootstrap_payload or {}
    self.state = {
      "activeEmail": self.bootstrap_payload.get("activeEmail", ""),
      "activeEmailResolved": bool(self.bootstrap_payload.get("activeEmailResolved")),
      "registrationRequired": bool(self.bootstrap_payload.get("registrationRequired")),
      "userResolved": bool(self.bootstrap_payload.get("userResolved")),
      "user": self.bootstrap_payload.get("user") or {},
      "workout": self.bootstrap_payload.get("workout"),
      "completionSummary": None,
    }
    self.exercise_cards = []
    self.modal_form = None
    self.top_menu_open = False
    self.auto_prompted = False
    self._build_ui()
    self.render()

  def _build_ui(self):
    self.root = ColumnPanel(role="shell-wrap")
    self.add_component(self.root)

    self.subtitle = Label(text="", role="page-subtitle", spacing_above="none")
    self.root.add_component(self.subtitle)

    self.registration_card = ColumnPanel(role="card")
    self.root.add_component(self.registration_card, full_width_row=True)
    self.registration_help = Label(text="", role="muted")
    self.registration_name = TextBox(placeholder="Your name")
    self.registration_continue = Button(text="Continue", role="button-primary")
    self.registration_card.add_component(Label(text="Save your workouts", role="exercise-title", spacing_below="none"))
    self.registration_card.add_component(self.registration_help)
    self.registration_card.add_component(self.registration_name)
    self.registration_card.add_component(self.registration_continue)
    self.registration_continue.set_event_handler("click", self.register_continue_click)
    self.registration_name.set_event_handler("pressed_enter", self.register_continue_click)

    self.workout_area = ColumnPanel()
    self.root.add_component(self.workout_area, full_width_row=True)

    self.hero = ColumnPanel(role="card hero-card")
    self.workout_area.add_component(self.hero, full_width_row=True)
    self.hero_top = GridPanel()
    self.hero.add_component(self.hero_top, full_width_row=True)
    self.hero_left = ColumnPanel()
    self.hero_title = Label(text="", role="exercise-title", spacing_below="none")
    self.day_helper = Label(text="", role="muted")
    self.hero_left.add_component(self.hero_title)
    self.hero_left.add_component(self.day_helper)
    self.hero_top.add_component(self.hero_left, row="A", col_xs=0, width_xs=7)

    self.hero_right = ColumnPanel()
    self.hero_day_row = FlowPanel(align="right")
    self.day_selector = DropDown(include_placeholder=False, role="select day-select")
    self.top_menu_btn = Button(text="⋯", role="icon-button")
    self.hero_day_row.add_component(self.day_selector)
    self.hero_day_row.add_component(self.top_menu_btn)
    self.hero_right.add_component(self.hero_day_row)
    self.top_menu_panel = LinearPanel(role="inline-menu", visible=False, spacing="none")
    self.hero_right.add_component(self.top_menu_panel)
    self.hero_top.add_component(self.hero_right, row="A", col_xs=7, width_xs=5)

    self.top_menu_add_ex = Button(text="Add exercise", role="menu-item")
    self.top_menu_prog = Button(text="Progression settings", role="menu-item")
    self.top_menu_hist = Button(text="Workout history", role="menu-item")
    self.top_menu_add_day = Button(text="Add workout day", role="menu-item")
    self.top_menu_remove_day = Button(text="Remove current day", role="menu-item-danger")
    for c in [self.top_menu_add_ex, self.top_menu_prog, self.top_menu_hist, self.top_menu_add_day, self.top_menu_remove_day]:
      self.top_menu_panel.add_component(c)

    self.hero_progress = FlowPanel()
    self.hero.add_component(self.hero_progress)

    self.exercise_list = LinearPanel(spacing="small")
    self.workout_area.add_component(self.exercise_list, full_width_row=True)

    self.footer_wrap = ColumnPanel(role="sticky-submit")
    self.workout_area.add_component(self.footer_wrap, full_width_row=True)
    self.footer_card = ColumnPanel(role="card")
    self.footer_wrap.add_component(self.footer_card, full_width_row=True)
    self.complete_btn = Button(text="Workout Complete", role="button-primary")
    self.submit_msg = Label(text="", role="muted")
    self.credit = Label(text="Created by Agreadda", role="credit")
    self.footer_card.add_component(self.complete_btn)
    self.footer_card.add_component(self.submit_msg)
    self.footer_card.add_component(self.credit)

    self.modal_backdrop = ColumnPanel(role="modal-backdrop", visible=False)
    self.modal_backdrop.background = "rgba(5,8,12,0.76)"
    self.root.add_component(self.modal_backdrop, full_width_row=True)
    self.modal_host = ColumnPanel()
    spacer = Spacer()
    spacer.height = 20
    self.modal_backdrop.add_component(spacer)
    self.modal_backdrop.add_component(self.modal_host, full_width_row=True)

    self.day_selector.set_event_handler("change", self.day_selector_change)
    self.top_menu_btn.set_event_handler("click", self.toggle_top_menu)
    self.top_menu_add_ex.set_event_handler("click", self.add_exercise_click)
    self.top_menu_prog.set_event_handler("click", self.open_progression_modal)
    self.top_menu_hist.set_event_handler("click", self.open_history_modal)
    self.top_menu_add_day.set_event_handler("click", self.add_day_click)
    self.top_menu_remove_day.set_event_handler("click", self.remove_day_click)
    self.complete_btn.set_event_handler("click", self.attempt_workout_complete)

  def _user_display_name(self):
    workout_user = (self.state.get("workout") or {}).get("resolvedUser") or {}
    user = self.state.get("user") or {}
    return workout_user.get("display_name") or user.get("display_name") or "User"

  def render(self):
    self.registration_card.visible = bool(self.state.get("registrationRequired"))
    self.workout_area.visible = not self.registration_card.visible

    if self.registration_card.visible:
      active = self.state.get("activeEmail")
      if active:
        self.registration_help.text = f"Saving as {active}. Enter your name to continue."
      else:
        self.registration_help.text = "Enter your name to continue."
      self.registration_name.text = (self.state.get("user") or {}).get("display_name") or ""
      self.subtitle.text = "Complete setup"
      return

    workout = self.state.get("workout") or {}
    self.subtitle.text = f"Logged in as {self._user_display_name()}{' • ' + self.state.get('activeEmail') if self.state.get('activeEmail') else ''}"
    self.hero_title.text = self._user_display_name()
    self.day_helper.text = self._day_helper_text()
    self.top_menu_remove_day.visible = bool(workout.get("can_remove_current_day"))

    self.day_selector.items = [(f"Day {d['day_code']}", d['day_code']) for d in workout.get("day_options", [])]
    self.day_selector.selected_value = workout.get("current_day")

    self._render_hero_progress()
    self._render_exercises()

  def _day_helper_text(self):
    workout = self.state.get("workout") or {}
    current_day = workout.get("current_day") or ""
    next_day = workout.get("next_scheduled_day") or current_day
    if current_day == next_day:
      return f"Displayed Workout: Day {current_day}"
    return f"Displayed Workout: Day {current_day} • Next scheduled: Day {next_day}"

  def _render_hero_progress(self):
    self.hero_progress.clear()
    workout = self.state.get("workout") or {}
    exercises = [e for e in workout.get("exercises", []) if not e.get("is_unassigned")]
    total = len(exercises)
    completed = len([e for e in exercises if e.get("status") == "completed"])
    skipped = len([e for e in exercises if e.get("status") == "skipped"])
    remaining = total - completed - skipped
    rule = int((workout.get("progression_settings") or {}).get("progress_every_n_qualifying_workouts", 3))
    parts = [f"{completed} / {total} complete"]
    if skipped:
      parts.append(f"{skipped} skipped")
    if remaining:
      parts.append(f"{remaining} remaining")
    parts.append(f"Progress after {rule} qualifying workouts")
    for idx, text in enumerate(parts):
      if idx:
        self.hero_progress.add_component(Label(text="•", role="muted", spacing_above="none", spacing_below="none"))
      self.hero_progress.add_component(Label(text=text, role="muted", spacing_above="none", spacing_below="none"))

  def _render_exercises(self):
    self.exercise_list.clear()
    self.exercise_cards = []
    workout = self.state.get("workout") or {}
    for idx, ex in enumerate(workout.get("exercises", [])):
      card = ExerciseCard(exercise_index=idx, exercise_data=ex)
      card.set_event_handler("x-view-history", self.exercise_view_history)
      card.set_event_handler("x-change-exercise", self.exercise_change)
      card.set_event_handler("x-move-slot", self.exercise_move)
      card.set_event_handler("x-remove-slot", self.exercise_remove)
      card.set_event_handler("x-exercise-updated", self.exercise_updated)
      self.exercise_cards.append(card)
      self.exercise_list.add_component(card, full_width_row=True)

    if not workout.get("exercises"):
      empty = ColumnPanel(role="card")
      empty.add_component(Label(text="No exercises on this day yet. Tap Add exercise to create a new slot.", role="muted"))
      self.exercise_list.add_component(empty, full_width_row=True)

  def _refresh_workout(self, payload):
    self.state["workout"] = payload
    self.auto_prompted = False
    self.render()

  def day_selector_change(self, **event_args):
    payload = anvil.server.call("load_workout_day", self.day_selector.selected_value)
    self._refresh_workout(payload)

  def register_continue_click(self, **event_args):
    data = anvil.server.call("register_current_user", self.registration_name.text)
    self.state.update(data)
    self.render()

  def toggle_top_menu(self, **event_args):
    self.top_menu_panel.visible = not self.top_menu_panel.visible

  def _close_top_menu(self):
    self.top_menu_panel.visible = False

  def add_exercise_click(self, **event_args):
    self._close_top_menu()
    payload = anvil.server.call("add_exercise_slot", self.state["workout"]["current_day"])
    self._refresh_workout(payload)

  def add_day_click(self, **event_args):
    self._close_top_menu()
    payload = anvil.server.call("add_workout_day")
    self._refresh_workout(payload)

  def remove_day_click(self, **event_args):
    self._close_top_menu()
    payload = anvil.server.call("remove_workout_day", self.state["workout"]["current_day"])
    self._refresh_workout(payload)

  def open_progression_modal(self, **event_args):
    self._close_top_menu()
    current = int((self.state.get("workout") or {}).get("progression_settings", {}).get("progress_every_n_qualifying_workouts", 3))
    form = ProgressionSettingsModal(current)
    form.set_event_handler("x-close-modal", self.close_modal)
    form.set_event_handler("x-save-progress", self.save_progression_setting)
    self.open_modal(form)

  def save_progression_setting(self, value=None, **event_args):
    payload = anvil.server.call("update_progression_setting", value)
    self.close_modal()
    self._refresh_workout(payload)

  def open_history_modal(self, **event_args):
    self._close_top_menu()
    items = anvil.server.call("get_recent_history", 25)
    form = WorkoutHistoryModal(history_items=items)
    form.set_event_handler("x-close-modal", self.close_modal)
    self.open_modal(form)

  def exercise_view_history(self, exercise_data=None, **event_args):
    exercise_id = (exercise_data or {}).get("exercise_id")
    if not exercise_id:
      return
    items = anvil.server.call("get_exercise_history", exercise_id)
    form = WorkoutHistoryModal(history_items=items, exercise_name=(exercise_data or {}).get("exercise_label"))
    form.set_event_handler("x-close-modal", self.close_modal)
    self.open_modal(form)

  def exercise_change(self, exercise_data=None, **event_args):
    exercise_name = (exercise_data or {}).get("exercise_label") or ""
    form = ChangeExerciseModal(current_name=exercise_name)
    form.set_event_handler("x-close-modal", self.close_modal)
    form.set_event_handler("x-choose-exercise", self.change_exercise_selected, exercise_data=exercise_data)
    self.open_modal(form)

  def change_exercise_selected(self, exercise_id=None, exercise_data=None, **event_args):
    current_day = (self.state.get("workout") or {}).get("current_day")
    slot_number = (exercise_data or {}).get("slot_number")
    payload = anvil.server.call("assign_slot_exercise", current_day, slot_number, exercise_id)
    self.close_modal()
    self._refresh_workout(payload)

  def exercise_move(self, direction=None, exercise_data=None, **event_args):
    current_day = (self.state.get("workout") or {}).get("current_day")
    slot_number = (exercise_data or {}).get("slot_number")
    payload = anvil.server.call("move_exercise_slot", current_day, slot_number, direction)
    self._refresh_workout(payload)

  def exercise_remove(self, exercise_data=None, **event_args):
    current_day = (self.state.get("workout") or {}).get("current_day")
    slot_number = (exercise_data or {}).get("slot_number")
    payload = anvil.server.call("remove_exercise_slot", current_day, slot_number)
    self._refresh_workout(payload)

  def exercise_updated(self, exercise_index=None, exercise_data=None, **event_args):
    exercises = (self.state.get("workout") or {}).get("exercises", [])
    if exercise_index is None or exercise_index >= len(exercises):
      return
    exercises[exercise_index] = exercise_data
    self.render()
    self._check_auto_complete()

  def _all_done_or_skipped(self):
    exercises = [e for e in (self.state.get("workout") or {}).get("exercises", []) if not e.get("is_unassigned")]
    if not exercises:
      return False
    for ex in exercises:
      if ex.get("status") == "skipped":
        continue
      if any(not s.get("performed") for s in ex.get("sets", [])):
        return False
    return True

  def _has_skips(self):
    return any(
      ex.get("status") == "skipped"
      for ex in (self.state.get("workout") or {}).get("exercises", [])
      if not ex.get("is_unassigned")
    )

  def _first_unfinished_index(self):
    exercises = (self.state.get("workout") or {}).get("exercises", [])
    for idx, ex in enumerate(exercises):
      if ex.get("is_unassigned") or ex.get("status") == "skipped":
        continue
      if any(not s.get("performed") for s in ex.get("sets", [])):
        return idx
    return None

  def _check_auto_complete(self):
    if self.auto_prompted:
      return
    if self._all_done_or_skipped():
      self.auto_prompted = True
      form = AutoCompleteWorkoutModal(has_skipped=self._has_skips())
      form.set_event_handler("x-close-modal", self.close_modal)
      form.set_event_handler("x-complete-now", self.auto_complete_now)
      self.open_modal(form)

  def auto_complete_now(self, **event_args):
    self.close_modal()
    self.attempt_workout_complete()

  def attempt_workout_complete(self, **event_args):
    if self._all_done_or_skipped():
      self.submit_workout()
      return
    form = UnfinishedWorkoutModal()
    form.set_event_handler("x-close-modal", self.close_modal)
    form.set_event_handler("x-go-back", self.unfinished_go_back)
    form.set_event_handler("x-complete-anyway", self.unfinished_complete_anyway)
    form.set_event_handler("x-finish-remaining", self.unfinished_finish_remaining)
    self.open_modal(form)

  def unfinished_go_back(self, **event_args):
    self.close_modal()
    idx = self._first_unfinished_index()
    if idx is not None and idx < len(self.exercise_cards):
      try:
        self.exercise_cards[idx].scroll_into_view()
      except Exception:
        pass

  def unfinished_complete_anyway(self, **event_args):
    self.close_modal()
    self.submit_workout()

  def unfinished_finish_remaining(self, **event_args):
    exercises = (self.state.get("workout") or {}).get("exercises", [])
    for ex in exercises:
      if ex.get("is_unassigned") or ex.get("status") == "skipped":
        continue
      for s in ex.get("sets", []):
        if not s.get("performed"):
          s["performed"] = True
          s["auto_completed"] = True
      ex["status"] = "completed"
      ex["collapsed"] = True
    self.render()

  def _collect_submit_payload(self):
    workout = self.state.get("workout") or {}
    payload = {
      "day_code": workout.get("current_day"),
      "exercises": [],
    }
    for ex in workout.get("exercises", []):
      if ex.get("is_unassigned") or not ex.get("exercise_id"):
        continue
      payload["exercises"].append({
        "slot_number": ex.get("slot_number"),
        "exercise_id": ex.get("exercise_id"),
        "uses_bodyweight": ex.get("uses_bodyweight"),
        "recommended_weight": ex.get("recommended_weight"),
        "recommended_reps": ex.get("recommended_reps"),
        "status": ex.get("status"),
        "sets": ex.get("sets", []),
      })
    return payload

  def submit_workout(self):
    self.submit_msg.text = "Saving..."
    result = anvil.server.call("submit_workout", self._collect_submit_payload())
    self.submit_msg.text = ""
    self.state["workout"] = (result or {}).get("workout") or {}
    summary = (result or {}).get("completion_summary") or {}
    modal = WorkoutCompleteModal(summary=summary)
    modal.set_event_handler("x-close-modal", self.close_modal)
    self.open_modal(modal)
    self.render()

  def open_modal(self, form):
    self.modal_form = form
    self.modal_host.clear()
    self.modal_host.add_component(form, full_width_row=True)
    self.modal_backdrop.visible = True

  def close_modal(self, **event_args):
    self.modal_form = None
    self.modal_host.clear()
    self.modal_backdrop.visible = False