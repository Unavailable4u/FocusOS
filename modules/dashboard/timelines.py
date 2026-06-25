import flet as ft
from datetime import datetime, timedelta
from modules.color_palette import get_task_color, get_expense_color

# ---------------------------------------------------------------------------
# Color helpers
# ---------------------------------------------------------------------------

def get_focus_color(task_name: str) -> str:
    if not task_name:
        return "#546E7A"
    color = get_task_color(str(task_name).strip())
    return color if color else "#546E7A"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _fmt_mins(total_mins: float) -> str:
    m = int(total_mins)
    h, rem = divmod(m, 60)
    if h > 0:
        return f"{h}h {rem}m" if rem else f"{h}h"
    return f"{rem}m"


def clean_date_string(raw_date):
    try:
        if isinstance(raw_date, str):
            parts = raw_date.strip().split('-')
            if len(parts) == 3:
                return f"{int(parts[0]):04d}-{int(parts[1]):02d}-{int(parts[2]):02d}"
    except Exception:
        pass
    return str(raw_date).strip()


# ---------------------------------------------------------------------------
# AVG bar builders
# ---------------------------------------------------------------------------

def _build_avg_focus_bar(avg_mins: float, max_hour_total: float) -> ft.Column:
    GRAPH_H = 135
    avg_bar_height = max(6, int((avg_mins / max(max_hour_total, 1)) * GRAPH_H))
    transparent_h = GRAPH_H - avg_bar_height

    avg_label = _fmt_mins(avg_mins)

    avg_bar = ft.Container(
        width=28,
        height=avg_bar_height,
        border=ft.Border(
            ft.BorderSide(1, "#607D8B"),
            ft.BorderSide(1, "#607D8B"),
            ft.BorderSide(1, "#607D8B"),
            ft.BorderSide(1, "#607D8B"),
        ),
        border_radius=3,
        bgcolor="rgba(96,125,139,0.12)",
        content=ft.Text(
            avg_label,
            size=7,
            color="#90A4AE",
            weight=ft.FontWeight.BOLD,
            text_align=ft.TextAlign.CENTER,
        ),
        alignment=ft.Alignment(0, 0),
        tooltip=f"Average: {avg_label}",
    )

    return ft.Column(
        [
            ft.Container(width=28, height=transparent_h, bgcolor="transparent"),
            avg_bar,
            ft.Text("AVG", size=9, color="#607D8B", weight=ft.FontWeight.BOLD),
        ],
        spacing=4,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
    )


def _build_avg_expense_bar(avg_amt: float, max_val: float, currency_symbol: str = "৳") -> ft.Column:
    GRAPH_H = 135
    avg_bar_height = max(6, int((avg_amt / max(max_val, 1)) * GRAPH_H))
    transparent_h = GRAPH_H - avg_bar_height

    avg_label = f"{currency_symbol}{int(avg_amt)}"

    avg_bar = ft.Container(
        width=22,
        height=avg_bar_height,
        border=ft.Border(
            ft.BorderSide(1, "#607D8B"),
            ft.BorderSide(1, "#607D8B"),
            ft.BorderSide(1, "#607D8B"),
            ft.BorderSide(1, "#607D8B"),
        ),
        border_radius=2,
        bgcolor="rgba(96,125,139,0.12)",
        content=ft.Text(
            avg_label,
            size=7,
            color="#90A4AE",
            weight=ft.FontWeight.BOLD,
            text_align=ft.TextAlign.CENTER,
        ),
        alignment=ft.Alignment(0, 0),
        tooltip=f"Average: {avg_label}",
    )

    return ft.Column(
        [
            ft.Container(width=22, height=transparent_h, bgcolor="transparent"),
            avg_bar,
            ft.Text("AVG", size=9, color="#607D8B", weight=ft.FontWeight.BOLD),
        ],
        spacing=4,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
    )


# ---------------------------------------------------------------------------
# Graph builders
# ---------------------------------------------------------------------------

