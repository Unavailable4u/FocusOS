# ============================================================
# FocusOS — Unified Color Palette
# Single source of truth. All pages import from here.
# Place this file at:  modules/color_palette.py
# ============================================================

# ── Known task / focus colors ────────────────────────────────────────────────
# Only "General Study" is a built-in default focus task.
# All other task names are user-created and get colors from OVERFLOW_PALETTE.
TASK_COLORS = {
    "general study": "#00FFFF",   # Cyan — the default built-in focus task
}

# Overflow palette — for dynamically-created / unknown task names.
# Each color is highly distinct from its neighbours.
OVERFLOW_PALETTE = [
    "#00E676",   # Vivid Green
    "#FFEA00",   # Vivid Yellow
    "#FF9100",   # Vivid Orange
    "#D500F9",   # Vivid Purple
    "#00B0FF",   # Sky Blue
    "#FF4081",   # Hot Pink
    "#76FF03",   # Lime
    "#F50057",   # Deep Pink
]

# ── Expense category colors ──────────────────────────────────────────────────
# Mirror task colors so charts stay consistent across pages.
EXPENSE_COLORS = {
    "study":     "#00FFFF",   # Cyan
    "food":      "#FF1744",   # Vivid Red
    "transport": "#1565C0",   # Deep Blue
    "other":     "#95A5A6",   # Slate Grey
}

# ── Swatch palette exposed to the Settings UI ───────────────────────────────
# 12 high-contrast swatches for the color picker grid.
SWATCH_PALETTE = [
    "#00FFFF",   # Cyan
    "#00E676",   # Vivid Green
    "#FFEA00",   # Vivid Yellow
    "#FF9100",   # Vivid Orange
    "#FF1744",   # Vivid Red
    "#D500F9",   # Vivid Purple
    "#00B0FF",   # Sky Blue
    "#FF4081",   # Hot Pink
    "#76FF03",   # Lime
    "#F50057",   # Deep Pink
    "#1565C0",   # Deep Blue
    "#95A5A6",   # Slate Grey
]


# ── Helper functions ─────────────────────────────────────────────────────────

def _load_overrides() -> tuple[dict, dict]:
    """
    Lazily loads color overrides from data_manager to avoid a circular-import
    at module level.  Returns (task_color_overrides, category_color_overrides).
    Both dicts are keyed by **lowercase** names.
    """
    try:
        import data_manager as dm
        settings = dm.get_settings()
        task_ov = {k.strip().lower(): v for k, v in
                   settings.get("task_color_overrides", {}).items()}
        cat_ov  = {k.strip().lower(): v for k, v in
                   settings.get("category_color_overrides", {}).items()}
        return task_ov, cat_ov
    except Exception:
        return {}, {}


def get_task_color(task_name: str, all_known_tasks: list = None) -> str:
    """
    Returns a consistent, high-contrast color for any task name.

    Priority order:
      1. User override  (settings["task_color_overrides"][name])
      2. Built-in map   (TASK_COLORS)
      3. Stable index   (if all_known_tasks supplied)
      4. Hash fallback  (OVERFLOW_PALETTE)
    """
    key = str(task_name).strip().lower()

    # 1. User override
    task_ov, _ = _load_overrides()
    if key in task_ov:
        return task_ov[key]

    # 2. Built-in fixed map
    if key in TASK_COLORS:
        return TASK_COLORS[key]

    # 3. Stable-index assignment
    if all_known_tasks:
        lowered = [t.strip().lower() for t in all_known_tasks]
        if key in lowered:
            idx = lowered.index(key)
            return OVERFLOW_PALETTE[idx % len(OVERFLOW_PALETTE)]

    # 4. Deterministic hash fallback
    return OVERFLOW_PALETTE[abs(hash(key)) % len(OVERFLOW_PALETTE)]


def get_expense_color(cat_name: str) -> str:
    """
    Returns a consistent color for an expense category name.

    Priority order:
      1. User override  (settings["category_color_overrides"][name])
      2. Built-in map   (EXPENSE_COLORS)
      3. Hash fallback  (OVERFLOW_PALETTE)
    """
    key = str(cat_name).strip().lower()

    # 1. User override
    _, cat_ov = _load_overrides()
    if key in cat_ov:
        return cat_ov[key]

    # 2. Built-in fixed map
    if key in EXPENSE_COLORS:
        return EXPENSE_COLORS[key]

    # 3. Hash fallback
    return OVERFLOW_PALETTE[abs(hash(key)) % len(OVERFLOW_PALETTE)]


def get_unified_color(name: str, all_known_tasks: list = None) -> str:
    """
    Single entry-point used by the dashboard so focus bars and expense bars
    share exactly the same hues.

    Checks EXPENSE_COLORS / category overrides first (covers names like
    'food'), then falls through to get_task_color for focus task names.
    """
    key = str(name).strip().lower()

    # Check category override and built-in expense map first
    _, cat_ov = _load_overrides()
    if key in cat_ov:
        return cat_ov[key]

    if key in EXPENSE_COLORS:
        return EXPENSE_COLORS[key]

    return get_task_color(name, all_known_tasks)