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
    data         = dm.load_data()
    distribution = data.get("hourly_task_distribution", {})
    today        = datetime.now().date()
    streak       = 0

    for offset in range(0, 365):
        day_str   = (today - timedelta(days=offset)).strftime("%Y-%m-%d")
        day_total = _day_total_minutes(distribution, day_str)

        if day_total >= 25:
            streak += 1
        else:
            if offset == 0:
                continue
            break

    return streak


def calculate_focus_streak() -> int:
    data         = dm.load_data()
    distribution = data.get("hourly_task_distribution", {})
    goal_minutes = dm.get_goals().get("daily_focus_minutes", 0)
    today        = datetime.now().date()
    streak       = 0

    if not goal_minutes or goal_minutes <= 0:
        return 0

    for offset in range(0, 365):
        day_str   = (today - timedelta(days=offset)).strftime("%Y-%m-%d")
        day_total = _day_total_minutes(distribution, day_str)

        if day_total >= goal_minutes:
            streak += 1
        else:
            if offset == 0:
                continue
            break

    return streak


def get_daily_completion_map(num_days: int = 90) -> dict:
    data         = dm.load_data()
    distribution = data.get("hourly_task_distribution", {})
    goal_minutes = dm.get_goals().get("daily_focus_minutes", 0)
    today        = datetime.now().date()

    completion_map: dict[str, float] = {}

    for offset in range(num_days - 1, -1, -1):
        day_str = (today - timedelta(days=offset)).strftime("%Y-%m-%d")

        if not goal_minutes or goal_minutes <= 0:
            completion_map[day_str] = 0
            continue

        day_total = _day_total_minutes(distribution, day_str)
        percentage = min(100, (day_total / goal_minutes) * 100)
        completion_map[day_str] = percentage

    return completion_map


def get_focus_by_weekday() -> dict:
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
            continue
        weekday_totals[weekday_name] += _day_total_minutes(distribution, date_str)

    return weekday_totals


def get_focus_vs_spending_by_day(num_days: int = 30) -> list[dict]:
    """
    Returns a list of dicts, one per calendar day for the last `num_days` days,
    sorted oldest-first:

        [{"date": "2025-06-01", "focus_mins": 95, "spend": 430.0}, ...]

    focus_mins: sum of all task minutes in hourly_task_distribution for that day.
    spend:      sum of all expense amounts whose "date" field matches that day.
    Days with no data for either dimension still appear with 0 values so the
    chart always shows a continuous date axis.
    """
    data         = dm.load_data()
    distribution = data.get("hourly_task_distribution", {})
    expenses     = data.get("expenses", [])
    today        = datetime.now().date()

    # Build day list oldest-first
    days = [
        (today - timedelta(days=i)).strftime("%Y-%m-%d")
        for i in range(num_days - 1, -1, -1)
    ]

    # Aggregate spend per day
    spend_by_day: dict[str, float] = {d: 0.0 for d in days}
    for exp in expenses:
        if not isinstance(exp, dict):
            continue
        exp_date = str(exp.get("date", "")).strip()
        if exp_date in spend_by_day:
            try:
                spend_by_day[exp_date] += float(exp.get("amount", 0.0))
            except (ValueError, TypeError):
                continue

    result = []
    for day_str in days:
        result.append({
            "date":       day_str,
            "focus_mins": _day_total_minutes(distribution, day_str),
            "spend":      spend_by_day[day_str],
        })

    return result


def get_weekly_summary() -> dict:
    this_week = parse_aggregated_metrics("Weekly", time_offset=0)

    total_focus_mins = int(this_week["total_focus_mins"])
    total_focus_hours = round(total_focus_mins / 60, 1)

    task_breakdown: dict[str, int] = this_week.get("task_time_breakdown", {})
    if task_breakdown:
        top_task      = max(task_breakdown, key=task_breakdown.get)
        top_task_mins = int(task_breakdown[top_task])
    else:
        top_task      = ""
        top_task_mins = 0

    this_week_expense = float(this_week["total_expense"])
    completed_tasks   = int(this_week["completed_tasks"])
    pending_tasks     = int(this_week["pending_tasks"])

    target_dates = this_week.get("target_dates", [])
    week_start   = target_dates[0]  if target_dates else ""
    week_end     = target_dates[-1] if target_dates else ""

    last_week         = parse_aggregated_metrics("Weekly", time_offset=-1)
    last_week_expense = float(last_week["total_expense"])

    if last_week_expense == 0.0:
        expense_change_pct: float | None = None
    else:
        expense_change_pct = round(
            (this_week_expense - last_week_expense) / last_week_expense * 100, 1
        )

    return {
        "total_focus_mins":   total_focus_mins,
        "total_focus_hours":  total_focus_hours,
        "top_task":           top_task,
        "top_task_mins":      top_task_mins,
        "completed_tasks":    completed_tasks,
        "pending_tasks":      pending_tasks,
        "this_week_expense":  this_week_expense,
        "last_week_expense":  last_week_expense,
        "expense_change_pct": expense_change_pct,
        "week_start":         week_start,
        "week_end":           week_end,
    }


def get_target_dates(current_interval, time_offset):
    base_today = datetime.now().date()

    if current_interval == "Daily":
        target = base_today + timedelta(days=time_offset)
        return [target.strftime("%Y-%m-%d")]

    elif current_interval == "Weekly":
        start = base_today + timedelta(days=(time_offset * 7) - 6)
        return [(start + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(7)]

    else:
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

    tasks           = data.get("tasks", [])
    completed_count = len([t for t in tasks if t.get("completed")])
    pending_count   = len(tasks) - completed_count

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


# ── Badge evaluation ──────────────────────────────────────────────────────────

def evaluate_and_unlock_badges() -> list:
    data   = dm.load_data()
    newly_unlocked = []

    if len(data.get("focus_logs", [])) >= 1:
        if dm.unlock_badge("first_focus"):
            newly_unlocked.append("first_focus")

    streak = calculate_focus_streak()
    for badge_id, threshold in [("streak_3", 3), ("streak_7", 7), ("streak_30", 30)]:
        if streak >= threshold:
            if dm.unlock_badge(badge_id):
                newly_unlocked.append(badge_id)

    completed_count = len([t for t in data.get("tasks", []) if t.get("completed")])
    for badge_id, threshold in [("tasks_10", 10), ("tasks_50", 50)]:
        if completed_count >= threshold:
            if dm.unlock_badge(badge_id):
                newly_unlocked.append(badge_id)

    total_focus_minutes = sum(
        log.get("duration", 0)
        for log in data.get("focus_logs", [])
        if isinstance(log.get("duration"), (int, float))
    )
    total_focus_hours = total_focus_minutes / 60
    for badge_id, threshold in [("focus_10h", 10), ("focus_100h", 100)]:
        if total_focus_hours >= threshold:
            if dm.unlock_badge(badge_id):
                newly_unlocked.append(badge_id)

    if len(data.get("expenses", [])) >= 10:
        if dm.unlock_badge("expense_logged_10"):
            newly_unlocked.append("expense_logged_10")

    monthly_budget = dm.get_goals().get("monthly_expense_budget", 0)
    if monthly_budget and monthly_budget > 0:
        now        = datetime.now()
        month_str  = now.strftime("%Y-%m")
        month_spend = sum(
            float(exp.get("amount", 0))
            for exp in data.get("expenses", [])
            if str(exp.get("date", "")).startswith(month_str)
        )
        if month_spend < monthly_budget:
            if dm.unlock_badge("budget_month"):
                newly_unlocked.append("budget_month")

    return newly_unlocked