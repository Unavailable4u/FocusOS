"""
modules/onboarding.py
---------------------
First-launch onboarding wizard for FocusOS.

Shows a 3-step modal dialog that collects:
  Step 1 — Profile name  (saved to settings["profile_name"])
  Step 2 — Daily focus goal in minutes  (saved to goals["daily_focus_minutes"])
  Step 3 — Monthly expense budget  (saved to goals["monthly_expense_budget"])

Usage in main.py
----------------
    from modules.onboarding import show_onboarding_if_needed

    # Call *after* initialize_db() and *before* building the main layout.
    # Pass a callback that the wizard calls when it completes so main.py
    # can finish wiring up the UI.
    show_onboarding_if_needed(page, on_complete=lambda: _build_main_layout())

The function is a no-op when settings["onboarding_complete"] is already True,
so it is safe to call unconditionally every launch.
"""

from __future__ import annotations

import flet as ft
import data_manager as dm


# ── Palette / style constants (match dashboard dark theme) ───────────────────
_BG        = "#1E2631"
_CARD      = "#141A23"
_ACCENT    = "#00FFFF"
_GREEN     = "#00E676"
_ORANGE    = "#FF9100"
_TEXT      = "#E0E0E0"
_MUTED     = "#607080"
_BORDER    = "rgba(255,255,255,0.10)"
_STEP_CLR  = ["#00FFFF", "#00E676", "#FF9100"]   # per-step accent


def _field(label: str, hint: str, keyboard_type=ft.KeyboardType.TEXT,
           prefix_icon: str | None = None) -> ft.TextField:
    return ft.TextField(
        label=label,
        hint_text=hint,
        keyboard_type=keyboard_type,
        prefix_icon=prefix_icon,
        label_style=ft.TextStyle(color=_MUTED, size=12),
        border_color=_BORDER,
        focused_border_color=_ACCENT,
        text_style=ft.TextStyle(color=_TEXT, size=14),
        content_padding=ft.Padding(12, 10, 12, 10),
        border_radius=8,
        expand=True,
    )


def _step_dot(idx: int, current: int) -> ft.Container:
    active = idx == current
    return ft.Container(
        width=10 if active else 8,
        height=10 if active else 8,
        border_radius=5,
        bgcolor=_STEP_CLR[idx] if active else _MUTED,
        animate=ft.Animation(200, ft.AnimationCurve.EASE_OUT),
    )


def show_onboarding_if_needed(page: ft.Page, on_complete: callable) -> None:
    """
    Opens the onboarding wizard if this is a first launch, otherwise calls
    on_complete immediately so normal startup continues uninterrupted.

    Parameters
    ----------
    page        : ft.Page — the active Flet page.
    on_complete : callable — zero-argument callback invoked when the wizard
                  finishes (either after Step 3 or if the user skips).
    """
    if dm.get_settings().get("onboarding_complete"):
        on_complete()
        return

    _run_wizard(page, on_complete)


# ── Internal wizard implementation ───────────────────────────────────────────

