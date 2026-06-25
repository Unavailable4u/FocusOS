import flet as ft
import asyncio
import sys
import os

# Secure runtime environment pathing parameters
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

from modules.pomodoro.pomodoro import build_pomodoro
import modules.pomodoro.pomodoro as pomodoro_module
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
    _SIDEBAR_FALLBACK = "rgba(17,21,29,0.90)"
    try:
        _glass      = get_active_glass_theme()
        _card_bg    = (_glass.get("card_bg", _SIDEBAR_FALLBACK)
                       if isinstance(_glass, dict) else _SIDEBAR_FALLBACK)
        _sidebar_bg = _set_alpha(_card_bg, 0.90)
    except Exception:
        _sidebar_bg = _SIDEBAR_FALLBACK

    # ── Pomodoro toggle ref ───────────────────────────────────────────────────
    _pomodoro_toggle = {"fn": None}

    # ── Navigation core ───────────────────────────────────────────────────────
    def _navigate_to(index: int):
        """Build and display the page for *index*; update the rail highlight."""
        try:
            if index == 0:
                # Build the dashboard layout but do NOT let it self-paint yet.
                layout = build_dashboard(page)
                content_area.content = layout
                # Mount into the live page tree first.
                content_area.update()
                # Now that widgets are mounted, trigger the first paint.
                if hasattr(layout, "refresh"):
                    layout.refresh()
                _pomodoro_toggle["fn"] = None
                # Return early — content_area is already updated above.
                return

            elif index == 1:
                layout, toggle_fn = build_pomodoro(page)
                content_area.content = layout
                _pomodoro_toggle["fn"] = toggle_fn
            elif index == 2:
                content_area.content = build_tasks(page, on_focus_task=switch_to_pomodoro_with_task)
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

    # ── Task → Pomodoro deep link (P12-T1) ──────────────────────────────────
    def switch_to_pomodoro_with_task(task_title: str):
        """
        Called by the "Focus on this" button on a task tile (modules/tasks.py).
        Stashes *task_title* on the Pomodoro module's session dict so that the
        next build_pomodoro() call pre-selects it in task_dropdown, then
        switches to the Pomodoro tab via the same _navigate_to() path the
        sidebar rail itself uses — this keeps the spacebar-toggle wiring
        (_pomodoro_toggle["fn"]) and the existing error handling intact
        instead of duplicating that logic here.

        Reads/writes pomodoro_module._global_timer_session as a module
        attribute (not a name imported directly from the module) so this
        always sees the live dict even if build_pomodoro() hasn't run yet
        this session — `from modules.pomodoro.pomodoro import
        _global_timer_session` would instead capture whatever value that
        name held at import time (typically None, before the first
        build_pomodoro() call), and keep pointing at that stale value
        forever, even after build_pomodoro() replaces it with the real dict.
        """
        if pomodoro_module._global_timer_session is None:
            # Mirrors the default shape build_pomodoro() itself creates on
            # first run — needed here only so there's a dict to stash the
            # pending selection into before build_pomodoro() has run once.
            pomodoro_module._global_timer_session = {
                "timer_running": False,
                "current_mode": "Focus",
                "total_focus_remaining": 25 * 60,
                "current_segment_elapsed": 0,
                "break_time_remaining": 0,
                "completed_sprints": 0,
                "active_view": "Bars",
                "active_theme": "Glass Cyan",
                "selected_task": "General Study",
                "live_timer_text": None,
                "live_progress_bar": None,
                "sound_enabled": False,
                "sound_src": "None",
                "pending_task_selection": None,
            }
        pomodoro_module._global_timer_session["pending_task_selection"] = task_title

        sidebar_rail.selected_index = 1
        sidebar_rail.update()
        _navigate_to(1)

    # ── Navigation handler (rail on_change) ───────────────────────────────────
    def nav_change(e):
        _navigate_to(e.control.selected_index)

    # ── Keyboard shortcuts ────────────────────────────────────────────────────
    def on_keyboard_event(e: ft.KeyboardEvent):
        key   = e.key
        ctrl  = e.ctrl
        shift = e.shift
        alt   = e.alt

        # Ignore modified Space presses — only bare Space.
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
            content_area.content = build_tasks(page, initial_query=query, on_focus_task=switch_to_pomodoro_with_task)
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
    sidebar_rail = ft.NavigationRail(
        selected_index=0,
        label_type=ft.NavigationRailLabelType.ALL,
        min_width=100,
        bgcolor=_sidebar_bg,
        height=420,
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
    sidebar_column = ft.Container(
        content=ft.Column(
            [sidebar_search, sidebar_rail, ft.Container(expand=True), sidebar_footer],
            spacing=0,
            expand=True,
        ),
        bgcolor=_sidebar_bg,
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
        bgcolor=None,
        expand=True,
    )

    # Wire up the wallpaper system: this frame is the background target
    register_wallpaper_container(main_layout_frame)

    # page.add MUST come before any content_area.update() calls — the widget
    # tree must be mounted first or updates are silently dropped.
    page.add(main_layout_frame)

    # ── Floating mini-timer overlay (P12-T3) ─────────────────────────────────
    # Build the pill widget. bottom/right positioning only works inside a
    # ft.Stack, so we wrap the pill in an expand=True Stack and append that
    # to page.overlay AFTER all other overlay items (audio, pickers, etc.)
    # are added by the modules themselves — this keeps them unaffected.
    mini_timer_text = ft.Text(
        "",
        size=13,
        color="#00FFFF",
        weight=ft.FontWeight.W_600,
        font_family="Courier New",
    )
    mini_timer_pill = ft.Container(
        content=mini_timer_text,
        bgcolor="rgba(17,21,29,0.88)",
        border_radius=20,
        padding=ft.Padding(16, 8, 16, 8),
        border=ft.Border(
            ft.BorderSide(1, "rgba(0,255,255,0.3)"),
            ft.BorderSide(1, "rgba(0,255,255,0.3)"),
            ft.BorderSide(1, "rgba(0,255,255,0.3)"),
            ft.BorderSide(1, "rgba(0,255,255,0.3)"),
        ),
        visible=False,
        bottom=16,
        right=16,
    )
    mini_timer_stack = ft.Stack(
        [mini_timer_pill],
        expand=True,
    )
    page.overlay.append(mini_timer_stack)

    def refresh_mini_timer():
        from modules.pomodoro.pomodoro import get_mini_timer_text
        text, visible = get_mini_timer_text()
        mini_timer_text.value = text
        mini_timer_pill.visible = visible
        try:
            mini_timer_pill.update()
        except Exception:
            pass

    async def _poll_mini_timer():
        while True:
            await asyncio.sleep(1)
            refresh_mini_timer()

    page.run_task(_poll_mini_timer)
    # ── End mini-timer overlay ────────────────────────────────────────────────

    # ── Post-mount startup ────────────────────────────────────────────────────
    def _launch():
        """
        Called by show_onboarding_if_needed once the wizard is done (or
        immediately on repeat launches when onboarding is already complete).

        Everything that touches content_area lives here so it only runs
        AFTER page.add() has mounted the widget tree.
        """
        # Load the dashboard into the now-mounted content_area.
        # _navigate_to(0) handles: build → mount → paint, in that order.
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