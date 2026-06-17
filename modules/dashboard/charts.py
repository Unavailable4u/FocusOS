import flet as ft
from modules.color_palette import get_unified_color

def create_stat_card(title, value, subtitle, color):
    return ft.Container(
        content=ft.Column([
            ft.Row([
                ft.Container(width=4, height=14, bgcolor=color, border_radius=2),
                ft.Text(title, size=11, color="#8E9AA6", weight=ft.FontWeight.W_600)
            ], spacing=6),
            ft.Container(height=1),
            ft.Text(value, size=24, weight=ft.FontWeight.BOLD, color=color),
            ft.Text(subtitle, size=10, color="grey600")
        ], spacing=2, alignment=ft.MainAxisAlignment.CENTER),
        bgcolor="#11151D", padding=14, border_radius=8, expand=True,
        border=ft.Border(ft.BorderSide(1, "rgba(255,255,255,0.05)"), ft.BorderSide(1, "rgba(255,255,255,0.05)"), ft.BorderSide(1, "rgba(255,255,255,0.05)"), ft.BorderSide(1, "rgba(255,255,255,0.05)"))
    )

def build_proportional_share_panel(title, allocation_dict, is_currency=False):
    segments = []
    legend_items = []
    total_volume = sum(allocation_dict.values()) if allocation_dict else 0.0
    
    # FIXED: Uniform lower-case case-insensitive category matching array sequence
    sorted_items = sorted(allocation_dict.items(), key=lambda x: str(x[0]).strip().lower())

    for name, val in sorted_items:
        # Prevent division-by-zero errors if total volume on this targeted date is 0
        share = (val / total_volume) if total_volume > 0 else 0.0
        seg_color = get_unified_color(name)
        
        if val > 0:
            tooltip_str = f"{name}: ৳{val:,.2f}" if is_currency else f"{name}: {int(val)}m"
            legend_str = f"{name} (৳{val:,.0f})" if is_currency else f"{name} ({int(share*100)}%)"
            
            segments.append(ft.Container(expand=max(1, int(share*100)), height=18, bgcolor=seg_color, tooltip=tooltip_str))
            legend_items.append(
                ft.Row([
                    ft.Container(width=8, height=8, bgcolor=seg_color, border_radius=2),
                    ft.Text(legend_str, size=11, color="#8E9AA6")
                ], spacing=6)
            )

    # Fallback placeholder view row if no record tracking data exists for this specific calendar date slot
    has_data = total_volume > 0 and len(segments) > 0
    display_row = ft.Row(controls=segments, spacing=2) if has_data else ft.Row([ft.Container(expand=True, height=18, bgcolor="rgba(255,255,255,0.02)")])

    return ft.Container(
        content=ft.Column([
            ft.Text(title, size=13, weight=ft.FontWeight.W_600, color="#FFFFFF"),
            ft.Divider(height=10, color="rgba(255,255,255,0.05)"),
            ft.Container(height=4),
            ft.Container(content=display_row, border_radius=6, clip_behavior=ft.ClipBehavior.ANTI_ALIAS),
            ft.Container(height=8),
            ft.Container(
                content=ft.Column(
                    controls=[
                        ft.Row(
                            controls=legend_items if legend_items else [ft.Text("No records tracked on this date.", size=11, color="grey600", italic=True)],
                            wrap=True,
                            spacing=12,
                            run_spacing=8
                        )
                    ],
                    scroll=ft.ScrollMode.ADAPTIVE
                ),
                alignment=ft.Alignment(-1, -1),
                expand=True,
                height=110  
            )
        ]),
        bgcolor="#151A22", padding=16, border_radius=10, expand=True, height=220, 
        border=ft.Border(ft.BorderSide(1, "rgba(255,255,255,0.05)"), ft.BorderSide(1, "rgba(255,255,255,0.05)"), ft.BorderSide(1, "rgba(255,255,255,0.05)"), ft.BorderSide(1, "rgba(255,255,255,0.05)"))
    )

def build_upcoming_goal_pie_panel():
    return ft.Container(
        content=ft.Column([
            ft.Text("Target Objectives & Sprints Goal Pie Engine", size=13, weight=ft.FontWeight.W_600, color="#FFFFFF"),
            ft.Divider(height=10, color="rgba(255,255,255,0.05)"),
            ft.Container(
                content=ft.Column([
                    ft.Icon(ft.Icons.PIE_CHART_ROUNDED, size=44, color="#45A29E"),
                    ft.Text("Goals Visualization Suite (Coming Soon)", size=12, color="grey600", weight=ft.FontWeight.W_500)
                ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                expand=True, 
                alignment=ft.Alignment(0, 0)
            )
        ]),
        bgcolor="#151A22", padding=16, border_radius=10, expand=True, height=220, visible=False,
        border=ft.Border(ft.BorderSide(1, "rgba(255,255,255,0.05)"), ft.BorderSide(1, "rgba(255,255,255,0.05)"), ft.BorderSide(1, "rgba(255,255,255,0.05)"), ft.BorderSide(1, "rgba(255,255,255,0.05)"))
    )