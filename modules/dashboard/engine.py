import sys, os
from datetime import datetime, timedelta
import data_manager as dm

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
        # --- BUG 7 FIX: Monthly dates were in reverse order (newest→oldest).
        # Old code used `range(30)` without reversing, so day 0 was "today" and
        # day 29 was "30 days ago", making the expense graph bars go right-to-left.
        # Fix: build from oldest to newest so the graph reads left→right correctly.
        start = base_today + timedelta(days=(time_offset * 30) - 29)
        return [(start + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(30)]

def get_date_range_display_string(current_interval, target_dates):
    if not target_dates:
        return ""
    if current_interval == "Daily":
        try:
            d = datetime.strptime(target_dates[0], "%Y-%m-%d")
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
        start_lbl = datetime.strptime(sorted_dates[0], "%Y-%m-%d").strftime("%b %d")
        end_lbl = datetime.strptime(sorted_dates[-1], "%Y-%m-%d").strftime("%b %d, %Y")
        return f"Range Window: {start_lbl} - {end_lbl}"
    except (ValueError, IndexError):
        return f"Range: {sorted_dates[0]} to {sorted_dates[-1]}"

def parse_aggregated_metrics(current_interval, time_offset):
    data = dm.load_data()
    target_dates = get_target_dates(current_interval, time_offset)

    total_focus_mins = 0
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
    tasks = data.get("tasks", [])
    completed_count = len([t for t in tasks if t.get("completed")])
    pending_count = len(tasks) - completed_count

    # EXPENSE PROCESSING
    total_expense = 0.0
    category_expense_breakdown = {}
    expenses = data.get("expenses", [])

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
        "total_focus_mins": total_focus_mins,
        "completed_tasks": completed_count,
        "pending_tasks": pending_count,
        "total_expense": total_expense,
        "chrono_distribution": chrono_distribution,
        "task_time_breakdown": task_time_breakdown,
        "category_expense_breakdown": category_expense_breakdown,
        "target_dates": target_dates
    }
