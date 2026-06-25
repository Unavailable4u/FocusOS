import flet as ft
import sys
import os

# Secure runtime environment pathing parameters
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

from modules.pomodoro.pomodoro import build_pomodoro
from modules.tasks import build_tasks
from modules.expenses import build_expenses
from modules.expenses.engine import load_expense_data
from modules.dashboard import build_dashboard
from modules.journal import build_journal
from modules.settings import build_settings
from modules.glass_theme import (
    register_wallpaper_container,
    update_background_wallpaper,
    get_active_glass_theme,
    _parse_rgba,
    _set_alpha,
)

import data_manager as dm
from modules.onboarding import show_onboarding_if_needed


def main(page: ft.Page):
    import traceback
    page.on_error = lambda e: print(f"PAGE ERROR: {e.data}")

    # Bootstrap data.json (creates it with the default goals shape and runs
    # the legacy-budget migration) before anything else touches the data layer.
    try:
        dm.initialize_db()
    except Exception:
        print("CRASH in initialize_db:")
        traceback.print_exc()
        return

    page.title            = "FocusOS - Advanced Productivity Dashboard"
    page.theme_mode       = ft.ThemeMode.DARK
    page.window.width     = 1280
    page.window.height    = 800
    page.window.resizable = True

    content_area = ft.Container(expand=True, padding=15)

    # ── Glass sidebar colour ──────────────────────────────────────────────────
    # Resolved once at startup; both the NavigationRail AND the sidebar
    # Container use the same value so there is no colour seam between them.
    _SIDEBAR_FALLBACK = "rgba(17,21,29,0.90)"
    try:
        _glass      = get_active_glass_theme()
        _card_bg    = (_glass.get("card_bg", _SIDEBAR_FALLBACK)
                       if isinstance(_glass, dict) else _SIDEBAR_FALLBACK)
        _sidebar_bg = _set_alpha(_card_bg, 0.90)
    except Exception:
        _sidebar_bg = _SIDEBAR_FALLBACK

    # ── Pomodoro toggle ref ───────────────────────────────────────────────────
    # build_pomodoro returns (layout, toggle_timer_fn).  We keep the fn here
    # so the keyboard handler can call it when Space is pressed on tab 1.
    _pomodoro_toggle = {"fn": None}

    # ── Navigation core ───────────────────────────────────────────────────────
    def _navigate_to(index: int):
        """Build and display the page for *index*; update the rail highlight."""
        try:
            if index == 0:
                content_area.content = build_dashboard(page)
                _pomodoro_toggle["fn"] = None
            elif index == 1:
                layout, toggle_fn = build_pomodoro(page)
                content_area.content = layout
                _pomodoro_toggle["fn"] = toggle_fn
            elif index == 2:
                content_area.content = build_tasks(page)
                _pomodoro_toggle["fn"] = None
            elif index == 3:
                content_area.content = build_expenses(page)
                _pomodoro_toggle["fn"] = None
            elif index == 4:
                content_area.content = build_journal(page)
                _pomodoro_toggle["fn"] = None
            elif index == 5:
                try:
                    content_area.content = build_settings(page)
                    _pomodoro_toggle["fn"] = None
                except Exception:
                    err = traceback.format_exc()
                    print(">>> EXCEPTION in settings build:")
                    print(err)
                    content_area.content = ft.Text(
                        err, color="#FF4B4B", size=11, selectable=True
                    )
            content_area.update()
        except Exception as exc:
            # Surface any build error as a visible message instead of silent fail
            content_area.content = ft.Text(
                f"Error loading page {index}:\n{exc}",
                color="#FF4B4B", size=13,
            )
            content_area.update()

    # ── Navigation handler (rail on_change) ───────────────────────────────────
    def nav_change(e):
        _navigate_to(e.control.selected_index)

    # ── Keyboard shortcuts ────────────────────────────────────────────────────
    # Ctrl+1…6  → switch to tab 0…5
    # Ctrl+N    → jump to Tasks (2); if already there, jump to Expenses (3)
    # Space     → toggle Pomodoro timer (only when Pomodoro tab is active)
    def on_keyboard_event(e: ft.KeyboardEvent):
        key   = e.key
        ctrl  = e.ctrl
        shift = e.shift
        alt   = e.alt

        # Ignore modified Space presses (Ctrl+Space etc.) — only bare Space.
        if key == " " and not ctrl and not shift and not alt:
            fn = _pomodoro_toggle.get("fn")
            if fn is not None:
                fn()
            return

        if not ctrl or shift or alt:
            return

        # Ctrl+1…6 → nav tabs 0…5
        if key in ("1", "2", "3", "4", "5", "6"):
            target = int(key) - 1
            sidebar_rail.selected_index = target
            sidebar_rail.update()
            _navigate_to(target)
            return

        # Ctrl+N → Tasks, or Expenses if already on Tasks
        if key.upper() == "N":
            current = sidebar_rail.selected_index
            target  = 3 if current == 2 else 2
            sidebar_rail.selected_index = target
            sidebar_rail.update()
            _navigate_to(target)
            return

    page.on_keyboard_event = on_keyboard_event

    # ── Always-on-top pin button ──────────────────────────────────────────────
    _pinned = {"value": False}

    def toggle_pin(e):
        _pinned["value"] = not _pinned["value"]
        page.window.always_on_top = _pinned["value"]
        pin_btn.icon       = (ft.Icons.PUSH_PIN_ROUNDED
                              if _pinned["value"]
                              else ft.Icons.PUSH_PIN_OUTLINED)
        pin_btn.icon_color = "#00FFFF" if _pinned["value"] else "grey600"
        pin_btn.tooltip    = ("Unpin window" if _pinned["value"]
                              else "Pin window on top")
        page.update()

    pin_btn = ft.IconButton(
        icon=ft.Icons.PUSH_PIN_OUTLINED,
        icon_color="grey600",
        icon_size=18,
        tooltip="Pin window on top",
        on_click=toggle_pin,
    )

    sidebar_footer = ft.Container(
        content=pin_btn,
        alignment=ft.alignment.Alignment(0, 0),
        padding=ft.Padding(0, 0, 0, 8),
    )

    # ── Global search ─────────────────────────────────────────────────────────
    global_search_feedback = ft.Text("", size=10, color="#FF4B4B", visible=False)

    def global_search_submit(e):
        query = (global_search_field.value or "").strip()
        global_search_feedback.visible = False
        if not query:
            return
        needle = query.lower()

        try:
            tasks_data  = dm.load_data()
            task_titles = [t.get("title", "") for t in tasks_data.get("tasks", [])]
        except Exception:
            task_titles = []

        if any(needle in title.lower() for title in task_titles):
            sidebar_rail.selected_index = 2
            content_area.content = build_tasks(page, initial_query=query)
            content_area.update()
            page.update()
            return

        try:
            expense_data   = load_expense_data()
            expense_titles = [exp.get("title", "")
                              for exp in expense_data.get("expenses", [])]
        except Exception:
            expense_titles = []

        if any(needle in title.lower() for title in expense_titles):
            sidebar_rail.selected_index = 3
            content_area.content = build_expenses(page, initial_query=query)
            content_area.update()
            page.update()
            return

        global_search_feedback.value   = "No matches found."
        global_search_feedback.visible = True
        page.update()

    global_search_field = ft.TextField(
        label="Search everything...",
        label_style=ft.TextStyle(color="#45A29E", size=10),
        border_color="#243142",
        prefix_icon=ft.Icons.TRAVEL_EXPLORE_ROUNDED,
        text_size=11,
        content_padding=ft.Padding(8, 4, 8, 4),
        on_submit=global_search_submit,
    )

    sidebar_search = ft.Container(
        content=ft.Column([global_search_field, global_search_feedback], spacing=2),
        padding=ft.Padding(8, 10, 8, 6),
    )

    # ── Navigation rail ───────────────────────────────────────────────────────
    # bgcolor matches _sidebar_bg exactly so every destination — including
    # Settings (index 5) — renders on the same background colour.
    sidebar_rail = ft.NavigationRail(
        selected_index=0,
        label_type=ft.NavigationRailLabelType.ALL,
        min_width=100,
        bgcolor=_sidebar_bg,  # ← same value as sidebar_column below
        height=420,           # fixed height: NavigationRail needs a bounded height,
                              # it can't be sized by an expanding parent Column alone
        destinations=[
            ft.NavigationRailDestination(
                icon=ft.Icons.DASHBOARD_ROUNDED,
                label="Dashboard",
            ),
            ft.NavigationRailDestination(
                icon=ft.Icons.SHIELD_ROUNDED,
                label="Pomodoro",
            ),
            ft.NavigationRailDestination(
                icon=ft.Icons.ASSIGNMENT_ROUNDED,
                label="Tasks",
            ),
            ft.NavigationRailDestination(
                icon=ft.Icons.ACCOUNT_BALANCE_WALLET_ROUNDED,
                label="Expenses",
            ),
            ft.NavigationRailDestination(
                icon=ft.Icons.MENU_BOOK_ROUNDED,
                label="Journal",
            ),
            ft.NavigationRailDestination(
                icon=ft.Icons.SETTINGS_ROUNDED,
                label="Settings",
            ),
        ],
        on_change=nav_change,
    )

    # ── Sidebar container ─────────────────────────────────────────────────────
    # bgcolor is intentionally the same as sidebar_rail so there is no
    # visible colour gap around the search box or pin button.
    sidebar_column = ft.Container(
        content=ft.Column(
            [sidebar_search, sidebar_rail, ft.Container(expand=True), sidebar_footer],
            spacing=0,
            expand=True,
        ),
        bgcolor=_sidebar_bg,  # ← unified with the rail colour
        width=100,
    )

    main_layout_frame = ft.Container(
        content=ft.Row(
            [
                sidebar_column,
                ft.VerticalDivider(width=1, color="rgba(255,255,255,0.05)"),
                content_area,
            ],
            expand=True,
        ),
        bgcolor=None,   # wallpaper DecorationImage is the visual background
        expand=True,
    )

    # Wire up the wallpaper system: this frame is the background target
    register_wallpaper_container(main_layout_frame)

    # page.add MUST come before any content_area.update() calls — the widget
    # tree must be mounted first or updates are silently dropped.
    page.add(main_layout_frame)

    # ── Post-mount startup ────────────────────────────────────────────────────
    def _launch():
        """
        Called by show_onboarding_if_needed once the wizard is done (or
        immediately on repeat launches when onboarding is already complete).

        Everything that touches content_area lives here so it only runs
        AFTER page.add() has mounted the widget tree.
        """
        # Load the dashboard into the now-mounted content_area
        _navigate_to(0)

        # Restore a previously-chosen wallpaper, if one was saved
        try:
            settings = dm.get_settings()
        except AttributeError:
            settings = {}
        bg_path = (settings.get("background_image_path")
                   if isinstance(settings, dict)
                   else getattr(settings, "background_image_path", None))
        if bg_path:
            update_background_wallpaper(bg_path)

    # Show the onboarding wizard on first launch; calls _launch when done.
    # On subsequent launches it is a no-op and calls _launch immediately.
    show_onboarding_if_needed(page, on_complete=_launch)


if __name__ == "__main__":
    ft.run(main)