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
            "categories": ["Study", "Food", "Transport", "Other"] # Added default tracking
        }
        with open(DATA_FILE, "w") as f:
            json.dump(default_data, f, indent=4)
    else:
        # Graceful migration check: ensure categories key exists in old files
        data = load_data()
        if "categories" not in data:
            data["categories"] = ["Study", "Food", "Transport", "Other"]
            save_data(data)

def update_expense(expense_index, new_title, new_amount, new_category):
    data = load_data()
    if 0 <= expense_index < len(data.get("expenses", [])):
        data["expenses"][expense_index] = {
            "title": new_title,
            "amount": float(new_amount),
            "category": new_category
        }
        save_data(data)

def delete_expense(expense_index):
    data = load_data()
    if 0 <= expense_index < len(data.get("expenses", [])):
        data["expenses"].pop(expense_index)
        save_data(data)

# --- DYNAMIC CATEGORY MANAGEMENT LOGIC ---
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
        
        # Safe fallback: reassign orphan expenses under this category to "Other"
        for exp in data.get("expenses", []):
            if exp.get("category") == category_name:
                exp["category"] = "Other"
                
        if "Other" not in data["categories"]:
            data["categories"].append("Other")
            
        save_data(data)

def load_data():
    # If the file doesn't exist, create it with a pristine, comprehensive schema baseline
    if not os.path.exists(DATA_FILE):
        return {"tasks": [], "expenses": [], "categories": ["Study", "Food", "Transport", "Other"], "focus_logs": [], "hourly_focus": {}}
    
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            # Check if the file is completely empty to prevent json.decode crashes
            content = f.read().strip()
            if not content:
                return {"tasks": [], "expenses": [], "categories": ["Study", "Food", "Transport", "Other"], "focus_logs": [], "hourly_focus": {}}
            
            data = json.loads(content)
            
            # Safe Fallbacks: Ensure all necessary structural keys exist in memory
            if "tasks" not in data: data["tasks"] = []
            if "expenses" not in data: data["expenses"] = []
            if "categories" not in data: data["categories"] = ["Study", "Food", "Transport", "Other"]
            if "focus_logs" not in data: data["focus_logs"] = []
            if "hourly_focus" not in data: data["hourly_focus"] = {}
                
            return data
            
    except (json.JSONDecodeError, TypeError, ValueError):
        # Massive Safety Net: If the file got corrupted, return a clean dictionary template
        return {"tasks": [], "expenses": [], "categories": ["Study", "Food", "Transport", "Other"], "focus_logs": [], "hourly_focus": {}}

def save_data(data):
    """Saves the current data dictionary back to the file."""
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

def add_task(title, quadrant):
    data = load_data()
    # Generate a unique sequential ID
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
    """Finds a task by ID and flips its completed status."""
    data = load_data()
    for task in data["tasks"]:
        if task["id"] == task_id:
            task["completed"] = not task["completed"]
            break
    save_data(data)

def add_expense(title, amount, category):  # Ensure it has exactly these 3 parameters
    data = load_data()
    if "expenses" not in data:
        data["expenses"] = []
        
    new_expense = {
        "title": title,
        "amount": float(amount),
        "category": category
    }
    data["expenses"].append(new_expense)
    save_data(data)
    return new_expense
def log_focus(task_title, duration_minutes):
    data = load_data()
    now = datetime.now()
    new_log = {
        "date": now.strftime("%Y-%m-%d"),
        "hour": now.hour,
        "duration": int(duration_minutes),
        "task": task_title
    }
    data["focus_logs"].append(new_log)
    save_data(data)