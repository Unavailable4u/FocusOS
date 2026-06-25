import json
import os
import csv
from datetime import datetime


DATA_FILE = "data.json"


# ── Badge definitions ─────────────────────────────────────────────────────────

BADGE_DEFINITIONS = {
    "first_focus":        {"label": "First Focus",        "icon": "🎯", "desc": "Complete your first focus session"},
    "streak_3":           {"label": "3-Day Streak",        "icon": "🔥", "desc": "3 consecutive days of focus"},
    "streak_7":           {"label": "Week Warrior",        "icon": "⚡", "desc": "7-day focus streak"},
    "streak_30":          {"label": "Iron Discipline",     "icon": "💎", "desc": "30-day focus streak"},
    "tasks_10":           {"label": "Task Crusher",        "icon": "✅", "desc": "Complete 10 tasks"},
    "tasks_50":           {"label": "Productivity Master", "icon": "🏆", "desc": "Complete 50 tasks"},
    "budget_month":       {"label": "Budget Hero",         "icon": "💰", "desc": "Stay under budget for a full month"},
    "focus_10h":          {"label": "Deep Worker",         "icon": "🧠", "desc": "Log 10 total hours of focus"},
    "focus_100h":         {"label": "Century Club",        "icon": "🌟", "desc": "Log 100 total hours of focus"},
    "expense_logged_10":  {"label": "Accountant",          "icon": "📊", "desc": "Log 10 expenses"},
}


def load_data():
    if not os.path.exists(DATA_FILE):
        return {
            "tasks": [], "expenses": [],
            "categories": ["Study", "Food", "Transport", "Other"],
            "focus_logs": [], "hourly_focus": {},
            "hourly_task_distribution": {},
            "budgets": {}, "settings": {}, "goals": {},
            "journal": [], "pomodoro_notes": []
        }

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            content = f.read().strip()
            if not content:
                return {
                    "tasks": [], "expenses": [],
                    "categories": ["Study", "Food", "Transport", "Other"],
                    "focus_logs": [], "hourly_focus": {},
                    "hourly_task_distribution": {},
                    "budgets": {}, "settings": {}, "goals": {},
                    "journal": [], "pomodoro_notes": []
                }

            data = json.loads(content)

            if "tasks"                    not in data: data["tasks"]                    = []
            if "expenses"                 not in data: data["expenses"]                 = []
            if "categories"               not in data: data["categories"]               = ["Study", "Food", "Transport", "Other"]
            if "focus_logs"               not in data: data["focus_logs"]               = []
            if "hourly_focus"             not in data: data["hourly_focus"]             = {}
            if "hourly_task_distribution" not in data: data["hourly_task_distribution"] = {}
            if "budgets"                  not in data: data["budgets"]                  = {}
            if "settings"                 not in data: data["settings"]                 = {}
            if "goals"                    not in data: data["goals"]                    = {}
            if "journal"                  not in data: data["journal"]                  = []
            if "pomodoro_notes"           not in data: data["pomodoro_notes"]           = []

            return data

    except (json.JSONDecodeError, TypeError, ValueError):
        return {
            "tasks": [], "expenses": [],
            "categories": ["Study", "Food", "Transport", "Other"],
            "focus_logs": [], "hourly_focus": {},
            "hourly_task_distribution": {},
            "budgets": {}, "settings": {}, "goals": {},
            "journal": [], "pomodoro_notes": []
        }


def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)


# ── Data Export helpers ───────────────────────────────────────────────────────

