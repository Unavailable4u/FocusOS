import flet as ft
import flet_charts as fch
import math

def generate_precision_radial_clock(today_data, color_map):
    """Computes exact trigonometric coordinates to render your minute-precision contextual dial."""
    clock_sections = []
    
    # Calculate total daily tracking minutes to check if the entire day is completely empty
    grand_daily_total = 0
    for hour in range(24):
        hour_dict = today_data.get(str(hour), {})
        if isinstance(hour_dict, dict):
            grand_daily_total += sum(hour_dict.values())

    # If the day is completely empty, render ONE single continuous dark gray ring.
    if grand_daily_total == 0:
        clock_sections.append(
            fch.PieChartSection(
                value=1440, 
                color="#1E293B",  # Solid dark slate gray baseline
                radius=15,
                title=""
            )
        )
    else:
        # If there is data, build the precise segment slices dynamically per hour
        for hour in range(24):
            hour_dict = today_data.get(str(hour), {})
            if not isinstance(hour_dict, dict): 
                hour_dict = {}
            
            total_hour_focused = sum(hour_dict.values())

            if total_hour_focused == 0:
                clock_sections.append(fch.PieChartSection(value=60, color="#1E293B", radius=15, title=""))
            else:
                accumulated_time = 0
                # STACKED LOGIC: Iterate over each individual logged task inside this hour slot
                for task_name, task_mins in hour_dict.items():
                    if task_mins > 0:
                        section_color = color_map.get(task_name, "#00FFFF")
                        # Add the proportional sub-slice matching this specific task's tracked duration
                        clock_sections.append(
                            fch.PieChartSection(
                                value=task_mins, 
                                color=section_color, 
                                radius=16, 
                                title=""
                            )
                        )
                        accumulated_time += task_mins
                
                # Fill up the remainder of the 60-minute segment with the background plate token if incomplete
                if accumulated_time < 60:
                    clock_sections.append(fch.PieChartSection(value=60 - accumulated_time, color="#1E293B", radius=15, title=""))

    stack_controls = [
        fch.PieChart(
            sections=clock_sections,
            sections_space=1.0,
            center_space_radius=95, 
            expand=True
        )
    ]

    # Render clean hour labels around the perimeter
    for idx in range(12):
        hour_val = (idx + 1) * 2
        angle_radians = (hour_val * 15) * (math.pi / 180)
        pos_x = math.sin(angle_radians) * 1.28
        pos_y = -math.cos(angle_radians) * 1.28
        display_label = f"{hour_val:02d}h" if hour_val != 24 else "24h"

        stack_controls.append(
            ft.Container(
                content=ft.Text(display_label, size=9, color="#FFFFFF", weight=ft.FontWeight.BOLD),
                alignment=ft.alignment.Alignment(pos_x, pos_y)
            )
        )

    stack_controls.append(
        ft.Container(
            content=ft.Column([
                ft.Icon(ft.Icons.ACCESS_TIME_ROUNDED, color="#00FFFF", size=24),
                ft.Text("Task Matrix", size=10, color="#FFFFFF", weight=ft.FontWeight.W_600)
            ], spacing=2, alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            alignment=ft.alignment.Alignment(0, 0)
        )
    )

    return ft.Stack(controls=stack_controls, width=220, height=220)