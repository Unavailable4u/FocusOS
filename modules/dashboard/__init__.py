import flet as ft
from datetime import datetime, timedelta
import data_manager as dm
import asyncio
from .engine import parse_aggregated_metrics, get_date_range_display_string
from .timelines import build_chrono_timeline_graph, build_expense_trend_graph, build_monthly_horizontal_focus_graph
from .charts import create_stat_card, build_proportional_share_panel, build_upcoming_goal_pie_panel

def build_dashboard(page: ft.Page):
    current_interval = "Daily"
    time_offset = 0  # 0 = today, -1 = yesterday, etc.

    dashboard_subtitle_lbl = ft.Text("", size=13, color="grey600")
    card_focus    = ft.Container(expand=True)
    card_tasks    = ft.Container(expand=True)
    card_expenses = ft.Container(expand=True)

    chrono_bar_graph        = ft.Container(expand=True)
    expense_bar_graph       = ft.Container(expand=True)
    monthly_horizontal_graph = ft.Container(expand=True)

    task_distribution_panel    = ft.Container(expand=True)
    expense_distribution_panel = ft.Container(expand=True)
    goal_pie_panel             = build_upcoming_goal_pie_panel()

    def repaint_dashboard_ui():
        nonlocal time_offset
        m            = parse_aggregated_metrics(current_interval, time_offset)
        raw_db_data  = dm.load_data()

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
        card_focus.content    = create_stat_card(f"FOCUS TIME TRACKED ({current_interval.upper()})", f"{f_hours}h {int(f_mins)}m", "Productive focus allocation", "#00FFFF")
        card_tasks.content    = create_stat_card("MATRIX TOTAL ACTIONS", f"{m['completed_tasks']}", f"Active backlog remaining: {m['pending_tasks']}", "#00E676")
        card_expenses.content = create_stat_card("CONSOLIDATED BURNS TALLY", f"৳{m['total_expense']:,.2f}", "Tracked financial outbounds", "#FF9100")

        chrono_bar_graph.content        = build_chrono_timeline_graph(current_interval, m["chrono_distribution"], m["target_dates"])
        task_distribution_panel.content = build_proportional_share_panel("Task Category Volume Distribution Share", m["task_time_breakdown"], is_currency=False)
        expense_distribution_panel.content = build_proportional_share_panel("Capital Resource Cost Proportional Allocation", m["category_expense_breakdown"], is_currency=True)

        expense_bar_graph.content        = build_expense_trend_graph(current_interval, display_dates, raw_db_data.get("expenses", []))
        monthly_horizontal_graph.content = build_monthly_horizontal_focus_graph(raw_db_data.get("hourly_task_distribution", {}))

        try:
            card_focus.update(); card_tasks.update(); card_expenses.update()
            chrono_bar_graph.update(); expense_bar_graph.update(); monthly_horizontal_graph.update()
            task_distribution_panel.update(); expense_distribution_panel.update(); goal_pie_panel.update()
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

    # ── DATE PICKER FIX ──────────────────────────────────────────────────────
    # Flet's DatePicker fires on_change with a datetime object whose time
    # component is midnight UTC. In UTC+6 that rolls back to the previous
    # calendar day. Fix: store the pending value on on_change, then commit
    # it on on_dismiss (which fires after the user taps OK / confirms).
    _pending_date = {"value": None}

    def handle_anchor_date_change(e):
        """Store the raw picker value; don't apply it yet."""
        if e.control.value:
            _pending_date["value"] = e.control.value

    def handle_anchor_date_dismiss(e):
        """Apply the stored date only when the user confirms (dismisses dialog)."""
        nonlocal time_offset
        raw = _pending_date["value"]
        if raw is None:
            return

        # Normalise to a plain date — add 1 day to correct the UTC-midnight shift
        # that Flet introduces on Windows (picker returns 23:00 prev day in UTC+6).
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
        ft.Row([card_focus, card_tasks, card_expenses], spacing=12),
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
        [header_bar, dashboard_scroll_body],
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