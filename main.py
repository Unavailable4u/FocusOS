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
from modules.glass_theme import register_wallpaper_container, update_background_wallpaper, get_active_glass_theme

import data_manager as dm


def main(page: ft.Page):
    # Bootstrap data.json (creates it with the default goals shape and runs
    # the legacy-budget migration) before anything else touches the data layer.
    dm.initialize_db()

    page.title = "FocusOS - Advanced Productivity Dashboard"
    page.theme_mode = ft.ThemeMode.DARK
    page.window.width     = 1280
    page.window.height    = 800
    page.window.resizable = True

    content_area = ft.Container(expand=True, padding=15)

    def nav_change(e):
        index = e.control.selected_index
        if index == 0:
            content_area.content = build_dashboard(page)
        elif index == 1:
            content_area.content = build_pomodoro(page)
        elif index == 2:
            content_area.content = build_tasks(page)
        elif index == 3:
            content_area.content = build_expenses(page)
        elif index == 4:
            content_area.content = build_journal(page)
        elif index == 5:
            content_area.content = build_settings(page)
        content_area.update()

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

    # Sidebar footer: pin button sits at the very bottom of the sidebar
    sidebar_footer = ft.Container(
        content=pin_btn,
        alignment=ft.alignment.Alignment(0, 0),
        padding=ft.Padding(0, 0, 0, 8),
    )

    # ── Global search ──────────────────────────────────────────────────────────
    # Searches task titles first, then expense titles, and jumps to whichever
    # page has a match, pre-filling that page's own local search field.
    global_search_feedback = ft.Text("", size=10, color="#FF4B4B", visible=False)

    def global_search_submit(e):
        query = (global_search_field.value or "").strip()
        global_search_feedback.visible = False
        if not query:
            return
        needle = query.lower()

        try:
            tasks_data = dm.load_data()
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
            expense_data = load_expense_data()
            expense_titles = [exp.get("title", "") for exp in expense_data.get("expenses", [])]
        except Exception:
            expense_titles = []

        if any(needle in title.lower() for title in expense_titles):
            sidebar_rail.selected_index = 3
            content_area.content = build_expenses(page, initial_query=query)
            content_area.update()
            page.update()
            return

        global_search_feedback.value = "No matches found."
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

    # ── Glass sidebar colour ──────────────────────────────────────────────────
    # get_active_glass_theme() returns {"card_bg": "rgba(r,g,b,a)", "border": ...}.
    # We reuse the card_bg RGB channels but bump opacity to ~0.65 so the
    # sidebar reads as a distinct frosted panel rather than fully see-through.
    # _parse_rgba / _set_alpha live in glass_theme — import them for reuse.
    from modules.glass_theme import _parse_rgba, _set_alpha
    _SIDEBAR_FALLBACK = "rgba(17,21,29,0.65)"
    try:
        _glass      = get_active_glass_theme()
        _card_bg    = _glass.get("card_bg", _SIDEBAR_FALLBACK) if isinstance(_glass, dict) else _SIDEBAR_FALLBACK
        # Clamp sidebar opacity to 0.65 so the wallpaper shows through subtly
        _sidebar_bg = _set_alpha(_card_bg, 0.65)
    except Exception:
        _sidebar_bg = _SIDEBAR_FALLBACK

    sidebar_rail = ft.NavigationRail(
        selected_index=0,
        label_type=ft.NavigationRailLabelType.ALL,
        min_width=100,
        bgcolor=_sidebar_bg,
        expand=True,
        destinations=[
            ft.NavigationRailDestination(icon=ft.Icons.DASHBOARD_ROUNDED,              label="Dashboard"),
            ft.NavigationRailDestination(icon=ft.Icons.SHIELD_ROUNDED,                 label="Pomodoro"),
            ft.NavigationRailDestination(icon=ft.Icons.ASSIGNMENT_ROUNDED,             label="Tasks"),
            ft.NavigationRailDestination(icon=ft.Icons.ACCOUNT_BALANCE_WALLET_ROUNDED, label="Expenses"),
            ft.NavigationRailDestination(icon=ft.Icons.MENU_BOOK_ROUNDED,              label="Journal"),
            ft.NavigationRailDestination(icon=ft.Icons.SETTINGS_ROUNDED,               label="Settings"),
        ],
        on_change=nav_change,
    )

    # Sidebar column: search up top, nav rail expands to fill, pin button pinned at the bottom
    sidebar_column = ft.Container(
        content=ft.Column(
            [sidebar_search, sidebar_rail, ft.Container(expand=True), sidebar_footer],
            spacing=0,
            expand=True,
        ),
        bgcolor="#11151D",
        width=100,
    )

    # Load Dashboard immediately on startup
    content_area.content = build_dashboard(page)

    main_layout_frame = ft.Container(
        content=ft.Row([
            sidebar_column,
            ft.VerticalDivider(width=1, color="rgba(255,255,255,0.05)"),
            content_area,
        ], expand=True),
        bgcolor=None,   # wallpaper DecorationImage is the visual background
        expand=True,
    )

    # Wire up the wallpaper system: this frame is the background target
    register_wallpaper_container(main_layout_frame)

    page.add(main_layout_frame)

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


if __name__ == "__main__":
    ft.run(main)