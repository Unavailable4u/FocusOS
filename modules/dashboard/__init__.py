import flet as ft
from datetime import datetime, timedelta
import data_manager as dm
import asyncio
from .engine import parse_aggregated_metrics, get_date_range_display_string, get_focus_streak, get_weekly_summary
from .timelines import build_chrono_timeline_graph, build_expense_trend_graph, build_monthly_horizontal_focus_graph
from .charts import create_stat_card, build_proportional_share_panel, build_upcoming_goal_pie_panel

def build_dashboard(page: ft.Page):
    current_interval = "Daily"
    time_offset = 0  # 0 = today, -1 = yesterday, etc.

    dashboard_subtitle_lbl = ft.Text("", size=13, color="grey600")
    card_focus    = ft.Container(expand=True)
    card_tasks    = ft.Container(expand=True)
    card_expenses = ft.Container(expand=True)
    card_streak   = ft.Container(expand=True)   # 4th stat card

    chrono_bar_graph         = ft.Container(expand=True)
    expense_bar_graph        = ft.Container(expand=True)
    monthly_horizontal_graph = ft.Container(expand=True)

    task_distribution_panel    = ft.Container(expand=True)
    expense_distribution_panel = ft.Container(expand=True)
    goal_pie_panel             = build_upcoming_goal_pie_panel()

    def repaint_dashboard_ui():
        nonlocal time_offset
        m           = parse_aggregated_metrics(current_interval, time_offset)
        raw_db_data = dm.load_data()

        btn_next.disabled   = (time_offset >= 0)
        btn_next.icon_color = "grey700" if (time_offset >= 0) else "#00FFFF"
        try: btn_next.update()
        except Exception: pass

        display_dates = []
        for d_str in m["target_dates"]:
            try:
                display_dates.append(datetime.strptime(d_str, "%Y-%m-%d").strftime("%Y-%m-%d"))
            except ValueError:
                display_dates.append(d_str)

        dashboard_subtitle_lbl.value = get_date_range_display_string(current_interval, display_dates)
        try: dashboard_subtitle_lbl.update()
        except Exception: pass

        f_hours, f_mins = divmod(m["total_focus_mins"], 60)
        card_focus.content    = create_stat_card(
            f"FOCUS TIME TRACKED ({current_interval.upper()})",
            f"{f_hours}h {int(f_mins)}m",
            "Productive focus allocation", "#00FFFF")
        card_tasks.content    = create_stat_card(
            "MATRIX TOTAL ACTIONS",
            f"{m['completed_tasks']}",
            f"Active backlog remaining: {m['pending_tasks']}", "#00E676")
        card_expenses.content = create_stat_card(
            "CONSOLIDATED BURNS TALLY",
            f"৳{m['total_expense']:,.2f}",
            "Tracked financial outbounds", "#FF9100")

        # ── Streak card — always reflects current running streak ─────────────
        streak = get_focus_streak()
        if streak == 0:
            streak_value    = "0 days"
            streak_subtitle = "Log 25+ min today to start your streak!"
        elif streak == 1:
            streak_value    = "🔥 1 day"
            streak_subtitle = "Streak started — keep it going!"
        else:
            streak_value    = f"🔥 {streak} days"
            streak_subtitle = f"{streak} consecutive days of 25+ min focus"
        card_streak.content = create_stat_card(
            "FOCUS STREAK",
            streak_value,
            streak_subtitle, "#FFEA00")

        chrono_bar_graph.content = build_chrono_timeline_graph(
            current_interval, m["chrono_distribution"], m["target_dates"])
        task_distribution_panel.content = build_proportional_share_panel(
            "Task Category Volume Distribution Share",
            m["task_time_breakdown"], is_currency=False)
        expense_distribution_panel.content = build_proportional_share_panel(
            "Capital Resource Cost Proportional Allocation",
            m["category_expense_breakdown"], is_currency=True)

        expense_bar_graph.content = build_expense_trend_graph(
            current_interval, display_dates, raw_db_data.get("expenses", []))
        monthly_horizontal_graph.content = build_monthly_horizontal_focus_graph(
            raw_db_data.get("hourly_task_distribution", {}))

        try:
            card_focus.update(); card_tasks.update()
            card_expenses.update(); card_streak.update()
            chrono_bar_graph.update(); expense_bar_graph.update()
            monthly_horizontal_graph.update()
            task_distribution_panel.update(); expense_distribution_panel.update()
            goal_pie_panel.update()
        except Exception: pass

    def interval_changed(e):
        nonlocal current_interval, time_offset
        current_interval = "Daily" if e.control.selected_index == 0 else ("Weekly" if e.control.selected_index == 1 else "Monthly")
        time_offset = 0
        repaint_dashboard_ui()

    def step_backward(e):
        nonlocal time_offset
        time_offset -= 1
        repaint_dashboard_ui()

    def step_forward(e):
        nonlocal time_offset
        if time_offset < 0:
            time_offset += 1
            repaint_dashboard_ui()

    _pending_date = {"value": None}

    def handle_anchor_date_change(e):
        if e.control.value:
            _pending_date["value"] = e.control.value

    def handle_anchor_date_dismiss(e):
        nonlocal time_offset
        raw = _pending_date["value"]
        if raw is None:
            return
        if hasattr(raw, "date"):
            selected_day = raw.date() + timedelta(days=1)
        else:
            selected_day = raw + timedelta(days=1)
        today_day = datetime.now().date()
        delta     = selected_day - today_day
        if current_interval == "Daily":
            time_offset = delta.days
        elif current_interval == "Weekly":
            time_offset = delta.days // 7
        else:
            time_offset = delta.days // 30
        _pending_date["value"] = None
        repaint_dashboard_ui()

    anchor_picker_dialog = ft.DatePicker(
        first_date=datetime(2020, 1, 1),
        last_date=datetime(2030, 12, 31),
        on_change=handle_anchor_date_change,
        on_dismiss=handle_anchor_date_dismiss,
    )
    if anchor_picker_dialog not in page.overlay:
        page.overlay.append(anchor_picker_dialog)

    def trigger_anchor_calendar(e):
        anchor_picker_dialog.open = True
        page.update()

    # ── Weekly Summary Banner ─────────────────────────────────────────────────
    # Show when: it's Monday  OR  the banner has never been dismissed / was last
    # dismissed on a different Monday than today's.
    def _this_monday() -> str:
        today = datetime.now().date()
        return (today - timedelta(days=today.weekday())).strftime("%Y-%m-%d")

    def _should_show_banner() -> bool:
        raw_data      = dm.load_data()
        last_dismissed = raw_data.get("last_summary_dismissed", "")
        return last_dismissed != _this_monday()

    weekly_banner = ft.Banner(
        bgcolor="#1A2332",
        leading=ft.Icon(ft.Icons.INSIGHTS_ROUNDED, color="#00FFFF", size=32),
        content=ft.Text("", color="white", size=13),
        actions=[
            ft.TextButton(
                "Dismiss",
                style=ft.ButtonStyle(color="#00FFFF"),
                on_click=lambda e: _dismiss_banner(e),
            )
        ],
        visible=False,
    )

    def _build_banner_text(s: dict) -> str:
        h, m = divmod(int(s["total_focus_mins"]), 60)
        focus_str   = f"{h}h {m}m" if h else f"{m}m"
        top_str     = f"  ·  Top task: {s['top_task']}" if s["top_task"] else ""
        expense_str = f"৳{s['total_expense']:,.0f}" if s["total_expense"] else "৳0"
        return (
            f"📊  Weekly wrap  ({s['week_start']} → {s['week_end']})   "
            f"Focus: {focus_str}{top_str}   "
            f"Burns: {expense_str}   "
            f"Completed tasks: {s['completed_tasks']}"
        )

    def _dismiss_banner(e):
        raw_data = dm.load_data()
        raw_data["last_summary_dismissed"] = _this_monday()
        dm.save_data(raw_data)
        weekly_banner.visible = False
        try:
            weekly_banner.update()
        except Exception:
            pass

    if _should_show_banner():
        s = get_weekly_summary()
        weekly_banner.content = ft.Text(_build_banner_text(s), color="white", size=13)
        weekly_banner.visible = True

    interval_toggle = ft.CupertinoSegmentedButton(
        controls=[
            ft.Text("Daily View",   size=12, weight=ft.FontWeight.W_600, width=80, text_align=ft.TextAlign.CENTER),
            ft.Text("Weekly View",  size=12, weight=ft.FontWeight.W_600, width=80, text_align=ft.TextAlign.CENTER),
            ft.Text("Monthly View", size=12, weight=ft.FontWeight.W_600, width=80, text_align=ft.TextAlign.CENTER),
        ],
        selected_index=0, selected_color="#00FFFF", unselected_color="#1E2631",
        border_color="rgba(255,255,255,0.15)", on_change=interval_changed,
    )

    btn_prev     = ft.IconButton(icon=ft.Icons.KEYBOARD_ARROW_LEFT_ROUNDED,  icon_color="#00FFFF", icon_size=22, on_click=step_backward)
    btn_next     = ft.IconButton(icon=ft.Icons.KEYBOARD_ARROW_RIGHT_ROUNDED, icon_color="grey700", icon_size=22, on_click=step_forward, disabled=True)
    btn_calendar = ft.IconButton(icon=ft.Icons.CALENDAR_MONTH_ROUNDED,       icon_color="#00FFFF", icon_size=22, on_click=trigger_anchor_calendar)

    header_bar = ft.Container(
        content=ft.Row([
            ft.Column([
                ft.Text("Comprehensive Performance Dashboard Engine", size=22, weight=ft.FontWeight.W_600, color="#45A29E"),
                dashboard_subtitle_lbl,
            ], spacing=2),
            ft.Row([btn_prev, btn_calendar, interval_toggle, btn_next], spacing=4, alignment=ft.MainAxisAlignment.END),
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
        bgcolor="#1E2631",
        padding=ft.Padding(left=4, right=4, top=10, bottom=10),
    )

    dashboard_scroll_body = ft.Column([
        ft.Container(height=10),
        # All 4 stat cards in one row
        ft.Row([card_focus, card_tasks, card_expenses, card_streak], spacing=12),
        ft.Container(height=5),
        monthly_horizontal_graph,
        ft.Container(height=5),
        chrono_bar_graph,
        ft.Container(height=5),
        ft.Row([task_distribution_panel, expense_distribution_panel, goal_pie_panel], spacing=12, alignment=ft.MainAxisAlignment.START),
        ft.Container(height=5),
        expense_bar_graph,
        ft.Container(height=5),
    ], expand=True, scroll=ft.ScrollMode.ALWAYS)

    dashboard_layout_view = ft.Column(
        [weekly_banner, header_bar, dashboard_scroll_body],
        expand=True,
        spacing=0,
    )

    async def snap_inner_matrix_to_end_async():
        await asyncio.sleep(0.15)
        try:
            if monthly_horizontal_graph.content and len(monthly_horizontal_graph.content.controls) >= 3:
                inner_scroll_wrapper = monthly_horizontal_graph.content.controls[2]
                if hasattr(inner_scroll_wrapper, "content") and inner_scroll_wrapper.content:
                    await inner_scroll_wrapper.content.scroll_to(offset=-1, duration=100)
        except Exception:
            pass

    def schedule_native_callback():
        asyncio.run_coroutine_threadsafe(snap_inner_matrix_to_end_async(), page.loop)

    import threading
    threading.Thread(target=schedule_native_callback, daemon=True).start()

    repaint_dashboard_ui()

    return dashboard_layout_view