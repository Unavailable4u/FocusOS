import flet as ft
import flet_charts as fch
from datetime import datetime

import data_manager as dm
from modules.color_palette import get_unified_color
from modules.glass_theme import create_glass_card, get_active_glass_theme
from modules.dashboard import engine


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
    """
    Today's daily-focus-goal completion as a donut chart: a cyan "done"
    slice vs. a dark-gray "remaining" slice, with the completion
    percentage centered in the donut hole (flet_charts.PieChart has no
    built-in center label, so the percentage Text is overlaid on top of
    the chart via a Stack, matching the chart's center_space_radius hole).

    Falls back to a short "set a goal" prompt when the user hasn't set
    goals["daily_focus_minutes"] yet (data_manager.get_goals()), since an
    unset goal means there's no meaningful "remaining" to chart.
    """
    goals      = dm.get_goals()
    daily_goal = goals.get("daily_focus_minutes", 0) or 0

    if daily_goal <= 0:
        content = ft.Column(
            [
                ft.Text(
                    "Today's Focus Goal",
                    size=13,
                    weight=ft.FontWeight.W_600,
                    color="#FFFFFF",
                ),
                ft.Divider(height=10, color="rgba(255,255,255,0.05)"),
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Icon(ft.Icons.FLAG_ROUNDED, size=44, color="#45A29E"),
                            ft.Text(
                                "Set a daily goal in Settings",
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
        card.visible = True
        return card

    raw_data     = dm.load_data()
    distribution = raw_data.get("hourly_task_distribution", {})
    today_str    = datetime.now().strftime("%Y-%m-%d")
    done_mins    = engine._day_total_minutes(distribution, today_str)
    pct          = (done_mins / daily_goal) * 100 if daily_goal > 0 else 0

    # Chart slices clamp at the goal — a day that blows past 100% just
    # renders as a full cyan ring; the actual (possibly >100%) percentage
    # still shows in the center label and subtitle.
    chart_done      = min(done_mins, daily_goal)
    chart_remaining = max(0.0, daily_goal - done_mins)

    sections = []
    if chart_done > 0:
        sections.append(fch.PieChartSection(
            value=chart_done, title="", color="#00FFFF", radius=38,
        ))
    if chart_remaining > 0:
        sections.append(fch.PieChartSection(
            value=chart_remaining, title="", color="#243142", radius=38,
        ))
    if not sections:
        sections.append(fch.PieChartSection(value=1, title="", color="#243142", radius=38))

    donut = fch.PieChart(
        sections=sections, sections_space=2,
        center_space_radius=34, height=140, width=140,
    )

    label_color = "#00FFFF" if pct < 100 else "#00E676"
    donut_with_label = ft.Stack(
        [
            ft.Container(content=donut, alignment=ft.Alignment(0, 0)),
            ft.Container(
                content=ft.Text(f"{int(pct)}%", size=20, weight=ft.FontWeight.BOLD, color=label_color),
                alignment=ft.Alignment(0, 0),
            ),
        ],
        height=140,
    )

    if pct >= 100:
        subtitle = f"Goal met — {int(done_mins)}m logged 🎉"
    else:
        subtitle = f"{int(done_mins)}m of {int(daily_goal)}m  ·  {int(daily_goal - done_mins)}m to go"

    legend = ft.Row(
        [
            ft.Row(
                [
                    ft.Container(width=8, height=8, bgcolor="#00FFFF", border_radius=2),
                    ft.Text("Done", size=11, color="#8E9AA6"),
                ],
                spacing=6,
            ),
            ft.Row(
                [
                    ft.Container(width=8, height=8, bgcolor="#243142", border_radius=2),
                    ft.Text("Remaining", size=11, color="#8E9AA6"),
                ],
                spacing=6,
            ),
        ],
        spacing=16,
        alignment=ft.MainAxisAlignment.CENTER,
    )

    content = ft.Column(
        [
            ft.Text(
                "Today's Focus Goal",
                size=13,
                weight=ft.FontWeight.W_600,
                color="#FFFFFF",
            ),
            ft.Divider(height=10, color="rgba(255,255,255,0.05)"),
            ft.Container(height=4),
            ft.Container(content=donut_with_label, alignment=ft.Alignment(0, 0), expand=True),
            ft.Text(subtitle, size=11, color="grey600", text_align=ft.TextAlign.CENTER),
            ft.Container(height=6),
            legend,
        ]
    )

    card = create_glass_card(content, theme_name=None, expand=True, height=220)
    card.visible = True
    return card