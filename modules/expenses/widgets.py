import flet as ft
from datetime import datetime

# Define the color map used by your expenses module
COLOR_MAP = {
    "Study": "#66FCF1", 
    "Food": "#FF4B4B", 
    "Transport": "#BB86FC", 
    "Other": "#95A5A6"
}

def get_cat_color(cat):
    """Returns the color for a given category."""
    return COLOR_MAP.get(cat, "#45A29E")

def build_daily_trend_graph(filtered_items):
    """
    Builds the trend graph widget based on filtered expense items.
    """
    day_totals = {}
    for idx, exp in filtered_items:
        date_str = exp.get("date", datetime.now().strftime("%Y-%m-%d"))
        day_totals[date_str] = day_totals.get(date_str, 0.0) + exp.get("amount", 0.0)
        
    columns = []
    # Sort dates to ensure the graph displays correctly
    for day_stamp in sorted(day_totals.keys()):
        total_amt = day_totals[day_stamp]
        try:
            label = datetime.strptime(day_stamp, "%Y-%m-%d").strftime("%d")
        except ValueError:
            label = day_stamp[-2:]

        columns.append(
            ft.Column([
                ft.Container(
                    width=28, height=60, bgcolor="#FFB74D", border_radius=3,
                    tooltip=f"Date: {day_stamp}\nTotal: ৳{int(total_amt)}"
                ),
                ft.Text(label, size=9, color="#8E9AA6")
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER)
        )
        
    return ft.Container(
        content=ft.Row(
            controls=columns if columns else [ft.Text("No data to plot", color="grey")], 
            scroll=ft.ScrollMode.ADAPTIVE
        ),
        padding=10
    )