def _run_wizard(page: ft.Page, on_complete: callable) -> None:  # noqa: C901
    TOTAL_STEPS = 3
    state = {"step": 0}

    # ── Input fields ─────────────────────────────────────────────────────────
    name_field = _field(
        "Your name", "e.g. Alex",
        prefix_icon=ft.Icons.PERSON_OUTLINE_ROUNDED,
    )
    focus_field = _field(
        "Daily focus goal (minutes)", "e.g. 120",
        keyboard_type=ft.KeyboardType.NUMBER,
        prefix_icon=ft.Icons.TIMER_OUTLINED,
    )
    budget_field = _field(
        f"Monthly expense budget ({dm.get_currency_symbol()})", "e.g. 5000  (0 = skip)",
        keyboard_type=ft.KeyboardType.NUMBER,
        prefix_icon=ft.Icons.ACCOUNT_BALANCE_WALLET_OUTLINED,
    )

    # ── Step meta ─────────────────────────────────────────────────────────────
    _STEPS = [
        {
            "icon":    ft.Icons.WAVING_HAND_ROUNDED,
            "title":   "Welcome to FocusOS",
            "body":    "Let's personalise your dashboard in three quick steps.\n"
                       "How should we address you?",
            "field":   name_field,
            "tip":     "You can change this any time in Settings.",
        },
        {
            "icon":    ft.Icons.TRACK_CHANGES_ROUNDED,
            "title":   "Set Your Focus Goal",
            "body":    "How many minutes of focused work do you want to hit each day?\n"
                       "The dashboard will track your progress toward this target.",
            "field":   focus_field,
            "tip":     "25–30 min (one Pomodoro) is a great starting point.",
        },
        {
            "icon":    ft.Icons.SAVINGS_OUTLINED,
            "title":   "Monthly Expense Budget",
            "body":    "Set an overall monthly spending cap so FocusOS can alert\n"
                       "you when you're running close to your limit.",
            "field":   budget_field,
            "tip":     "Enter 0 to skip budgeting for now.",
        },
    ]

    # ── Dynamic UI refs ───────────────────────────────────────────────────────
    icon_ref    = ft.Ref[ft.Icon]()
    title_ref   = ft.Ref[ft.Text]()
    body_ref    = ft.Ref[ft.Text]()
    tip_ref     = ft.Ref[ft.Text]()
    field_wrap  = ft.Container(expand=True)        # swapped per step
    dots_row    = ft.Row(spacing=8, alignment=ft.MainAxisAlignment.CENTER)
    btn_next    = ft.Ref[ft.ElevatedButton]()
    btn_back    = ft.Ref[ft.TextButton]()
    btn_skip    = ft.Ref[ft.TextButton]()
    error_text  = ft.Text("", color="#FF4B4B", size=11, visible=False)

    # ── Step renderer ─────────────────────────────────────────────────────────
    def _render_step(step_idx: int) -> None:
        meta = _STEPS[step_idx]
        icon_ref.current.name  = meta["icon"]
        icon_ref.current.color = _STEP_CLR[step_idx]
        title_ref.current.value = meta["title"]
        body_ref.current.value  = meta["body"]
        tip_ref.current.value   = f"💡  {meta['tip']}"
        field_wrap.content      = meta["field"]
        error_text.value        = ""
        error_text.visible      = False

        # Step dots
        dots_row.controls = [_step_dot(i, step_idx) for i in range(TOTAL_STEPS)]

        is_last = step_idx == TOTAL_STEPS - 1
        btn_next.current.text       = "Get Started 🚀" if is_last else "Next →"
        btn_next.current.bgcolor    = _STEP_CLR[step_idx]
        btn_back.current.visible    = step_idx > 0

    def _validate_current() -> str | None:
        """Returns an error string, or None if the current step is valid."""
        step = state["step"]
        if step == 0:
            if not name_field.value or not name_field.value.strip():
                return "Please enter your name to continue."
        elif step == 1:
            val = (focus_field.value or "").strip()
            if not val:
                return "Please enter your daily focus goal."
            try:
                mins = int(val)
                if mins <= 0:
                    return "Goal must be at least 1 minute."
            except ValueError:
                return "Please enter a whole number of minutes."
        elif step == 2:
            val = (budget_field.value or "").strip()
            if val:
                try:
                    float(val)
                except ValueError:
                    return "Please enter a valid number (or 0 to skip)."
        return None

    def _save_and_finish() -> None:
        """Persist all collected values and mark onboarding complete."""
        name = (name_field.value or "").strip()
        if name:
            dm.save_settings({"profile_name": name})

        try:
            focus_mins = int((focus_field.value or "120").strip())
        except ValueError:
            focus_mins = 120
        dm.save_goals({"daily_focus_minutes": max(1, focus_mins)})

        try:
            budget = float((budget_field.value or "0").strip() or "0")
        except ValueError:
            budget = 0.0
        dm.save_goals({"monthly_expense_budget": max(0.0, budget)})

        dm.save_settings({"onboarding_complete": True})

    def _close_dialog() -> None:
        """Close the dialog — compatible with both old and new Flet APIs."""
        try:
            page.close(dlg)          # Flet >= 0.23
        except AttributeError:
            dlg.open = False
            page.update()

    # ── Button handlers ───────────────────────────────────────────────────────
    def on_next(e):
        err = _validate_current()
        if err:
            error_text.value   = err
            error_text.visible = True
            try: error_text.update()
            except Exception: pass
            return

        if state["step"] < TOTAL_STEPS - 1:
            state["step"] += 1
            _render_step(state["step"])
            try: dlg.update()
            except Exception: page.update()
        else:
            _save_and_finish()
            _close_dialog()
            on_complete()

    def on_back(e):
        if state["step"] > 0:
            state["step"] -= 1
            _render_step(state["step"])
            try: dlg.update()
            except Exception: page.update()

    def on_skip(e):
        # Save whatever has been entered so far, mark complete, close.
        _save_and_finish()
        _close_dialog()
        on_complete()

    # ── Dialog construction ───────────────────────────────────────────────────
    dlg = ft.AlertDialog(
        modal=True,
        bgcolor=_CARD,
        shape=ft.RoundedRectangleBorder(radius=16),
        content_padding=ft.Padding(0, 0, 0, 0),
        content=ft.Container(
            width=480,
            padding=ft.Padding(32, 28, 32, 24),
            content=ft.Column(
                [
                    # Icon + dots
                    ft.Row(
                        [
                            ft.Icon(
                                ft.Icons.WAVING_HAND_ROUNDED,
                                ref=icon_ref,
                                color=_ACCENT,
                                size=36,
                            ),
                            ft.Container(expand=True),
                            dots_row,
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                    ft.Container(height=16),
                    ft.Text(
                        "",
                        ref=title_ref,
                        size=20,
                        weight=ft.FontWeight.W_700,
                        color=_TEXT,
                    ),
                    ft.Container(height=6),
                    ft.Text(
                        "",
                        ref=body_ref,
                        size=13,
                        color=_MUTED,
                    ),
                    ft.Container(height=20),
                    field_wrap,
                    ft.Container(height=6),
                    error_text,
                    ft.Container(height=4),
                    ft.Text(
                        "",
                        ref=tip_ref,
                        size=11,
                        color=_MUTED,
                        italic=True,
                    ),
                    ft.Container(height=24),
                    # Action row
                    ft.Row(
                        [
                            ft.TextButton(
                                "Skip setup",
                                ref=btn_skip,
                                style=ft.ButtonStyle(color=_MUTED),
                                on_click=on_skip,
                            ),
                            ft.Container(expand=True),
                            ft.TextButton(
                                "← Back",
                                ref=btn_back,
                                style=ft.ButtonStyle(color=_MUTED),
                                visible=False,
                                on_click=on_back,
                            ),
                            ft.Container(width=8),
                            ft.ElevatedButton(
                                "Next →",
                                ref=btn_next,
                                bgcolor=_ACCENT,
                                color="#000000",
                                style=ft.ButtonStyle(
                                    shape=ft.RoundedRectangleBorder(radius=8),
                                    padding=ft.Padding(20, 12, 20, 12),
                                ),
                                on_click=on_next,
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.START,
                    ),
                ],
                spacing=0,
                tight=True,
            ),
        ),
    )

    # Populate the first step before opening
    _render_step(0)

    # Open dialog — compatible with both old and new Flet APIs
    try:
        page.open(dlg)               # Flet >= 0.23
    except AttributeError:
        page.dialog = dlg
        dlg.open = True
        page.update()