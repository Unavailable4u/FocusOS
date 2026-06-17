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
from modules.dashboard import build_dashboard
from modules.journal import build_journal


def main(page: ft.Page):
    page.title = "FocusOS - Advanced Productivity Dashboard"
    page.theme_mode = ft.ThemeMode.DARK
    page.window_width = 1280
    page.window_height = 800
    page.window_resizable = True

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
        content_area.update()

    # ── Always-on-top pin button ──────────────────────────────────────────────
    _pinned = {"value": False}

    def toggle_pin(e):
        _pinned["value"] = not _pinned["value"]
        page.window_always_on_top = _pinned["value"]
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

    sidebar_rail = ft.NavigationRail(
        selected_index=0,
        label_type=ft.NavigationRailLabelType.ALL,
        min_width=100,
        bgcolor="#11151D",
        expand=True,
        destinations=[
            ft.NavigationRailDestination(icon=ft.Icons.DASHBOARD_ROUNDED,              label="Dashboard"),
            ft.NavigationRailDestination(icon=ft.Icons.SHIELD_ROUNDED,                 label="Pomodoro"),
            ft.NavigationRailDestination(icon=ft.Icons.ASSIGNMENT_ROUNDED,             label="Tasks"),
            ft.NavigationRailDestination(icon=ft.Icons.ACCOUNT_BALANCE_WALLET_ROUNDED, label="Expenses"),
            ft.NavigationRailDestination(icon=ft.Icons.MENU_BOOK_ROUNDED,              label="Journal"),
        ],
        on_change=nav_change,
    )

    # Sidebar column: nav rail expands to fill, pin button pinned at the bottom
    sidebar_column = ft.Container(
        content=ft.Column(
            [sidebar_rail, sidebar_footer],
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
        bgcolor="#0B0E14",
        expand=True,
    )

    page.add(main_layout_frame)


if __name__ == "__main__":
    ft.app(target=main)