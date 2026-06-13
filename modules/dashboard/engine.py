import sys, os
from datetime import datetime, timedelta
import data_manager as dm

def get_target_dates(current_interval, time_offset):
    # base_today is 2026-06-13
    base_today = datetime.now().date()
    
    if current_interval == "Daily":
        # Ensure time_offset is 0 for "today"
        target = base_today + timedelta(days=time_offset)
        return [target.strftime("%Y-%m-%d")]
    # ... rest of your code
        
    elif current_interval == "Weekly":
        # Returns the range of 7 days for the weekly view
        return [(base_today + timedelta(days=(time_offset * 7) - i)).strftime("%Y-%m-%d") for i in reversed(range(7))]
        
    else:
        # Returns the range of 30 days for the monthly view
        return [(base_today + timedelta(days=(time_offset * 30) - i)).strftime("%Y-%m-%d") for i in range(30)]

def get_date_range_display_string(current_interval, target_dates):
    """Returns a formatted string for the dashboard banner."""
    if not target_dates:
        return ""
    if current_interval == "Daily":
        return f"Showing Log: {target_dates[0]}"
    
    sorted_dates = sorted(target_dates)
    try:
        start_lbl = datetime.strptime(sorted_dates[0], "%Y-%m-%d").strftime("%b %d")
        end_lbl = datetime.strptime(sorted_dates[-1], "%Y-%m-%d").strftime("%b %d, %Y")
        return f"Range Window: {start_lbl} - {end_lbl}"
    except (ValueError, IndexError):
        return f"Range: {sorted_dates[0]} to {sorted_dates[-1]}"

def parse_aggregated_metrics(current_interval, time_offset):
    """
    Parses data and returns metrics. 
    Restores task keys to prevent 'KeyError' crashes.
    """
    data = dm.load_data()
    target_dates = get_target_dates(current_interval, time_offset)
    
    # 1. Initialize metrics
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
                            
                            # Aggregate into chrono map
                            if current_interval == "Daily":
                                h_key = str(int(hour_str))
                                if h_key not in chrono_distribution: chrono_distribution[h_key] = {}
                                chrono_distribution[h_key][task] = chrono_distribution[h_key].get(task, 0) + mins

    # 2. RESTORE TASK KEYS (Prevents KeyError)
    tasks = data.get("tasks", [])
    completed_count = len([t for t in tasks if t.get("completed")])
    pending_count = len(tasks) - completed_count

    # 3. EXPENSE PROCESSING (Exact Date Match)
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

    # Return full dictionary with required keys
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