import flet as ft
import sys
import os

# Secure runtime environment pathing parameters 
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

# Restore imports for all your real page layout modules
from modules.pomodoro.pomodoro import build_pomodoro
from modules.tasks import build_tasks
from modules.expenses import build_expenses
from modules.dashboard import build_dashboard
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
        # UPDATED: Replaced placeholder text with your new dynamic performance metrics overview page
            content_area.content = build_dashboard(page)
        elif index == 1:
            content_area.content = build_pomodoro(page)
        elif index == 2:
            # RESTORED: Pointing seamlessly to your original layout logic from tasks.py
            content_area.content = build_tasks(page)
        elif index == 3:
            # RESTORED: Pointing seamlessly to your original layout logic from expenses.py
            content_area.content = build_expenses(page)
        
        content_area.update()

    # Default focus is strictly set to index 0 (Dashboard Overview) on launch
    sidebar_rail = ft.NavigationRail(
        selected_index=0,  
        label_type=ft.NavigationRailLabelType.ALL,
        min_width=100,
        bgcolor="#11151D",
        destinations=[
            ft.NavigationRailDestination(icon=ft.Icons.DASHBOARD_ROUNDED, label="Dashboard"),
            ft.NavigationRailDestination(icon=ft.Icons.SHIELD_ROUNDED, label="Pomodoro"),
            ft.NavigationRailDestination(icon=ft.Icons.ASSIGNMENT_ROUNDED, label="Tasks"),
            ft.NavigationRailDestination(icon=ft.Icons.ACCOUNT_BALANCE_WALLET_ROUNDED, label="Expenses"),
        ],
        on_change=nav_change
    )

    # Default initial content area load state mapping configuration (Overview)
    content_area.content = build_dashboard(page)

    main_layout_frame = ft.Container(
        content=ft.Row([
            sidebar_rail,
            ft.VerticalDivider(width=1, color="rgba(255,255,255,0.05)"),
            content_area
        ], expand=True),
        bgcolor="#0B0E14",
        expand=True
    )

    page.add(main_layout_frame)

if __name__ == "__main__":
    ft.app(target=main)