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


# ── Helper functions ─────────────────────────────────────────────────────────

def get_task_color(task_name: str, all_known_tasks: list = None) -> str:
    """
    Returns a consistent, high-contrast color for any task name.

    • Known names  → fixed color from TASK_COLORS.
    • Unknown names → deterministic color from OVERFLOW_PALETTE via hash,
      so the same name always gets the same color across every page.

    Optional `all_known_tasks` (ordered list of strings) can be passed to
    assign overflow colors by stable index rather than hash — useful when
    you want colors to stay the same even if task names are similar hashes.
    """
    key = str(task_name).strip().lower()

    if key in TASK_COLORS:
        return TASK_COLORS[key]

    if all_known_tasks:
        lowered = [t.strip().lower() for t in all_known_tasks]
        if key in lowered:
            idx = lowered.index(key)
            return OVERFLOW_PALETTE[idx % len(OVERFLOW_PALETTE)]

    # Deterministic hash fallback — same name → same color, always.
    return OVERFLOW_PALETTE[abs(hash(key)) % len(OVERFLOW_PALETTE)]


def get_expense_color(cat_name: str) -> str:
    """
    Returns a consistent color for an expense category name.
    Unknown categories fall back to the overflow palette via hash.
    """
    key = str(cat_name).strip().lower()

    if key in EXPENSE_COLORS:
        return EXPENSE_COLORS[key]

    return OVERFLOW_PALETTE[abs(hash(key)) % len(OVERFLOW_PALETTE)]


def get_unified_color(name: str, all_known_tasks: list = None) -> str:
    """
    Single entry-point used by the dashboard so focus bars and expense bars
    share exactly the same hues.

    Checks EXPENSE_COLORS first (covers category names like 'food'),
    then falls through to get_task_color for focus task names.
    """
    key = str(name).strip().lower()

    if key in EXPENSE_COLORS:
        return EXPENSE_COLORS[key]

    return get_task_color(name, all_known_tasks)