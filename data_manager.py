import json
import os
from datetime import datetime

DATA_FILE = "data.json"

def initialize_db():
    import os, json
    if not os.path.exists(DATA_FILE):
        default_data = {
            "tasks": [],
            "focus_logs": [],
            "expenses": [],
            "categories": ["Study", "Food", "Transport", "Other"]
        }
        with open(DATA_FILE, "w") as f:
            json.dump(default_data, f, indent=4)
    else:
        data = load_data()
        if "categories" not in data:
            data["categories"] = ["Study", "Food", "Transport", "Other"]
            save_data(data)

# --- BUG 5 FIX: update_expense now preserves the original date ---
def update_expense(expense_index, new_title, new_amount, new_category, new_date=None):
    data = load_data()
    if 0 <= expense_index < len(data.get("expenses", [])):
        # Preserve the original date if no new date is provided
        original_date = data["expenses"][expense_index].get(
            "date", datetime.now().strftime("%Y-%m-%d")
        )
        data["expenses"][expense_index] = {
            "title": new_title,
            "amount": float(new_amount),
            "category": new_category,
            "date": new_date if new_date else original_date  # <-- FIXED: date is no longer dropped
        }
        save_data(data)

def delete_expense(expense_index):
    data = load_data()
    if 0 <= expense_index < len(data.get("expenses", [])):
        data["expenses"].pop(expense_index)
        save_data(data)

# --- DYNAMIC CATEGORY MANAGEMENT ---
def add_custom_category(category_name):
    data = load_data()
    if "categories" not in data:
        data["categories"] = ["Study", "Food", "Transport", "Other"]

    clean_cat = category_name.strip()
    if clean_cat and clean_cat not in data["categories"]:
        data["categories"].append(clean_cat)
        save_data(data)
        return True
    return False

def delete_custom_category(category_name):
    data = load_data()
    if category_name in data.get("categories", []):
        data["categories"].remove(category_name)

        for exp in data.get("expenses", []):
            if exp.get("category") == category_name:
                exp["category"] = "Other"

        if "Other" not in data["categories"]:
            data["categories"].append("Other")

        save_data(data)

def load_data():
    if not os.path.exists(DATA_FILE):
        return {
            "tasks": [], "expenses": [],
            "categories": ["Study", "Food", "Transport", "Other"],
            "focus_logs": [], "hourly_focus": {}, "hourly_task_distribution": {}
        }

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            content = f.read().strip()
            if not content:
                return {
                    "tasks": [], "expenses": [],
                    "categories": ["Study", "Food", "Transport", "Other"],
                    "focus_logs": [], "hourly_focus": {}, "hourly_task_distribution": {}
                }

            data = json.loads(content)

            if "tasks" not in data: data["tasks"] = []
            if "expenses" not in data: data["expenses"] = []
            if "categories" not in data: data["categories"] = ["Study", "Food", "Transport", "Other"]
            if "focus_logs" not in data: data["focus_logs"] = []
            if "hourly_focus" not in data: data["hourly_focus"] = {}
            if "hourly_task_distribution" not in data: data["hourly_task_distribution"] = {}

            return data

    except (json.JSONDecodeError, TypeError, ValueError):
        return {
            "tasks": [], "expenses": [],
            "categories": ["Study", "Food", "Transport", "Other"],
            "focus_logs": [], "hourly_focus": {}, "hourly_task_distribution": {}
        }

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

def add_task(title, quadrant):
    data = load_data()
    task_id = len(data["tasks"]) + 1 if data["tasks"] else 1
    new_task = {
        "id": task_id,
        "title": title,
        "quadrant": int(quadrant),
        "completed": False
    }
    data["tasks"].append(new_task)
    save_data(data)
    return new_task

def toggle_task_completion(task_id):
    data = load_data()
    for task in data["tasks"]:
        if task["id"] == task_id:
            task["completed"] = not task["completed"]
            break
    save_data(data)

# --- BUG 2 FIX: add_expense now saves the "date" field ---
def add_expense(title, amount, category):
    data = load_data()
    if "expenses" not in data:
        data["expenses"] = []

    new_expense = {
        "title": title,
        "amount": float(amount),
        "category": category,
        "date": datetime.now().strftime("%Y-%m-%d")  # <-- FIXED: date is now saved
    }
    data["expenses"].append(new_expense)
    save_data(data)
    return new_expense

# --- BUG 6 FIX: log_focus now also writes to hourly_task_distribution ---
# so that non-pomodoro focus logs appear correctly on the dashboard.
def log_focus(task_title, duration_minutes):
    data = load_data()
    now = datetime.now()
    today = now.strftime("%Y-%m-%d")
    hour = now.hour

    # Keep existing focus_logs entry as before
    new_log = {
        "date": today,
        "hour": hour,
        "duration": int(duration_minutes),
        "task": task_title
    }
    data["focus_logs"].append(new_log)

    # FIXED: Also write to hourly_task_distribution so engine.py picks it up
    if "hourly_task_distribution" not in data:
        data["hourly_task_distribution"] = {}
    if today not in data["hourly_task_distribution"]:
        data["hourly_task_distribution"][today] = {str(h): {} for h in range(24)}
    hour_str = str(hour)
    if hour_str not in data["hourly_task_distribution"][today]:
        data["hourly_task_distribution"][today][hour_str] = {}
    task_map = data["hourly_task_distribution"][today][hour_str]
    task_map[task_title] = task_map.get(task_title, 0) + int(duration_minutes)

    save_data(data)
