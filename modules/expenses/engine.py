import sys
import os
from datetime import datetime, timedelta

try:
    import data_manager as dm
except ModuleNotFoundError:
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    import data_manager as dm

def load_expense_data():
    return dm.load_data()

def save_expense_data(data):
    dm.save_data(data)

def get_filter_date_range(filter_mode, anchor_date):
    """Returns exact date strings based on anchor_date."""
    if filter_mode == "Day":
        return [anchor_date.strftime("%Y-%m-%d")]
    elif filter_mode == "Week":
        return [(anchor_date - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(7)]
    else:
        return [(anchor_date - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(30)]



def get_filter_banner_string(filter_mode, anchor_date):
    if filter_mode == "Day":
        return f"Selected Date: {anchor_date.strftime('%Y-%m-%d')}"
    range_dates = sorted(get_filter_date_range(filter_mode, anchor_date))
    start_lbl = datetime.strptime(range_dates[0], "%Y-%m-%d").strftime("%b %d")
    end_lbl = datetime.strptime(range_dates[-1], "%Y-%m-%d").strftime("%b %d, %Y")
    return f"Scope: {start_lbl} - {end_lbl}"

def get_filtered_expenses(all_expenses, filter_mode, anchor_date):
    """
    Retrieves expenses by matching exact YYYY-MM-DD string keys.
    """
    target_dates = get_filter_date_range(filter_mode, anchor_date)
    filtered = []
    for idx, exp in enumerate(all_expenses):
        # We explicitly compare the string stored in 'date' to our target list
        exp_date = str(exp.get("date", "")).strip()
        if exp_date in target_dates:
            filtered.append((idx, exp))
    return filtered