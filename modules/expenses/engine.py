import sys
import os
from datetime import datetime, timedelta, date as date_type

try:
    import data_manager as dm
except ModuleNotFoundError:
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    import data_manager as dm

def load_expense_data():
    return dm.load_data()

def save_expense_data(data):
    dm.save_data(data)

def _to_date(anchor):
    """Normalise anchor to a plain date object regardless of input type."""
    if isinstance(anchor, datetime):
        return anchor.date()
    return anchor  # already a date

def get_filter_date_range(filter_mode, anchor_date):
    """Returns a list of YYYY-MM-DD strings for the selected range."""
    anchor = _to_date(anchor_date)
    if filter_mode == "Day":
        return [anchor.strftime("%Y-%m-%d")]
    elif filter_mode == "Week":
        # Chronological: 6 days ago → anchor day
        return [(anchor - timedelta(days=i)).strftime("%Y-%m-%d") for i in reversed(range(7))]
    else:
        # Chronological: 29 days ago → anchor day
        return [(anchor - timedelta(days=i)).strftime("%Y-%m-%d") for i in reversed(range(30))]

def get_filter_banner_string(filter_mode, anchor_date):
    anchor = _to_date(anchor_date)
    if filter_mode == "Day":
        today = datetime.now().date()
        label = anchor.strftime("%Y-%m-%d")
        if anchor == today:
            return f"Selected Date: {label} (Today)"
        elif anchor == today - timedelta(days=1):
            return f"Selected Date: {label} (Yesterday)"
        return f"Selected Date: {label}"
    range_dates = sorted(get_filter_date_range(filter_mode, anchor))
    start_lbl = datetime.strptime(range_dates[0],  "%Y-%m-%d").strftime("%b %d")
    end_lbl   = datetime.strptime(range_dates[-1], "%Y-%m-%d").strftime("%b %d, %Y")
    return f"Scope: {start_lbl} — {end_lbl}"

def get_filtered_expenses(all_expenses, filter_mode, anchor_date):
    target_dates = get_filter_date_range(filter_mode, anchor_date)
    filtered = []
    for idx, exp in enumerate(all_expenses):
        exp_date = str(exp.get("date", "")).strip()
        if exp_date in target_dates:
            filtered.append((idx, exp))
    return filtered