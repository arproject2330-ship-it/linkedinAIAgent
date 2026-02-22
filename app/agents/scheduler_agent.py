"""Scheduler Agent: decide immediate vs scheduled publish from best_days / best_time_ranges."""
from datetime import datetime, timezone, timedelta
from app.workflow.state import WorkflowState


def scheduler_agent(state: WorkflowState) -> dict:
    """
    Pure logic: given performance_insights and optional schedule_override,
    returns suggested_immediate: bool and suggested_scheduled_at: datetime | None.
    Actual scheduling is done in the API layer with APScheduler.
    """
    performance = state.get("performance_insights") or {}
    best_days = performance.get("best_days") or ["Tuesday", "Wednesday", "Thursday"]
    best_times = performance.get("best_time_ranges") or performance.get("best_times") or ["08:00-10:00", "12:00-14:00"]

    now = datetime.now(timezone.utc)
    current_day = now.strftime("%A")
    current_hour = now.hour
    current_slot = f"{current_hour:02d}:00-{(current_hour + 1) % 24:02d}:00"

    in_best_day = current_day in best_days
    in_best_time = any(
        current_slot == t or (t and current_hour >= int(t.split("-")[0].split(":")[0]))
        for t in best_times
    )

    if in_best_day and in_best_time:
        return {"suggested_immediate": True, "suggested_scheduled_at": None}

    # Next best slot: next Tue/Wed/Thu at first best time
    day_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    first_best_time = best_times[0] if best_times else "09:00-10:00"
    try:
        hour = int(first_best_time.split("-")[0].split(":")[0])
    except (ValueError, IndexError):
        hour = 9
    for d in day_order:
        if d in best_days:
            # Find next occurrence of d
            days_ahead = (day_order.index(d) - day_order.index(current_day) + 7) % 7
            if days_ahead == 0 and not in_best_time:
                days_ahead = 7
            target = now.replace(hour=hour, minute=0, second=0, microsecond=0) + timedelta(days=days_ahead)
            if target <= now:
                target += timedelta(days=7)
            return {"suggested_immediate": False, "suggested_scheduled_at": target.isoformat()}
    target = now.replace(hour=9, minute=0, second=0, microsecond=0)
    if target <= now:
        target += timedelta(days=1)
    return {"suggested_immediate": False, "suggested_scheduled_at": target.isoformat()}