def build_chrono_timeline_graph(current_interval, distribution_dict, target_dates=None):
    graph_columns = []
    max_hour_total = 1
    non_zero_values = []

    for k, val in distribution_dict.items():
        if isinstance(val, dict):
            total = sum(val.values())
        elif isinstance(val, (int, float)):
            total = val
        else:
            total = 0
        if total > 0:
            non_zero_values.append(total)
        max_hour_total = max(max_hour_total, total)

    avg_mins = (sum(non_zero_values) / len(non_zero_values)) if non_zero_values else 0

    if current_interval == "Daily":
        sorted_keys = [str(h) for h in range(24)]
    else:
        if target_dates:
            sorted_keys = sorted(target_dates)
        else:
            sorted_keys = sorted(distribution_dict.keys())

    if avg_mins > 0:
        graph_columns.append(_build_avg_focus_bar(avg_mins, max_hour_total))

    for axis_key in sorted_keys:
        hour_data = distribution_dict.get(axis_key, {})
        stacked_segments = []
        total_mins = sum(hour_data.values()) if isinstance(hour_data, dict) else 0

        if total_mins > 0:
            total_bar_height = max(6, int((total_mins / max_hour_total) * 135))
            transparent_space_height = 135 - total_bar_height

            for task_name, mins in sorted(
                hour_data.items(), key=lambda x: str(x[0]).strip().lower()
            ):
                if mins > 0:
                    stacked_segments.append(
                        ft.Container(
                            width=28,
                            height=max(4, int((mins / total_mins) * total_bar_height)),
                            bgcolor=get_focus_color(task_name),
                            border_radius=3,
                            tooltip=f"{axis_key} — {task_name}: {int(mins)}m",
                        )
                    )

            value_label = ft.Text(
                _fmt_mins(total_mins),
                size=7,
                color="#B0BEC5",
                weight=ft.FontWeight.BOLD,
                text_align=ft.TextAlign.CENTER,
            )
            transparent_space_height = max(0, transparent_space_height - 10)
        else:
            transparent_space_height = 131
            value_label = None
            stacked_segments.append(
                ft.Container(
                    width=28,
                    height=4,
                    bgcolor="rgba(255,255,255,0.04)",
                    border_radius=3,
                )
            )

        if current_interval == "Daily":
            try:
                display_label = f"{int(axis_key):02d}h"
            except (ValueError, TypeError):
                display_label = axis_key
        else:
            try:
                display_label = datetime.strptime(axis_key, "%Y-%m-%d").strftime("%b %d")
            except (ValueError, TypeError):
                display_label = axis_key

        column_controls = [
            ft.Container(width=28, height=transparent_space_height, bgcolor="transparent"),
        ]
        if value_label:
            column_controls.append(value_label)
        column_controls.append(
            ft.Column(
                controls=stacked_segments,
                spacing=1,
                alignment=ft.MainAxisAlignment.END,
            )
        )
        column_controls.append(
            ft.Text(
                display_label,
                size=9,
                color="#8E9AA6",
                weight=ft.FontWeight.BOLD,
            )
        )

        graph_columns.append(
            ft.Column(
                column_controls,
                spacing=4,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            )
        )

    subtitle = (
        "Hourly Focus Breakdown"
        if current_interval == "Daily"
        else ("7-Day Focus Trend" if current_interval == "Weekly" else "30-Day Focus Overview")
    )

    return ft.Container(
        content=ft.Column(
            [
                ft.Row(
                    [
                        ft.Text(
                            "Distributed Chronological Focus Timeline Grid",
                            size=13,
                            weight=ft.FontWeight.W_600,
                            color="#FFFFFF",
                        ),
                        ft.Text(subtitle, size=10, color="#45A29E"),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                ft.Divider(height=12, color="rgba(255,255,255,0.05)"),
                ft.Container(
                    content=ft.Row(
                        controls=graph_columns,
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        scroll=ft.ScrollMode.ADAPTIVE,
                    ),
                    padding=ft.Padding(5, 8, 5, 2),
                ),
            ]
        ),
        bgcolor="#151A22",
        padding=16,
        border_radius=10,
        border=ft.Border(
            ft.BorderSide(1, "rgba(255,255,255,0.05)"),
            ft.BorderSide(1, "rgba(255,255,255,0.05)"),
            ft.BorderSide(1, "rgba(255,255,255,0.05)"),
            ft.BorderSide(1, "rgba(255,255,255,0.05)"),
        ),
    )


def build_expense_trend_graph(current_interval, target_dates, raw_expenses_list, currency_symbol: str = "৳"):
    clean_targets = [clean_date_string(d) for d in target_dates]
    day_totals = {d: 0.0 for d in clean_targets}
    day_categories = {d: {} for d in clean_targets}

    for exp in raw_expenses_list:
        if not isinstance(exp, dict):
            continue
        exp_date = clean_date_string(exp.get("date", ""))
        if exp_date in day_totals:
            try:
                amt = float(exp.get("amount", 0.0))
                cat = str(exp.get("category", "Other")).strip()
                day_totals[exp_date] += amt
                if cat not in day_categories[exp_date]:
                    day_categories[exp_date][cat] = 0.0
                day_categories[exp_date][cat] += amt
            except (ValueError, TypeError):
                continue

    non_zero_amounts = [v for v in day_totals.values() if v > 0]
    max_val = max(non_zero_amounts) if non_zero_amounts else 1.0
    avg_amt = (sum(non_zero_amounts) / len(non_zero_amounts)) if non_zero_amounts else 0.0

    columns = []

    if current_interval in ("Weekly", "Monthly") and avg_amt > 0:
        columns.append(_build_avg_expense_bar(avg_amt, max_val, currency_symbol))

    for day_stamp in sorted(day_totals.keys()):
        total_amt = day_totals[day_stamp]
        total_bar_height = max(4, int((total_amt / max_val) * 135))
        stacked_segments = []
        cats_on_this_day = day_categories.get(day_stamp, {})
        actual_segments_height = 0

        if total_amt > 0 and cats_on_this_day:
            for cat_name, cat_amt in sorted(
                cats_on_this_day.items(), key=lambda x: str(x[0]).strip().lower()
            ):
                if cat_amt > 0:
                    segment_height = max(4, int((cat_amt / total_amt) * total_bar_height))
                    actual_segments_height += segment_height
                    segment_color = get_expense_color(cat_name)
                    stacked_segments.append(
                        ft.Container(
                            width=22,
                            height=segment_height,
                            bgcolor=segment_color,
                            border_radius=2,
                            tooltip=f"{cat_name}: {currency_symbol}{int(cat_amt)}",
                        )
                    )
            transparent_space_height = max(0, 135 - actual_segments_height)
        else:
            transparent_space_height = 131
            stacked_segments.append(
                ft.Container(
                    width=22,
                    height=4,
                    bgcolor="rgba(255,255,255,0.02)",
                    border_radius=2,
                )
            )

        try:
            parsed_label = datetime.strptime(day_stamp, "%Y-%m-%d").strftime("%d")
        except ValueError:
            parsed_label = day_stamp[-2:]

        if total_amt > 0:
            value_label = ft.Text(
                f"{currency_symbol}{int(total_amt)}",
                size=7,
                color="#B0BEC5",
                weight=ft.FontWeight.BOLD,
                text_align=ft.TextAlign.CENTER,
            )
            transparent_space_height = max(0, transparent_space_height - 10)
        else:
            value_label = None

        column_controls = [
            ft.Container(width=22, height=transparent_space_height, bgcolor="transparent"),
        ]
        if value_label:
            column_controls.append(value_label)
        column_controls.append(
            ft.Column(
                controls=stacked_segments,
                spacing=1,
                alignment=ft.MainAxisAlignment.END,
            )
        )
        column_controls.append(
            ft.Text(
                parsed_label,
                size=9,
                color="#8E9AA6",
                weight=ft.FontWeight.BOLD,
            )
        )

        columns.append(
            ft.Column(
                column_controls,
                spacing=4,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            )
        )

    return ft.Container(
        content=ft.Column(
            [
                ft.Row(
                    [
                        ft.Text(
                            "Categorical Resource Expenditures Trend Timeline",
                            size=13,
                            weight=ft.FontWeight.W_600,
                            color="#FFFFFF",
                        ),
                        ft.Text("Financial Capital Burns", size=10, color="#FF9100"),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                ft.Divider(height=12, color="rgba(255,255,255,0.05)"),
                ft.Container(
                    content=ft.Row(
                        controls=columns,
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        scroll=ft.ScrollMode.ADAPTIVE,
                    ),
                    padding=ft.Padding(5, 8, 5, 2),
                ),
            ]
        ),
        bgcolor="#151A22",
        padding=16,
        border_radius=10,
        border=ft.Border(
            ft.BorderSide(1, "rgba(255,255,255,0.05)"),
            ft.BorderSide(1, "rgba(255,255,255,0.05)"),
            ft.BorderSide(1, "rgba(255,255,255,0.05)"),
            ft.BorderSide(1, "rgba(255,255,255,0.05)"),
        ),
    )


def build_weekday_focus_graph(weekday_totals: dict) -> ft.Container:
    BAR_COLOR = "#7C4DFF"
    GRAPH_H = 135

    weekday_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    weekday_short = {
        "Monday": "Mon", "Tuesday": "Tue", "Wednesday": "Wed", "Thursday": "Thu",
        "Friday": "Fri", "Saturday": "Sat", "Sunday": "Sun",
    }

    max_total = max(weekday_totals.values()) if weekday_totals else 0
    max_total = max(max_total, 1)

    columns = []
    for day_name in weekday_order:
        total_mins = weekday_totals.get(day_name, 0)

        if total_mins > 0:
            bar_height = max(6, int((total_mins / max_total) * GRAPH_H))
            transparent_h = max(0, (GRAPH_H - bar_height) - 10)
            value_label = ft.Text(
                _fmt_mins(total_mins),
                size=7,
                color="#B0BEC5",
                weight=ft.FontWeight.BOLD,
                text_align=ft.TextAlign.CENTER,
            )
            bar = ft.Container(
                width=28,
                height=bar_height,
                bgcolor=BAR_COLOR,
                border_radius=3,
                tooltip=f"{day_name}: {_fmt_mins(total_mins)} total (all-time)",
            )
        else:
            transparent_h = 131
            value_label = None
            bar = ft.Container(
                width=28,
                height=4,
                bgcolor="rgba(255,255,255,0.04)",
                border_radius=3,
            )

        column_controls = [
            ft.Container(width=28, height=transparent_h, bgcolor="transparent"),
        ]
        if value_label:
            column_controls.append(value_label)
        column_controls.append(bar)
        column_controls.append(
            ft.Text(weekday_short[day_name], size=9, color="#8E9AA6", weight=ft.FontWeight.BOLD)
        )

        columns.append(
            ft.Column(
                column_controls,
                spacing=4,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            )
        )

    top_day = max(weekday_totals, key=weekday_totals.get) if any(weekday_totals.values()) else None
    subtitle = f"Peak day: {top_day}" if top_day else "No data logged yet"

    return ft.Container(
        content=ft.Column(
            [
                ft.Row(
                    [
                        ft.Text(
                            "Focus By Day Of Week",
                            size=13,
                            weight=ft.FontWeight.W_600,
                            color="#FFFFFF",
                        ),
                        ft.Text(subtitle, size=10, color=BAR_COLOR),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                ft.Divider(height=12, color="rgba(255,255,255,0.05)"),
                ft.Container(
                    content=ft.Row(
                        controls=columns,
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        scroll=ft.ScrollMode.ADAPTIVE,
                    ),
                    padding=ft.Padding(5, 8, 5, 2),
                ),
            ]
        ),
        bgcolor="#151A22",
        padding=16,
        border_radius=10,
        border=ft.Border(
            ft.BorderSide(1, "rgba(255,255,255,0.05)"),
            ft.BorderSide(1, "rgba(255,255,255,0.05)"),
            ft.BorderSide(1, "rgba(255,255,255,0.05)"),
            ft.BorderSide(1, "rgba(255,255,255,0.05)"),
        ),
    )


def build_monthly_horizontal_focus_graph(raw_hourly_distribution_data):
    base_today = datetime.now()
    monthly_dates = [
        (base_today - timedelta(days=i)).strftime("%Y-%m-%d")
        for i in reversed(range(30))
    ]

    SECONDS_IN_DAY = 86400
    scrollable_day_rows = []

    for day_stamp in monthly_dates:
        day_hours_data = raw_hourly_distribution_data.get(day_stamp, {})
        timeline_segments = []

        sorted_hours = (
            sorted([int(h) for h in day_hours_data.keys()])
            if isinstance(day_hours_data, dict)
            else []
        )
        last_processed_second = 0

        for current_hour in sorted_hours:
            h_str = str(current_hour)
            tasks_dict = day_hours_data.get(h_str, {})
            if not isinstance(tasks_dict, dict):
                continue

            for task_name, duration_mins in tasks_dict.items():
                if duration_mins <= 0:
                    continue

                session_start_second = current_hour * 3600
                session_duration_seconds = int(duration_mins * 60)
                session_end_second = min(
                    SECONDS_IN_DAY, session_start_second + session_duration_seconds
                )

                if session_start_second > last_processed_second:
                    gap_duration = session_start_second - last_processed_second
                    timeline_segments.append(
                        ft.Container(
                            expand=gap_duration,
                            height=14,
                            bgcolor="rgba(255,255,255,0.03)",
                        )
                    )

                actual_duration = session_end_second - max(
                    last_processed_second, session_start_second
                )
                if actual_duration > 0:
                    timeline_segments.append(
                        ft.Container(
                            expand=actual_duration,
                            height=14,
                            bgcolor=get_focus_color(task_name),
                            border_radius=1,
                            tooltip=(
                                f"Date: {day_stamp}\n"
                                f"Focus Type: {task_name}\n"
                                f"Duration: {int(duration_mins)}m"
                            ),
                        )
                    )
                last_processed_second = session_end_second

        if last_processed_second < SECONDS_IN_DAY:
            timeline_segments.append(
                ft.Container(
                    expand=SECONDS_IN_DAY - last_processed_second,
                    height=14,
                    bgcolor="rgba(255,255,255,0.03)",
                )
            )
        if not timeline_segments:
            timeline_segments.append(
                ft.Container(
                    expand=SECONDS_IN_DAY,
                    height=14,
                    bgcolor="rgba(255,255,255,0.03)",
                )
            )

        try:
            display_axis_label = datetime.strptime(day_stamp, "%Y-%m-%d").strftime("%b %d")
        except ValueError:
            display_axis_label = day_stamp[-5:]

        scrollable_day_rows.append(
            ft.Container(
                content=ft.Row(
                    [
                        ft.Container(
                            content=ft.Text(
                                display_axis_label,
                                size=10,
                                color="#8E9AA6",
                                weight=ft.FontWeight.BOLD,
                            ),
                            width=55,
                            alignment=ft.Alignment(-1, 0),
                        ),
                        ft.Row(
                            controls=timeline_segments,
                            spacing=0,
                            alignment=ft.MainAxisAlignment.START,
                            expand=True,
                        ),
                    ],
                    spacing=3,
                    alignment=ft.MainAxisAlignment.START,
                ),
                padding=ft.Padding(0, 0, 0, 4),
                border=ft.Border(bottom=ft.BorderSide(1, "rgba(255,255,255,0.06)")),
            )
        )

    static_bottom_axis_controls = [ft.Container(width=55)]
    for h in range(24):
        static_bottom_axis_controls.append(
            ft.Container(
                content=ft.Text(
                    f"{h:02d}h",
                    size=8,
                    color="#8E9AA6",
                    weight=ft.FontWeight.BOLD,
                    text_align=ft.TextAlign.CENTER,
                ),
                expand=True,
            )
        )

    return ft.Container(
        content=ft.Column(
            [
                ft.Row(
                    [
                        ft.Text(
                            "Static 30-Day Focus Horizon Matrix (High-Fidelity Chrono Map)",
                            size=13,
                            weight=ft.FontWeight.W_600,
                            color="#FFFFFF",
                        ),
                        ft.Text("Monthly Focus Map", size=10, color="#00FFFF"),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                ft.Divider(height=12, color="rgba(255,255,255,0.05)"),
                ft.Container(
                    content=ft.Column(
                        controls=scrollable_day_rows,
                        spacing=4,
                        scroll=ft.ScrollMode.ALWAYS,
                        auto_scroll=True,
                    ),
                    height=165,
                    padding=ft.Padding(0, 2, 5, 2),
                ),
                ft.Divider(height=8, color="rgba(255,255,255,0.03)"),
                ft.Row(
                    controls=static_bottom_axis_controls,
                    spacing=0,
                    alignment=ft.MainAxisAlignment.START,
                ),
            ]
        ),
        bgcolor="#151A22",
        padding=16,
        border_radius=10,
        border=ft.Border(
            ft.BorderSide(1, "rgba(255,255,255,0.05)"),
            ft.BorderSide(1, "rgba(255,255,255,0.05)"),
            ft.BorderSide(1, "rgba(255,255,255,0.05)"),
            ft.BorderSide(1, "rgba(255,255,255,0.05)"),
        ),
    )


# ---------------------------------------------------------------------------
# NEW: Focus vs. Spending correlation chart
# ---------------------------------------------------------------------------

def build_focus_vs_spending_chart(num_days: int = 30,
                                   currency_symbol: str = "৳") -> ft.Container:
    """
    Dual-axis bar chart: side-by-side cyan (focus mins) and orange (spend)
    bars for each of the last `num_days` calendar days, oldest-first.
    Both bar columns share 180px max height but scale independently
    (focus axis vs. spend axis are separate).
    """
    from .engine import get_focus_vs_spending_by_day

    GRAPH_H   = 180
    BAR_W     = 6    # width of each individual segment bar
    DAY_GAP   = 3    # gap between left/right bars within a day
    COL_GAP   = 4    # gap between day columns
    FOCUS_CLR = "#00FFFF"
    SPEND_CLR = "#FF9100"

    rows = get_focus_vs_spending_by_day(num_days)

    all_focus = [r["focus_mins"] for r in rows]
    all_spend = [r["spend"]      for r in rows]
    max_focus = max(all_focus) if any(f > 0 for f in all_focus) else 1
    max_spend = max(all_spend) if any(s > 0 for s in all_spend) else 1

    # No-data guard
    if all(f == 0 for f in all_focus) and all(s == 0 for s in all_spend):
        return ft.Container(
            content=ft.Column(
                [
                    ft.Text(
                        "Focus vs. Spending — Last 30 Days",
                        size=12, color="grey500",
                    ),
                    ft.Container(
                        content=ft.Text(
                            "No data yet",
                            size=13, color="grey600", italic=True,
                            text_align=ft.TextAlign.CENTER,
                        ),
                        alignment=ft.Alignment(0, 0),
                        expand=True,
                    ),
                ],
                spacing=6,
            ),
            bgcolor="#11151D",
            border_radius=10,
            padding=10,
            height=240,
        )

    day_columns = []
    for i, row in enumerate(rows):
        focus_mins = row["focus_mins"]
        spend_amt  = row["spend"]
        date_str   = row["date"]

        focus_h = max(2, int((focus_mins / max_focus) * GRAPH_H)) if focus_mins > 0 else 0
        spend_h = max(2, int((spend_amt  / max_spend)  * GRAPH_H)) if spend_amt  > 0 else 0

        focus_spacer = GRAPH_H - focus_h
        spend_spacer = GRAPH_H - spend_h

        # X-axis label: day-of-month every 5th day
        try:
            dom = datetime.strptime(date_str, "%Y-%m-%d").strftime("%d")
        except ValueError:
            dom = date_str[-2:]
        x_label = dom if (i % 5 == 0) else ""

        focus_col = ft.Column(
            [
                ft.Container(width=BAR_W, height=focus_spacer, bgcolor="transparent"),
                ft.Container(
                    width=BAR_W,
                    height=focus_h if focus_h > 0 else 2,
                    bgcolor=FOCUS_CLR if focus_h > 0 else "transparent",
                    border_radius=2,
                    tooltip=f"{date_str}\nFocus: {int(focus_mins)}m",
                ),
            ],
            spacing=0,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        )

        spend_col = ft.Column(
            [
                ft.Container(width=BAR_W, height=spend_spacer, bgcolor="transparent"),
                ft.Container(
                    width=BAR_W,
                    height=spend_h if spend_h > 0 else 2,
                    bgcolor=SPEND_CLR if spend_h > 0 else "transparent",
                    border_radius=2,
                    tooltip=f"{date_str}\nSpend: {currency_symbol}{spend_amt:,.0f}",
                ),
            ],
            spacing=0,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        )

        day_col = ft.Column(
            [
                ft.Row(
                    [focus_col, spend_col],
                    spacing=DAY_GAP,
                    alignment=ft.MainAxisAlignment.CENTER,
                ),
                ft.Text(
                    x_label,
                    size=8,
                    color="#8E9AA6",
                    weight=ft.FontWeight.BOLD,
                    text_align=ft.TextAlign.CENTER,
                    width=(BAR_W * 2 + DAY_GAP),
                ),
            ],
            spacing=3,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        )

        day_columns.append(day_col)

    legend = ft.Row(
        [
            ft.Row(
                [
                    ft.Container(width=10, height=10, bgcolor=FOCUS_CLR, border_radius=2),
                    ft.Text("Focus (min)", size=11, color=FOCUS_CLR),
                ],
                spacing=5,
            ),
            ft.Row(
                [
                    ft.Container(width=10, height=10, bgcolor=SPEND_CLR, border_radius=2),
                    ft.Text(f"Spend ({currency_symbol})", size=11, color=SPEND_CLR),
                ],
                spacing=5,
            ),
        ],
        spacing=16,
    )

    return ft.Container(
        content=ft.Column(
            [
                ft.Text(
                    "Focus vs. Spending — Last 30 Days",
                    size=12, color="grey500",
                ),
                ft.Container(height=4),
                legend,
                ft.Container(height=6),
                ft.Container(
                    content=ft.Row(
                        controls=day_columns,
                        spacing=COL_GAP,
                        alignment=ft.MainAxisAlignment.START,
                        scroll=ft.ScrollMode.ADAPTIVE,
                    ),
                    padding=ft.Padding(4, 4, 4, 0),
                ),
            ],
            spacing=0,
        ),
        bgcolor="#11151D",
        border_radius=10,
        padding=10,
    )