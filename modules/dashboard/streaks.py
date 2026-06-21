import flet as ft
from datetime import datetime, timedelta

from modules.glass_theme import create_glass_card
from modules.dashboard import engine

# ---------------------------------------------------------------------------
# Streak heatmap / goal-completion calendar
#
# GitHub-contributions-style grid. Doubles as two visualizations in one:
#   1. "Streak heatmap"           — at a glance, which days had any focus
#   2. "Goal completion % by day" — the color step encodes how close each
#                                    day got to goals["daily_focus_minutes"]
#
# Built on engine.get_daily_completion_map() / engine.calculate_focus_streak()
# (both already read the user's actual goal via data_manager.get_goals()).
# ---------------------------------------------------------------------------

CELL_SIZE = 14
CELL_GAP = 3
DAYS_PER_WEEK = 7
DEFAULT_LOOKBACK_DAYS = 90

# "No data logged" — kept visually distinct from "logged, but 0% of goal".
# Matches the faint-hairline / muted-grey vocabulary used elsewhere
# (charts.py's "rgba(255,255,255,0.05)" borders, "grey600" subtitles).
NO_DATA_COLOR = "rgba(255,255,255,0.06)"

# 5-step intensity ramp, dim teal -> bright cyan, keyed off completion %.
# Picked to sit next to this app's existing accent colors (charts.py uses
# "#45A29E" for focus subtitles, timelines.py uses "#00FFFF" for the
# monthly focus map) rather than inventing an unrelated palette.
INTENSITY_RAMP = [
    "#0B3D3A",  # >0%   — barest dim teal, "something happened"
    "#13564F",  # >=25%
    "#1B7A6E",  # >=50%
    "#23A28F",  # >=75%  (close to charts.py's #45A29E accent)
    "#3FE0C5",  # >=100% — bright cyan, goal met or exceeded
]


def _color_for_day(minutes: float, pct: float) -> str:
    """
    Picks a cell color from NO_DATA_COLOR or the 5-step INTENSITY_RAMP.

    minutes is the raw logged total for the day — used only to distinguish
    "no data" from "data, but 0% of goal". When no daily goal is set,
    engine.get_daily_completion_map() returns 0 for every day regardless
    of minutes logged, so pct alone can't make that distinction.
    """
    if minutes <= 0:
        return NO_DATA_COLOR
    if pct >= 100:
        return INTENSITY_RAMP[4]
    if pct >= 75:
        return INTENSITY_RAMP[3]
    if pct >= 50:
        return INTENSITY_RAMP[2]
    if pct >= 25:
        return INTENSITY_RAMP[1]
    return INTENSITY_RAMP[0]


def _day_minutes_lookup(num_days: int) -> dict:
    """
    Builds {date_str: minutes} for the same window get_daily_completion_map()
    covers, so each cell's tooltip can show raw minutes alongside percentage
    without re-deriving totals from hourly_task_distribution per cell.
    """
    data = engine.dm.load_data()
    distribution = data.get("hourly_task_distribution", {})
    today = datetime.now().date()

    minutes_by_day = {}
    for offset in range(num_days - 1, -1, -1):
        day_str = (today - timedelta(days=offset)).strftime("%Y-%m-%d")
        minutes_by_day[day_str] = engine._day_total_minutes(distribution, day_str)
    return minutes_by_day


def _build_cell(date_str: str, minutes: float, pct: float) -> ft.Container:
    """A single ~14x14 day cell with a tooltip showing date / minutes / %."""
    color = _color_for_day(minutes, pct)

    try:
        pretty_date = datetime.strptime(date_str, "%Y-%m-%d").strftime("%b %d, %Y")
    except ValueError:
        pretty_date = date_str

    if minutes <= 0:
        tooltip_str = f"{pretty_date}\nNo focus logged"
    else:
        tooltip_str = f"{pretty_date}\n{int(minutes)}m logged\n{pct:.0f}% of goal"

    return ft.Container(
        width=CELL_SIZE,
        height=CELL_SIZE,
        bgcolor=color,
        border_radius=3,
        tooltip=tooltip_str,
    )


def _build_grid(num_days: int = DEFAULT_LOOKBACK_DAYS) -> ft.Row:
    """
    Builds the GitHub-style grid: a Row of week-columns, each a Column of
    up to 7 day-cells, oldest week on the left, most recent on the right;
    within a week column, days run top (oldest) to bottom (newest).
    """
    completion_map = engine.get_daily_completion_map(num_days)
    minutes_map = _day_minutes_lookup(num_days)

    dates_oldest_first = list(completion_map.keys())  # already oldest->newest

    # Pad the front so the oldest week column is a full 7 days; padding
    # cells render as invisible spacers (keeps column alignment for a
    # partial leading week, same as GitHub's own contribution grid).
    pad_count = (DAYS_PER_WEEK - (len(dates_oldest_first) % DAYS_PER_WEEK)) % DAYS_PER_WEEK
    padded_dates = [None] * pad_count + dates_oldest_first

    week_columns = []
    for week_start in range(0, len(padded_dates), DAYS_PER_WEEK):
        week_dates = padded_dates[week_start:week_start + DAYS_PER_WEEK]
        day_cells = []
        for date_str in week_dates:
            if date_str is None:
                day_cells.append(ft.Container(width=CELL_SIZE, height=CELL_SIZE))
            else:
                day_cells.append(
                    _build_cell(
                        date_str,
                        minutes_map.get(date_str, 0),
                        completion_map.get(date_str, 0),
                    )
                )
        week_columns.append(ft.Column(controls=day_cells, spacing=CELL_GAP, tight=True))

    return ft.Row(
        controls=week_columns,
        spacing=CELL_GAP,
        scroll=ft.ScrollMode.ADAPTIVE,
    )


def _build_legend() -> ft.Row:
    """Small inline legend mapping ramp steps to rough % bands."""
    labels = ["No data", "1-24%", "25-49%", "50-74%", "75-99%", "100%+"]
    colors = [NO_DATA_COLOR] + INTENSITY_RAMP

    swatches = []
    for label, color in zip(labels, colors):
        swatches.append(
            ft.Row(
                [
                    ft.Container(width=10, height=10, bgcolor=color, border_radius=2),
                    ft.Text(label, size=10, color="#8E9AA6"),
                ],
                spacing=4,
            )
        )
    return ft.Row(controls=swatches, spacing=12, wrap=True)


def build_streak_heatmap_panel(num_days: int = DEFAULT_LOOKBACK_DAYS) -> ft.Container:
    """
    Public entry point. Returns a glass-themed panel containing the streak /
    goal-completion heatmap, ready to drop into the dashboard layout — same
    call shape as charts.py's build_*_panel() functions.
    """
    current_streak = engine.calculate_focus_streak()
    streak_label = f"{current_streak} day{'s' if current_streak != 1 else ''}"

    content = ft.Column(
        [
            ft.Row(
                [
                    ft.Text(
                        "Focus Streak & Goal Completion",
                        size=13,
                        weight=ft.FontWeight.W_600,
                        color="#FFFFFF",
                    ),
                    ft.Text(f"🔥 {streak_label}", size=10, color="#45A29E"),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            ),
            ft.Divider(height=10, color="rgba(255,255,255,0.05)"),
            ft.Container(height=4),
            _build_grid(num_days),
            ft.Container(height=8),
            _build_legend(),
        ]
    )

    # theme_name=None tracks the user's active glass theme automatically,
    # same convention charts.py uses for every panel it builds.
    return create_glass_card(content, theme_name=None, expand=True, height=260)