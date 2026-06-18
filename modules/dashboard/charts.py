import flet as ft
from modules.color_palette import get_unified_color
from modules.glass_theme import create_glass_card, get_active_glass_theme


def _uniform_border():
    """Returns a 4-side 1px faint border — used on inner sub-containers."""
    s = ft.BorderSide(1, "rgba(255,255,255,0.05)")
    return ft.Border(s, s, s, s)


def create_stat_card(title, value, subtitle, color):
    content = ft.Column(
        [
            ft.Row(
                [
                    ft.Container(width=4, height=14, bgcolor=color, border_radius=2),
                    ft.Text(title, size=11, color="#8E9AA6", weight=ft.FontWeight.W_600),
                ],
                spacing=6,
            ),
            ft.Container(height=1),
            ft.Text(value, size=24, weight=ft.FontWeight.BOLD, color=color),
            ft.Text(subtitle, size=10, color="grey600"),
        ],
        spacing=2,
        alignment=ft.MainAxisAlignment.CENTER,
    )
    return create_glass_card(content, theme_name=None, expand=True)


def build_proportional_share_panel(
    title,
    allocation_dict,
    is_currency=False,
    currency_symbol="৳",
):
    segments = []
    legend_items = []
    total_volume = sum(allocation_dict.values()) if allocation_dict else 0.0

    sorted_items = sorted(allocation_dict.items(), key=lambda x: str(x[0]).strip().lower())

    for name, val in sorted_items:
        share     = (val / total_volume) if total_volume > 0 else 0.0
        seg_color = get_unified_color(name)

        if val > 0:
            tooltip_str = (
                f"{name}: {currency_symbol}{val:,.2f}"
                if is_currency
                else f"{name}: {int(val)}m"
            )
            legend_str = (
                f"{name} ({currency_symbol}{val:,.0f})"
                if is_currency
                else f"{name} ({int(share * 100)}%)"
            )

            segments.append(
                ft.Container(
                    expand=max(1, int(share * 100)),
                    height=18,
                    bgcolor=seg_color,
                    tooltip=tooltip_str,
                )
            )
            legend_items.append(
                ft.Row(
                    [
                        ft.Container(width=8, height=8, bgcolor=seg_color, border_radius=2),
                        ft.Text(legend_str, size=11, color="#8E9AA6"),
                    ],
                    spacing=6,
                )
            )

    has_data   = total_volume > 0 and len(segments) > 0
    display_row = (
        ft.Row(controls=segments, spacing=2)
        if has_data
        else ft.Row([ft.Container(expand=True, height=18, bgcolor="rgba(255,255,255,0.02)")])
    )

    content = ft.Column(
        [
            ft.Text(title, size=13, weight=ft.FontWeight.W_600, color="#FFFFFF"),
            ft.Divider(height=10, color="rgba(255,255,255,0.05)"),
            ft.Container(height=4),
            ft.Container(
                content=display_row,
                border_radius=6,
                clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
            ),
            ft.Container(height=8),
            ft.Container(
                content=ft.Column(
                    controls=[
                        ft.Row(
                            controls=(
                                legend_items
                                if legend_items
                                else [
                                    ft.Text(
                                        "No records tracked on this date.",
                                        size=11,
                                        color="grey600",
                                        italic=True,
                                    )
                                ]
                            ),
                            wrap=True,
                            spacing=12,
                            run_spacing=8,
                        )
                    ],
                    scroll=ft.ScrollMode.ADAPTIVE,
                ),
                alignment=ft.Alignment(-1, -1),
                expand=True,
                height=110,
            ),
        ]
    )
    return create_glass_card(content, theme_name=None, expand=True, height=220)


def build_upcoming_goal_pie_panel():
    content = ft.Column(
        [
            ft.Text(
                "Target Objectives & Sprints Goal Pie Engine",
                size=13,
                weight=ft.FontWeight.W_600,
                color="#FFFFFF",
            ),
            ft.Divider(height=10, color="rgba(255,255,255,0.05)"),
            ft.Container(
                content=ft.Column(
                    [
                        ft.Icon(ft.Icons.PIE_CHART_ROUNDED, size=44, color="#45A29E"),
                        ft.Text(
                            "Goals Visualization Suite (Coming Soon)",
                            size=12,
                            color="grey600",
                            weight=ft.FontWeight.W_500,
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                expand=True,
                alignment=ft.Alignment(0, 0),
            ),
        ]
    )
    card = create_glass_card(content, theme_name=None, expand=True, height=220)
    card.visible = False
    return card