def export_tasks_csv(filepath: str) -> bool:
    """
    Writes all tasks to a CSV file at *filepath*.

    Columns: id, title, quadrant, completed, due_date

    Returns True on success, False on any I/O or serialisation error.
    """
    fieldnames = ["id", "title", "quadrant", "completed", "due_date"]
    try:
        tasks = load_data().get("tasks", [])
        with open(filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(tasks)
        return True
    except (OSError, csv.Error):
        return False


def export_expenses_csv(filepath: str) -> bool:
    """
    Writes all expenses to a CSV file at *filepath*.

    Columns: title, amount, category, date

    Returns True on success, False on any I/O or serialisation error.
    """
    fieldnames = ["title", "amount", "category", "date"]
    try:
        expenses = load_data().get("expenses", [])
        with open(filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(expenses)
        return True
    except (OSError, csv.Error):
        return False


# ── Database initialisation ───────────────────────────────────────────────────

def initialize_db():
    if not os.path.exists(DATA_FILE):
        default_data = {
            "tasks": [],
            "focus_logs": [],
            "expenses": [],
            "categories": ["Study", "Food", "Transport", "Other"],
            "budgets": {},         # legacy/deprecated — see set_category_budget()
            "settings": {},        # profile name, currency, accent colour, theme, etc.
            "goals": {
                "daily_focus_minutes": 120,
                "monthly_expense_budget": 0,
                "category_budgets": {}
            },
            "journal": [],         # [{"date": "YYYY-MM-DD", "mood": 3, "went_well": "...", "blockers": "..."}]
            "pomodoro_notes": []   # [{"date": "...", "task": "...", "note": "..."}]
        }
        with open(DATA_FILE, "w") as f:
            json.dump(default_data, f, indent=4)
    else:
        data = load_data()
        changed = False
        if "categories"    not in data: data["categories"]    = ["Study", "Food", "Transport", "Other"]; changed = True
        if "budgets"       not in data: data["budgets"]       = {};  changed = True
        if "settings"      not in data: data["settings"]      = {};  changed = True
        if "goals"         not in data: data["goals"]         = {};  changed = True
        if "journal"       not in data: data["journal"]       = [];  changed = True
        if "pomodoro_notes" not in data: data["pomodoro_notes"] = []; changed = True
        if changed:
            save_data(data)

    # One-time migration: fold any legacy data["budgets"] entries into
    # goals["category_budgets"], which is now the single source of truth.
    _migrate_legacy_budgets()


def _migrate_legacy_budgets() -> None:
    """
    Moves any entries still sitting in the old data["budgets"] dict into
    goals["category_budgets"]. Existing goals-side entries win on conflict
    (so a value the user already set under the new system is never
    clobbered by a stale legacy one). After merging, data["budgets"] is
    cleared so the legacy path stops being read or written anywhere.

    Safe to call repeatedly — it's a no-op once data["budgets"] is empty.
    """
    data = load_data()
    legacy_budgets = data.get("budgets", {})
    if not legacy_budgets:
        return

    goals = dict(data.get("goals", {}))
    category_budgets = dict(goals.get("category_budgets", {}))

    changed = False
    for cat, amount in legacy_budgets.items():
        if cat not in category_budgets and amount:
            category_budgets[cat] = amount
            changed = True

    if changed:
        goals["category_budgets"] = category_budgets
        data["goals"] = goals

    data["budgets"] = {}
    save_data(data)


# ── Task helpers ──────────────────────────────────────────────────────────────

def add_task(title, quadrant, due_date=None):
    data = load_data()
    task_id = len(data["tasks"]) + 1 if data["tasks"] else 1
    new_task = {
        "id": task_id,
        "title": title,
        "quadrant": int(quadrant),
        "completed": False,
        "due_date": due_date  # Optional "YYYY-MM-DD" string, or None
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


# ── Expense helpers ───────────────────────────────────────────────────────────

# BUG 2 FIX: add_expense now saves the "date" field
def add_expense(title, amount, category):
    data = load_data()
    if "expenses" not in data:
        data["expenses"] = []

    new_expense = {
        "title": title,
        "amount": float(amount),
        "category": category,
        "date": datetime.now().strftime("%Y-%m-%d")
    }
    data["expenses"].append(new_expense)
    save_data(data)
    return new_expense


# BUG 5 FIX: update_expense now preserves the original date
def update_expense(expense_index, new_title, new_amount, new_category, new_date=None):
    data = load_data()
    if 0 <= expense_index < len(data.get("expenses", [])):
        original_date = data["expenses"][expense_index].get(
            "date", datetime.now().strftime("%Y-%m-%d")
        )
        data["expenses"][expense_index] = {
            "title": new_title,
            "amount": float(new_amount),
            "category": new_category,
            "date": new_date if new_date else original_date
        }
        save_data(data)


def delete_expense(expense_index):
    data = load_data()
    if 0 <= expense_index < len(data.get("expenses", [])):
        data["expenses"].pop(expense_index)
        save_data(data)


# ── Category management ───────────────────────────────────────────────────────

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

        # Remove budget for deleted category too (goals/category_budgets —
        # the single source of truth; see set_category_budget()).
        goals = dict(data.get("goals", {}))
        category_budgets = dict(goals.get("category_budgets", {}))
        if category_budgets.pop(category_name, None) is not None:
            goals["category_budgets"] = category_budgets
            data["goals"] = goals

        # Remove any color override for deleted category
        data.get("settings", {}).get("category_color_overrides", {}).pop(category_name, None)

        save_data(data)


# ── Budget management (DEPRECATED — kept only for backward compatibility) ─────
#
# data["budgets"] is no longer the source of truth. All reads/writes for
# per-category budgets now go through set_category_budget()/get_category_budget()
# below, which live in goals["category_budgets"]. These two functions are
# kept only in case any external/legacy caller still references them, and
# they now delegate to the goals-based helpers so behaviour stays unified.

def set_budget(category_name: str, amount: float):
    """Deprecated — use set_category_budget(). Kept as a thin alias."""
    set_category_budget(category_name, amount)


def get_budgets() -> dict:
    """Deprecated — use get_goals()['category_budgets']. Kept as a thin alias."""
    return get_goals().get("category_budgets", {})


# ── Focus logging ─────────────────────────────────────────────────────────────

# BUG 6 FIX: log_focus now also writes to hourly_task_distribution
def log_focus(task_title, duration_minutes):
    data = load_data()
    now   = datetime.now()
    today = now.strftime("%Y-%m-%d")
    hour  = now.hour

    new_log = {
        "date": today,
        "hour": hour,
        "duration": int(duration_minutes),
        "task": task_title
    }
    data["focus_logs"].append(new_log)

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


# ── Settings helpers ──────────────────────────────────────────────────────────

def get_settings() -> dict:
    """
    Returns the full settings dict from data.json.

    Expected keys (all optional — callers should use .get() with a default):
        profile_name            : str   – display name shown in the UI
        currency_symbol         : str   – e.g. "৳", "$", "€"
        accent_color            : str   – hex string, e.g. "#00FFFF"
        glass_theme             : bool  – whether the glass/blur theme is active
        bg_image_path           : str   – absolute path to a background image, or ""
        color_overrides         : dict  – {token: hex} for per-token colour overrides
        task_color_overrides    : dict  – {task_title: hex} user-chosen task colors
        category_color_overrides: dict  – {category_name: hex} user-chosen cat colors
    """
    return load_data().get("settings", {})


def save_settings(updates: dict) -> None:
    """
    Merges *updates* into data["settings"] and persists.
    Passing an empty dict is a no-op (safe to call unconditionally).
    """
    if not updates:
        return
    data = load_data()
    if "settings" not in data:
        data["settings"] = {}
    data["settings"].update(updates)
    save_data(data)


def get_currency_symbol() -> str:
    """
    Returns the configured currency symbol (settings.currency_symbol),
    defaulting to "৳" (Taka) when unset or blank.
    """
    symbol = get_settings().get("currency_symbol", "৳")
    return symbol if symbol else "৳"


# ── Badge helpers ─────────────────────────────────────────────────────────────

def get_unlocked_badges() -> list:
    """Returns the list of unlocked badge IDs from settings."""
    return list(get_settings().get("unlocked_badges", []))


def unlock_badge(badge_id: str) -> bool:
    """
    Unlocks badge_id if not already unlocked.
    Returns True if this is a new unlock, False if already had it.
    """
    current = get_unlocked_badges()
    if badge_id in current:
        return False
    current.append(badge_id)
    save_settings({"unlocked_badges": current})
    return True


# ── Color override helpers ────────────────────────────────────────────────────

def set_task_color_override(task_title: str, hex_color: str) -> None:
    """
    Saves a user-chosen color for a specific task title.
    Pass hex_color="" or None to remove the override.
    """
    settings = get_settings()
    overrides = dict(settings.get("task_color_overrides", {}))
    if hex_color:
        overrides[task_title] = hex_color
    else:
        overrides.pop(task_title, None)
    save_settings({"task_color_overrides": overrides})


def set_category_color_override(category_name: str, hex_color: str) -> None:
    """
    Saves a user-chosen color for a specific expense category.
    Pass hex_color="" or None to remove the override.
    """
    settings = get_settings()
    overrides = dict(settings.get("category_color_overrides", {}))
    if hex_color:
        overrides[category_name] = hex_color
    else:
        overrides.pop(category_name, None)
    save_settings({"category_color_overrides": overrides})


def get_task_color_overrides() -> dict:
    """Returns {task_title: hex} for all user overrides."""
    return get_settings().get("task_color_overrides", {})


def get_category_color_overrides() -> dict:
    """Returns {category_name: hex} for all user overrides."""
    return get_settings().get("category_color_overrides", {})


# ── Backup / Restore helpers ──────────────────────────────────────────────────

# Top-level keys that a valid FocusOS data file must contain at least one of.
_EXPECTED_KEYS = {"tasks", "expenses", "focus_logs", "categories"}


def backup_data(dest_path: str) -> None:
    """
    Copies the current DATA_FILE to *dest_path*.
    Raises OSError on any I/O failure so the caller can surface it.
    """
    import shutil
    # Ensure latest in-memory state is flushed before copying
    if not os.path.exists(DATA_FILE):
        # Nothing to back up — write a clean default so the copy succeeds
        save_data(load_data())
    shutil.copy2(DATA_FILE, dest_path)


def validate_backup(src_path: str) -> tuple[bool, str]:
    """
    Checks that *src_path* is a readable JSON file that looks like FocusOS data.

    Returns
    -------
    (True, "")              – file is valid
    (False, reason_string)  – file is invalid, with a human-readable reason
    """
    try:
        with open(src_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        return False, "File not found."
    except (json.JSONDecodeError, ValueError):
        return False, "File is not valid JSON."
    except OSError as exc:
        return False, f"Could not read file: {exc}"

    if not isinstance(data, dict):
        return False, "JSON root must be an object, not a list or primitive."

    missing = _EXPECTED_KEYS - data.keys()
    if missing:
        return False, f"Missing expected keys: {', '.join(sorted(missing))}."

    return True, ""


def restore_data(src_path: str) -> tuple[bool, str]:
    """
    Validates *src_path* then overwrites DATA_FILE with its contents.

    Returns
    -------
    (True, "")              – restore succeeded
    (False, reason_string)  – validation or write failed
    """
    ok, reason = validate_backup(src_path)
    if not ok:
        return False, reason

    try:
        with open(src_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        save_data(data)
    except OSError as exc:
        return False, f"Could not write data file: {exc}"

    # Keep the legacy-budgets migration consistent after a restore too,
    # in case the restored backup pre-dates the goals-based budget system.
    _migrate_legacy_budgets()

    return True, ""


# ── Background image helpers ──────────────────────────────────────────────────

def set_background_image_path(path: str) -> None:
    """
    Persists *path* as the active wallpaper.
    *path* should be the copied asset path under assets/wallpapers/ so it
    remains valid even if the user's original file is moved.
    """
    save_settings({"background_image_path": path})


def clear_background_image_path() -> None:
    """Removes the wallpaper setting so the app falls back to plain bgcolor."""
    save_settings({"background_image_path": ""})


def get_background_image_path() -> str:
    """Returns the stored wallpaper path, or '' if none is set."""
    return get_settings().get("background_image_path", "")


# ── Goals helpers ─────────────────────────────────────────────────────────────

# Concrete default shape for data["goals"]. Every caller goes through
# get_goals()/save_goals() rather than touching the dict directly, so this
# is the single place the shape is defined.
_DEFAULT_GOALS = {
    "daily_focus_minutes": 120,
    "monthly_expense_budget": 0,
    "category_budgets": {}
}


def get_goals() -> dict:
    """
    Returns the full goals dict from data.json, backfilled with defaults
    for any missing keys so callers never need their own fallback logic.

    Keys:
        daily_focus_minutes   : int   – target focus minutes per day (default 120)
        monthly_expense_budget: float – overall monthly spending cap (default 0 = unset)
        category_budgets      : dict  – {category: float} per-category monthly caps (default {})
                                          — THIS IS THE SOLE SOURCE OF TRUTH for
                                          per-category budgets across the whole app.
    """
    goals = dict(load_data().get("goals", {}))
    for key, default in _DEFAULT_GOALS.items():
        if key not in goals:
            goals[key] = {} if isinstance(default, dict) else default
    return goals


def save_goals(updates: dict) -> None:
    """
    Merges *updates* into data["goals"] and persists, backfilling any
    missing default keys first so the stored dict always has the full shape.

    For "category_budgets", *updates* is merged one level deep into the
    existing sub-dict (so callers can set/clear a single category without
    re-sending the whole map). All other keys are simple overwrites.
    """
    if not updates:
        return
    data = load_data()
    goals = dict(data.get("goals", {}))
    for key, default in _DEFAULT_GOALS.items():
        if key not in goals:
            goals[key] = {} if isinstance(default, dict) else default

    for key, value in updates.items():
        if key == "category_budgets" and isinstance(value, dict):
            merged = dict(goals.get("category_budgets", {}))
            for cat, amount in value.items():
                if amount:
                    merged[cat] = amount
                else:
                    merged.pop(cat, None)
            goals["category_budgets"] = merged
        else:
            goals[key] = value

    data["goals"] = goals
    save_data(data)


def set_category_budget(category: str, amount: float) -> None:
    """
    Sets (or clears, if amount is falsy/<=0) the monthly budget for a single
    category inside goals["category_budgets"], via save_goals(). This is the
    single source of truth for per-category budgets — the legacy
    data["budgets"] dict is no longer read or written anywhere in the app.
    """
    save_goals({"category_budgets": {category: amount}})


def get_category_budget(category: str) -> float:
    """
    Returns the monthly budget for *category* from goals["category_budgets"],
    or 0 if no budget has been set for it.
    """
    return get_goals().get("category_budgets", {}).get(category, 0)


# ── Pomodoro-notes helpers ────────────────────────────────────────────────────

def add_pomodoro_note(task_title: str, note: str) -> dict:
    """
    Appends a post-session note to data["pomodoro_notes"] and returns it.

    Stored shape: {"date": "YYYY-MM-DD", "time": "HH:MM", "task": str, "note": str}
    """
    data = load_data()
    if "pomodoro_notes" not in data:
        data["pomodoro_notes"] = []
    now    = datetime.now()
    record = {
        "date": now.strftime("%Y-%m-%d"),
        "time": now.strftime("%H:%M"),
        "task": task_title,
        "note": note,
    }
    data["pomodoro_notes"].append(record)
    save_data(data)
    return record


def get_pomodoro_notes(date_str: str | None = None) -> list:
    """
    Returns pomodoro notes, optionally filtered to a single date ("YYYY-MM-DD").
    Results are sorted newest-first.
    """
    notes = load_data().get("pomodoro_notes", [])
    if date_str:
        notes = [n for n in notes if n.get("date") == date_str]
    return sorted(notes, key=lambda n: (n.get("date", ""), n.get("time", "")), reverse=True)


# ── Journal helpers ───────────────────────────────────────────────────────────

def add_journal_entry(mood_rating: int, went_well: str, blockers: str) -> dict:
    """
    Upserts today's journal entry in data["journal"].

    If an entry for today already exists it is updated in-place; otherwise
    a new one is appended.  Only one entry per calendar day is ever stored.

    Stored shape:
        {"date": "YYYY-MM-DD", "mood": int, "went_well": str, "blockers": str}

    Returns the final (inserted or updated) entry dict.
    """
    data  = load_data()
    today = datetime.now().strftime("%Y-%m-%d")

    entry = {
        "date":      today,
        "mood":      int(mood_rating),
        "went_well": went_well.strip(),
        "blockers":  blockers.strip(),
    }

    journal = data.get("journal", [])
    for i, existing in enumerate(journal):
        if existing.get("date") == today:
            journal[i] = entry          # update in-place — no duplicate
            data["journal"] = journal
            save_data(data)
            return entry

    journal.append(entry)               # first entry for today
    data["journal"] = journal
    save_data(data)
    return entry


def get_journal_entries(limit: int = 30) -> list:
    """
    Returns the most recent journal entries, newest-first.

    Parameters
    ----------
    limit : int
        Maximum number of entries to return (default 30).
        Pass 0 or a negative number to return all entries.

    Returns
    -------
    list of dicts, each with keys: date, mood, went_well, blockers.
    """
    entries = load_data().get("journal", [])
    entries = sorted(entries, key=lambda e: e.get("date", ""), reverse=True)
    if limit and limit > 0:
        entries = entries[:limit]
    return entries