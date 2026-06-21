import sys, os
from datetime import datetime, timedelta
import data_manager as dm


def _day_total_minutes(distribution: dict, day_str: str) -> int:
    """
    Sums every logged focus minute across all hours for a single day_str
    ("YYYY-MM-DD") inside an hourly_task_distribution-shaped dict.
    Tolerant of missing/malformed entries — returns 0 for empty days.
    """
    day_data = distribution.get(day_str, {})
    total = 0
    if isinstance(day_data, dict):
        for hour_data in day_data.values():
            if isinstance(hour_data, dict):
                total += sum(v for v in hour_data.values() if isinstance(v, (int, float)))
    return total


def get_focus_streak() -> int:
    """
    Counts consecutive days (going backwards from today) where the user
    logged at least 25 minutes of focus time.

    Rules:
    • Today is always checked first.
    • If today has < 25 min we skip it (streak may still be alive from yesterday).
    • The moment a past day has < 25 min the streak stops.
    • Returns 0 when there is no streak at all.
    """
    data         = dm.load_data()
    distribution = data.get("hourly_task_distribution", {})
    today        = datetime.now().date()
    streak       = 0

    for offset in range(0, 365):          # look back up to a year
        day_str   = (today - timedelta(days=offset)).strftime("%Y-%m-%d")
        day_total = _day_total_minutes(distribution, day_str)

        if day_total >= 25:
            streak += 1
        else:
            if offset == 0:
                # Today hasn't reached 25 min yet — don't break, check yesterday
                continue
            break   # gap in past days — streak is over

    return streak


def calculate_focus_streak() -> int:
    """
    Counts consecutive days (going backwards from today) where the user's
    logged focus minutes meet or exceed the goal in goals["daily_focus_minutes"]
    (via dm.get_goals(), which already backfills a sane default).

    Today-counts-early decision:
    "Today" is treated the same way get_focus_streak() treats it — it is
    checked first, and if it hasn't reached the goal yet we DON'T break the
    streak there, we just skip it and keep walking into yesterday. This is
    deliberate: a full calendar day hasn't elapsed yet, so a still-in-progress
    today shouldn't zero out a real streak the user is actively extending.
    Only a *past* day (offset > 0) that falls short ends the streak — by
    then the day is closed and there's no more opportunity to hit the goal.
    One consequence: if "today" is the ONLY day on the books and it hasn't
    hit the goal yet, this returns 0 for today's offset and then looks for
    a streak ending yesterday, same as the legacy function.

    Returns 0 when there is no streak at all, or when the goal is 0/unset
    (a 0-minute goal can't meaningfully be "met", so we don't award a
    streak for days that merely have zero or no data).
    """
    data         = dm.load_data()
    distribution = data.get("hourly_task_distribution", {})
    goal_minutes = dm.get_goals().get("daily_focus_minutes", 0)
    today        = datetime.now().date()
    streak       = 0

    if not goal_minutes or goal_minutes <= 0:
        return 0

    for offset in range(0, 365):          # look back up to a year
        day_str   = (today - timedelta(days=offset)).strftime("%Y-%m-%d")
        day_total = _day_total_minutes(distribution, day_str)

        if day_total >= goal_minutes:
            streak += 1
        else:
            if offset == 0:
                # Today hasn't hit the goal yet — the day isn't over, so
                # don't end the streak here; check whether it was already
                # alive coming into today (i.e. continued from yesterday).
                continue
            break   # a closed-out past day missed the goal — streak is over

    return streak


def get_daily_completion_map(num_days: int = 90) -> dict:
    """
    Returns {date_str: percentage} for each of the last *num_days* days
    (today back through today-(num_days-1)), where percentage is how much
    of goals["daily_focus_minutes"] was hit that day:

        percentage = min(100, total_minutes_that_day / goal_minutes * 100)

    A day with no logged minutes yields 0. If no daily focus goal is set
    (goal_minutes <= 0), every day in the range yields 0, since "percent of
    goal" is undefined with no goal to divide by.

    Dates are returned in chronological order (oldest → newest) so the
    result can be fed straight into a calendar-heatmap style widget.
    """
    data         = dm.load_data()
    distribution = data.get("hourly_task_distribution", {})
    goal_minutes = dm.get_goals().get("daily_focus_minutes", 0)
    today        = datetime.now().date()

    completion_map: dict[str, float] = {}

    for offset in range(num_days - 1, -1, -1):   # oldest first, today last
        day_str = (today - timedelta(days=offset)).strftime("%Y-%m-%d")

        if not goal_minutes or goal_minutes <= 0:
            completion_map[day_str] = 0
            continue

        day_total = _day_total_minutes(distribution, day_str)
        percentage = min(100, (day_total / goal_minutes) * 100)
        completion_map[day_str] = percentage

    return completion_map


def get_focus_by_weekday() -> dict:
    """
    Buckets every logged focus minute in hourly_task_distribution by weekday
    name (Monday..Sunday), summed across ALL history regardless of which
    calendar week or month a given date fell in — answers "which day of the
    week do I focus most on?" rather than any single week's distribution.

    Reuses _day_total_minutes() per date for the same malformed-data
    tolerance the streak/heatmap functions already rely on, rather than
    re-deriving totals by hand.

    Returns a dict with all 7 weekday names always present (Monday first,
    Sunday last, insertion-ordered) even when a weekday has zero minutes
    logged, so callers can render a fixed 7-bar chart without gap-filling.
    """
    data         = dm.load_data()
    distribution = data.get("hourly_task_distribution", {})

    weekday_totals = {
        "Monday": 0, "Tuesday": 0, "Wednesday": 0, "Thursday": 0,
        "Friday": 0, "Saturday": 0, "Sunday": 0,
    }

    for date_str in distribution.keys():
        try:
            weekday_name = datetime.strptime(date_str, "%Y-%m-%d").strftime("%A")
        except ValueError:
            continue   # malformed date key — skip rather than crash
        weekday_totals[weekday_name] += _day_total_minutes(distribution, date_str)

    return weekday_totals


def get_weekly_summary() -> dict:
    """
    Returns aggregated stats for the last 7 full days (yesterday back to -6).

    Keys returned
    -------------
    total_focus_mins  : int   – sum of all focus minutes across the 7 days
    top_task          : str   – task name with the most minutes (or "" if none)
    total_expense     : float – sum of all expenses across the 7 days
    completed_tasks   : int   – tasks marked completed (global count, same as
                                dashboard — tasks have no date field to filter by)
    week_start        : str   – oldest date in range, "YYYY-MM-DD"
    week_end          : str   – newest date in range, "YYYY-MM-DD"
    """
    data  = dm.load_data()
    today = datetime.now().date()

    # Build the 7-day window: today-6 … today-0 (inclusive)
    dates = [(today - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(6, -1, -1)]
    date_set = set(dates)

    # ── Focus minutes ──────────────────────────────────────────────────────────
    total_focus_mins = 0
    task_totals: dict[str, int] = {}
    distribution = data.get("hourly_task_distribution", {})

    for date_str, hours_dict in distribution.items():
        if date_str not in date_set or not isinstance(hours_dict, dict):
            continue
        for tasks_dict in hours_dict.values():
            if not isinstance(tasks_dict, dict):
                continue
            for task, mins in tasks_dict.items():
                if isinstance(mins, (int, float)) and mins > 0:
                    total_focus_mins        += mins
                    task_totals[task]        = task_totals.get(task, 0) + mins

    top_task = max(task_totals, key=task_totals.get) if task_totals else ""

    # ── Expenses ───────────────────────────────────────────────────────────────
    total_expense = 0.0
    for exp in data.get("expenses", []):
        if str(exp.get("date", "")).strip() in date_set:
            try:
                total_expense += float(exp.get("amount", 0.0))
            except (ValueError, TypeError):
                pass

    # ── Task counts (global — tasks carry no date stamp) ──────────────────────
    tasks           = data.get("tasks", [])
    completed_tasks = len([t for t in tasks if t.get("completed")])

    return {
        "total_focus_mins": total_focus_mins,
        "top_task":         top_task,
        "total_expense":    total_expense,
        "completed_tasks":  completed_tasks,
        "week_start":       dates[0],
        "week_end":         dates[-1],
    }


def get_target_dates(current_interval, time_offset):
    base_today = datetime.now().date()

    if current_interval == "Daily":
        target = base_today + timedelta(days=time_offset)
        return [target.strftime("%Y-%m-%d")]

    elif current_interval == "Weekly":
        # Returns 7 days in chronological order (oldest → newest)
        start = base_today + timedelta(days=(time_offset * 7) - 6)
        return [(start + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(7)]

    else:
        # Monthly: build from oldest to newest so graphs read left→right
        start = base_today + timedelta(days=(time_offset * 30) - 29)
        return [(start + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(30)]


def get_date_range_display_string(current_interval, target_dates):
    if not target_dates:
        return ""
    if current_interval == "Daily":
        try:
            d     = datetime.strptime(target_dates[0], "%Y-%m-%d")
            today = datetime.now().date()
            if d.date() == today:
                return f"Showing Log: {target_dates[0]} (Today)"
            elif d.date() == today - timedelta(days=1):
                return f"Showing Log: {target_dates[0]} (Yesterday)"
            return f"Showing Log: {target_dates[0]}"
        except ValueError:
            return f"Showing Log: {target_dates[0]}"

    sorted_dates = sorted(target_dates)
    try:
        start_lbl = datetime.strptime(sorted_dates[0],  "%Y-%m-%d").strftime("%b %d")
        end_lbl   = datetime.strptime(sorted_dates[-1], "%Y-%m-%d").strftime("%b %d, %Y")
        return f"Range Window: {start_lbl} - {end_lbl}"
    except (ValueError, IndexError):
        return f"Range: {sorted_dates[0]} to {sorted_dates[-1]}"


def parse_aggregated_metrics(current_interval, time_offset):
    data         = dm.load_data()
    target_dates = get_target_dates(current_interval, time_offset)

    total_focus_mins    = 0
    chrono_distribution = {}
    task_time_breakdown = {}

    # --- FOCUS TIME PROCESSING ---
    distribution_data = data.get("hourly_task_distribution", {})
    for date_str, hours_dict in distribution_data.items():
        if date_str in target_dates and isinstance(hours_dict, dict):
            for hour_str, tasks_dict in hours_dict.items():
                if isinstance(tasks_dict, dict):
                    for task, mins in tasks_dict.items():
                        if mins > 0:
                            total_focus_mins += mins
                            task_time_breakdown[task] = task_time_breakdown.get(task, 0) + mins

                            if current_interval == "Daily":
                                h_key = str(int(hour_str))
                                if h_key not in chrono_distribution:
                                    chrono_distribution[h_key] = {}
                                chrono_distribution[h_key][task] = chrono_distribution[h_key].get(task, 0) + mins
                            elif current_interval == "Weekly":
                                if date_str not in chrono_distribution:
                                    chrono_distribution[date_str] = {}
                                chrono_distribution[date_str][task] = chrono_distribution[date_str].get(task, 0) + mins
                            else:
                                if date_str not in chrono_distribution:
                                    chrono_distribution[date_str] = {}
                                chrono_distribution[date_str][task] = chrono_distribution[date_str].get(task, 0) + mins

    # TASK COUNTS
    tasks           = data.get("tasks", [])
    completed_count = len([t for t in tasks if t.get("completed")])
    pending_count   = len(tasks) - completed_count

    # EXPENSE PROCESSING
    total_expense              = 0.0
    category_expense_breakdown = {}
    expenses                   = data.get("expenses", [])

    for exp in expenses:
        exp_date = str(exp.get("date", "")).strip()
        if exp_date in target_dates:
            try:
                amt = float(exp.get("amount", 0.0))
                total_expense += amt
                cat = exp.get("category", "Others").strip()
                category_expense_breakdown[cat] = category_expense_breakdown.get(cat, 0.0) + amt
            except (ValueError, TypeError):
                continue

    return {
        "total_focus_mins":           total_focus_mins,
        "completed_tasks":            completed_count,
        "pending_tasks":              pending_count,
        "total_expense":              total_expense,
        "chrono_distribution":        chrono_distribution,
        "task_time_breakdown":        task_time_breakdown,
        "category_expense_breakdown": category_expense_breakdown,
        "target_dates":               target_dates,
    }