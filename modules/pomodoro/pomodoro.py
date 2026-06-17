import flet as ft
import asyncio
import sys
import os
from datetime import datetime

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(CURRENT_DIR))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

import data_manager as dm
from modules.glass_theme import GLASS_THEMES, create_glass_card
from modules.color_palette import get_task_color
from .clock_face import generate_precision_radial_clock

_global_timer_session = None


def _get_task_color(task_name):
    """
    Single source-of-truth color lookup for this page.
    Delegates to modules/color_palette.py so focus bars, the clock view,
    and the legend all share exactly the same hues as the rest of the app.

    Passes the current list of DB task titles as `all_known_tasks` so
    overflow colors are assigned by stable index (matching legacy
    get_task_color_signature behavior) rather than pure hash, wherever
    possible.
    """
    try:
        data = dm.load_data()
        db_tasks = [t["title"] for t in data.get("tasks", [])]
    except Exception:
        db_tasks = []
    return get_task_color(task_name, all_known_tasks=db_tasks)


def build_pomodoro(page: ft.Page):
    global _global_timer_session
    
    if _global_timer_session is None:
        _global_timer_session = {
            "timer_running": False,
            "current_mode": "Focus",              
            "total_focus_remaining": 25 * 60,     
            "current_segment_elapsed": 0,         
            "break_time_remaining": 0,            
            "completed_sprints": 0,               
            "active_view": "Bars",
            "active_theme": "Glass Cyan",
            "selected_task": "General Study",
            "live_timer_text": None,
            "live_progress_bar": None
        }
    
    state = _global_timer_session

    def get_config_durations():
        try:
            total_focus_mins = float(focus_input.value) if focus_input.value else 25.0
            short_mins = float(short_break_input.value) if short_break_input.value else 5.0
            long_mins = float(long_break_input.value) if long_break_input.value else 15.0
            interval_target = int(interval_input.value) if interval_input.value else 4
        except ValueError:
            total_focus_mins, short_mins, long_mins, interval_target = 25.0, 5.0, 15.0, 4
        return {"Total Focus": int(total_focus_mins * 60), "Short Break": int(short_mins * 60), "Long Break": int(long_mins * 60), "Interval Target": interval_target}

    def update_timer_display():
        config = get_config_durations()
        target_text = state["live_timer_text"] if state["live_timer_text"] else timer_text
        target_progress = state["live_progress_bar"] if state["live_progress_bar"] else progress_bar
        
        selected_task = state["selected_task"]
        active_color_token = _get_task_color(selected_task)

        if state["current_mode"] == "Focus":
            current_sprint_total = min(25 * 60, state["total_focus_remaining"] + state["current_segment_elapsed"])
            display_seconds = current_sprint_total - state["current_segment_elapsed"]
            mins, secs = divmod(max(0, display_seconds), 60)
            target_text.value = f"{mins:02d}:{secs:02d}"
            
            target_progress.value = min(1.0, state["current_segment_elapsed"] / current_sprint_total) if current_sprint_total > 0 else 0.0
            target_progress.color = active_color_token
        else:
            mins, secs = divmod(max(0, state["break_time_remaining"]), 60)
            target_text.value = f"{mins:02d}:{secs:02d}"
            target_break = config["Short Break"] if state["current_mode"] == "Short Break" else config["Long Break"]
            target_progress.value = min(1.0, (target_break - state["break_time_remaining"]) / target_break) if target_break > 0 else 1.0
            target_progress.color = "#FF1744" if state["current_mode"] == "Short Break" else "#D500F9"
            
        try: page.update()
        except Exception: pass

    def apply_config_changes(e):
        if not state["timer_running"]:
            config = get_config_durations()
            state["total_focus_remaining"] = config["Total Focus"]
            state["current_segment_elapsed"] = 0
            update_timer_display()

    async def tick():  
        while state["timer_running"]:
            await asyncio.sleep(1)  
            if not state["timer_running"]: break
            if state["current_mode"] == "Focus":
                if state["total_focus_remaining"] > 0:
                    state["total_focus_remaining"] -= 1
                    state["current_segment_elapsed"] += 1
                    if state["current_segment_elapsed"] % 60 == 0:
                        selected_task = state["selected_task"]
                        dm.log_focus(selected_task, 1)
                        log_hourly_metric(datetime.now().hour, selected_task, 1)
                        refresh_analytics_display()
                    update_timer_display()
                    if state["current_segment_elapsed"] >= 25 * 60 and state["total_focus_remaining"] > 0:
                        handle_segment_completion(reached_25_min=True)
                        break
                else:
                    handle_segment_completion(reached_25_min=False)
                    break
            else:
                if state["break_time_remaining"] > 0:
                    state["break_time_remaining"] -= 1
                    update_timer_display()
                else:
                    auto_resume_focus()
                    break

    def handle_segment_completion(reached_25_min=True):
        config = get_config_durations()
        target_text = state["live_timer_text"] if state["live_timer_text"] else timer_text
        if reached_25_min:
            state["completed_sprints"] += 1
            state["current_segment_elapsed"] = 0
            if state["completed_sprints"] % config["Interval Target"] == 0:
                state["current_mode"] = "Long Break"
                state["break_time_remaining"] = config["Long Break"]
                target_text.color = "#D500F9"
                status_badge.value = "Status: Auto Long Break! ☕"
            else:
                state["current_mode"] = "Short Break"
                state["break_time_remaining"] = config["Short Break"]
                target_text.color = "#FF1744"
                status_badge.value = "Status: Auto Short Break! ⚡"
            start_btn.visible, stop_btn.visible, skip_break_btn.visible = False, False, True
            update_timer_display()
            page.run_task(tick)
        else:
            reset_timer(None)

    def auto_resume_focus():
        target_text = state["live_timer_text"] if state["live_timer_text"] else timer_text
        state["current_mode"] = "Focus"
        state["current_segment_elapsed"] = 0
        
        selected_task = state["selected_task"]
        target_text.color = _get_task_color(selected_task)
        
        status_badge.value = "Status: Continuing Focus Pool... 🎯"
        start_btn.visible, stop_btn.visible, skip_break_btn.visible = False, True, False
        update_timer_display()
        page.run_task(tick)

    def skip_break_clicked(e):
        state["break_time_remaining"] = 0
        auto_resume_focus()

    def start_timer(e):
        if not state["timer_running"] and state["total_focus_remaining"] > 0:
            state["timer_running"] = True
            target_text = state["live_timer_text"] if state["live_timer_text"] else timer_text
            
            state["selected_task"] = task_dropdown.value if task_dropdown.value else "General Study"
            target_text.color = _get_task_color(state["selected_task"])
            
            start_btn.disabled, stop_btn.disabled = True, False
            toggle_inputs(disabled=True)
            page.run_task(tick)  
            page.update()

    def stop_timer(e):
        state["timer_running"] = False
        start_btn.disabled, stop_btn.disabled = False, True
        target_text = state["live_timer_text"] if state["live_timer_text"] else timer_text
        target_text.color = "#FFFFFF"
        toggle_inputs(disabled=False)
        page.update()

    def reset_timer(e):
        state["timer_running"] = False
        config = get_config_durations()
        state["current_mode"] = "Focus"
        state["total_focus_remaining"] = config["Total Focus"]
        state["current_segment_elapsed"] = state["break_time_remaining"] = state["completed_sprints"] = 0
        target_text = state["live_timer_text"] if state["live_timer_text"] else timer_text
        target_text.color = "#FFFFFF"
        status_badge.value = "Status: Ready to Excel 🎯"
        start_btn.visible, stop_btn.visible, start_btn.disabled, stop_btn.disabled, skip_break_btn.visible = True, True, False, True, False
        toggle_inputs(disabled=False)
        update_timer_display()
        refresh_analytics_display()

    def toggle_inputs(disabled=False):
        focus_input.disabled = short_break_input.disabled = long_break_input.disabled = interval_input.disabled = disabled
        try: focus_input.update(); short_break_input.update(); long_break_input.update(); interval_input.update()
        except Exception: pass

    def log_hourly_metric(hour, task_name, minutes):
        data = dm.load_data()
        if "hourly_task_distribution" not in data: data["hourly_task_distribution"] = {}
        today = datetime.now().strftime("%Y-%m-%d")
        if today not in data["hourly_task_distribution"]: data["hourly_task_distribution"][today] = {str(h): {} for h in range(24)}
        hour_str = str(hour)
        if hour_str not in data["hourly_task_distribution"][today]: data["hourly_task_distribution"][today][hour_str] = {}
        if task_name not in data["hourly_task_distribution"][today][hour_str]: data["hourly_task_distribution"][today][hour_str][task_name] = 0
        data["hourly_task_distribution"][today][hour_str][task_name] += minutes
        dm.save_data(data)

    def calculate_total_daily_focus():
        data = dm.load_data()
        distribution = data.get("hourly_task_distribution", {})
        today = datetime.now().strftime("%Y-%m-%d")
        today_distribution = distribution.get(today, {})
        total = 0
        for hour_data in today_distribution.values():
            if isinstance(hour_data, dict): total += sum(hour_data.values())
        return total

    def change_page_atmosphere(e):
        state["active_theme"] = theme_dropdown.value
        colors = GLASS_THEMES[state["active_theme"]]
        
        glass_border = ft.Border(
            top=ft.BorderSide(1, colors["border"]), bottom=ft.BorderSide(1, colors["border"]),
            left=ft.BorderSide(1, colors["border"]), right=ft.BorderSide(1, colors["border"])
        )
        left_timer_card.bgcolor = colors["card_bg"]
        left_timer_card.border = glass_border
        
        right_chart_card.bgcolor = colors["card_bg"]
        right_chart_card.border = glass_border
        
        left_timer_card.update()
        right_chart_card.update()

    def toggle_chart_view(e):
        state["active_view"] = "Bars" if view_toggle.selected_index == 0 else "Clock"
        refresh_analytics_display()

    def generate_custom_bars():
        data = dm.load_data()
        distribution = data.get("hourly_task_distribution", {})
        today = datetime.now().strftime("%Y-%m-%d")
        today_distribution = distribution.get(today, {})
        target_hours = [0, 2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22]
        columns = []
        hour_totals = []

        for hour in target_hours:
            hour_dict = today_distribution.get(str(hour), {})
            total_mins = sum(hour_dict.values()) if isinstance(hour_dict, dict) else 0
            hour_totals.append(total_mins)

            total_bar_height = max(4, int((total_mins / 60) * 180))
            transparent_space_height = 180 - total_bar_height
            stacked_segments = []
            
            if total_mins > 0:
                for task_name, task_mins in hour_dict.items():
                    if task_mins > 0:
                        segment_ratio = task_mins / total_mins
                        segment_height = max(2, int(segment_ratio * total_bar_height))
                        segment_color = _get_task_color(task_name)
                        
                        stacked_segments.append(
                            ft.Container(
                                width=18,
                                height=segment_height,
                                bgcolor=segment_color,
                                border_radius=2,
                                tooltip=f"{hour:02d}:00 - {task_name} ({int(task_mins)}m)"
                            )
                        )
            else:
                stacked_segments.append(
                    ft.Container(width=18, height=4, bgcolor="rgba(255,255,255,0.02)", border_radius=2)
                )

            columns.append(
                ft.Column([
                    ft.Text(f"{int(total_mins)}m" if total_mins > 0 else "", size=8, color="#FFFFFF", weight=ft.FontWeight.W_500),
                    ft.Container(width=18, height=transparent_space_height, bgcolor="transparent"),
                    ft.Column(controls=stacked_segments, spacing=1, alignment=ft.MainAxisAlignment.END),
                    ft.Text(f"{hour:02d}", size=9, color="#FFFFFF", weight=ft.FontWeight.BOLD)
                ], spacing=2, horizontal_alignment=ft.CrossAxisAlignment.CENTER)
            )

        # AVG reference bar — always rendered, in every view, so the day's
        # average load per sampled hour is visible alongside the real bars.
        avg_mins = (sum(hour_totals) / len(hour_totals)) if hour_totals else 0
        avg_bar_height = max(4, int((avg_mins / 60) * 180))
        avg_transparent_height = 180 - avg_bar_height
        avg_border = ft.Border(
            top=ft.BorderSide(1, "#FFD54F"), bottom=ft.BorderSide(1, "#FFD54F"),
            left=ft.BorderSide(1, "#FFD54F"), right=ft.BorderSide(1, "#FFD54F")
        )

        columns.append(
            ft.Column([
                ft.Text(f"{int(avg_mins)}m" if avg_mins > 0 else "", size=8, color="#FFD54F", weight=ft.FontWeight.W_500),
                ft.Container(width=18, height=avg_transparent_height, bgcolor="transparent"),
                ft.Container(
                    width=18,
                    height=avg_bar_height,
                    bgcolor="rgba(255,213,79,0.18)",
                    border_radius=2,
                    border=avg_border,
                    tooltip=f"Average across sampled hours: {int(avg_mins)}m"
                ),
                ft.Text("AVG", size=9, color="#FFD54F", weight=ft.FontWeight.BOLD)
            ], spacing=2, horizontal_alignment=ft.CrossAxisAlignment.CENTER)
        )
            
        return ft.Row(controls=columns, alignment=ft.MainAxisAlignment.SPACE_BETWEEN, expand=True)

    def build_dynamic_legend():
        data = dm.load_data()
        distribution = data.get("hourly_task_distribution", {})
        today = datetime.now().strftime("%Y-%m-%d")
        today_distribution = distribution.get(today, {})
        task_totals = {}
        for hour_data in today_distribution.values():
            if isinstance(hour_data, dict):
                for task, mins in hour_data.items(): task_totals[task] = task_totals.get(task, 0) + mins
        
        legend_items = []
        for task_name, total_mins in task_totals.items():
            color = _get_task_color(task_name)
            legend_items.append(
                ft.Row([
                    ft.Container(width=10, height=10, bgcolor=color, border_radius=2),
                    ft.Text(f"{task_name} ({int(total_mins)}m)", size=11, color="#FFFFFF", weight=ft.FontWeight.W_500)
                ], spacing=6, alignment=ft.MainAxisAlignment.START)
            )
        return ft.Row(controls=legend_items, alignment=ft.MainAxisAlignment.START, wrap=True, spacing=16)

    def refresh_analytics_display():
        try:
            total_time_badge.value = f"{int(calculate_total_daily_focus())}m"
            total_time_badge.update()
            
            data = dm.load_data()
            distribution = data.get("hourly_task_distribution", {})
            today = datetime.now().strftime("%Y-%m-%d")
            today_dist = distribution.get(today, {})
            
            clock_color_map = {}
            for hour_data in today_dist.values():
                if isinstance(hour_data, dict):
                    for t in hour_data.keys():
                        clock_color_map[t] = _get_task_color(t)

            if state["active_view"] == "Bars":
                chart_container_frame.content = generate_custom_bars()
                chart_title_label.value = "Chronological Linear Distribution (Hours vs Mins)"
            else:
                chart_container_frame.content = generate_precision_radial_clock(today_dist, clock_color_map)
                chart_title_label.value = "24-Hour Minute-Precision Contextual Task Clock"
                
            chart_title_label.update()
            chart_container_frame.update()
            legend_viewport_frame.content = build_dynamic_legend()
            legend_viewport_frame.update()
        except Exception: pass

    def on_task_changed(e):
        state["selected_task"] = task_dropdown.value if task_dropdown.value else "General Study"
        update_timer_display()

    # --- UI CONTROLS INITIALIZATION ---
    status_badge = ft.Text("Status: Ready to Excel 🎯", size=14, weight=ft.FontWeight.W_500, color="#FFFFFF")
    timer_text = ft.Text("25:00", size=68, weight=ft.FontWeight.BOLD, color="#FFFFFF", font_family="Courier New")
    progress_bar = ft.ProgressBar(value=0.0, color="#00FFFF", bgcolor="rgba(255,255,255,0.1)", width=320, height=6)
    
    state["live_timer_text"] = timer_text
    state["live_progress_bar"] = progress_bar

    focus_input = ft.TextField(label="Work (Min)", value="150", label_style=ft.TextStyle(color="#00FFFF"), border_color="rgba(255,255,255,0.2)", width=75, height=40, text_size=13, on_change=apply_config_changes)
    short_break_input = ft.TextField(label="Short (Min)", value="5", label_style=ft.TextStyle(color="#00FFFF"), border_color="rgba(255,255,255,0.2)", width=75, height=40, text_size=13)
    long_break_input = ft.TextField(label="Long (Min)", value="15", label_style=ft.TextStyle(color="#00FFFF"), border_color="rgba(255,255,255,0.2)", width=75, height=40, text_size=13)
    interval_input = ft.TextField(label="Interval", value="3", label_style=ft.TextStyle(color="#00FFFF"), border_color="rgba(255,255,255,0.2)", width=75, height=40, text_size=13)

    start_btn = ft.FilledButton("Start Focus", icon=ft.Icons.PLAY_ARROW_ROUNDED, style=ft.ButtonStyle(bgcolor="rgba(255,255,255,0.15)", color="#00FFFF"), disabled=state["timer_running"], on_click=start_timer)
    stop_btn = ft.FilledButton("Pause", icon=ft.Icons.PAUSE_ROUNDED, style=ft.ButtonStyle(bgcolor="rgba(255,255,255,0.15)", color="#FF1744"), disabled=not state["timer_running"], on_click=stop_timer)
    reset_btn = ft.IconButton(icon=ft.Icons.REPLAY_ROUNDED, icon_color="#FFFFFF", icon_size=24, tooltip="Reset Session Pool", on_click=reset_timer)
    skip_break_btn = ft.FilledButton("Skip Break (Resume Work)", icon=ft.Icons.SKIP_NEXT_ROUNDED, style=ft.ButtonStyle(bgcolor="#00FFFF", color="#11151D"), visible=False, on_click=skip_break_clicked)

    data_now = dm.load_data()
    db_tasks = data_now.get("tasks", [])
    task_options = [ft.dropdown.Option("General Study")] + [ft.dropdown.Option(t["title"]) for t in db_tasks if not t["completed"]]
    
    task_dropdown = ft.Dropdown(label="Link Focus Session to Objective", label_style=ft.TextStyle(color="#00FFFF"), value="General Study", options=task_options, border_color="rgba(255,255,255,0.2)", width=340, on_select=on_task_changed)

    # Restore the previously selected task (survives tab switches). If the
    # remembered task no longer exists as a valid option (e.g. it was
    # completed/removed from the DB), fall back safely to General Study.
    valid_task_keys = [opt.key for opt in task_options]
    if state["selected_task"] in valid_task_keys:
        task_dropdown.value = state["selected_task"]
    else:
        state["selected_task"] = "General Study"
        task_dropdown.value = "General Study"

    theme_dropdown = ft.Dropdown(label="Customize Glass Tint", label_style=ft.TextStyle(color="#00FFFF"), value=state["active_theme"], options=[ft.dropdown.Option(t) for t in GLASS_THEMES.keys()], border_color="rgba(255,255,255,0.2)", width=340, on_select=change_page_atmosphere)

    view_toggle = ft.CupertinoSegmentedButton(
        controls=[
            ft.Text("Bar Timeline View", size=13, weight=ft.FontWeight.W_600, width=130, text_align=ft.TextAlign.CENTER),
            ft.Text("Precision Clock View", size=13, weight=ft.FontWeight.W_600, width=140, text_align=ft.TextAlign.CENTER)
        ], 
        selected_index=(0 if state["active_view"] == "Bars" else 1), 
        selected_color="#00FFFF", unselected_color="#1E2631", border_color="rgba(255,255,255,0.15)", 
        on_change=toggle_chart_view
    )
    
    total_time_badge = ft.Text(f"{int(calculate_total_daily_focus())}m", size=26, weight=ft.FontWeight.BOLD, color="#00FFFF")
    chart_title_label = ft.Text("Chronological Linear Distribution (Hours vs Mins)" if state["active_view"] == "Bars" else "24-Hour Minute-Precision Contextual Task Clock", size=12, color="#FFFFFF", weight=ft.FontWeight.W_600)
    
    distribution = data_now.get("hourly_task_distribution", {})
    today = datetime.now().strftime("%Y-%m-%d")
    today_distribution_data = distribution.get(today, {})
    
    clock_color_map = {}
    for hour_data in today_distribution_data.values():
        if isinstance(hour_data, dict):
            for t in hour_data.keys():
                clock_color_map[t] = _get_task_color(t)

    if state["active_view"] == "Bars":
        frame_content_view = generate_custom_bars()
    else:
        frame_content_view = generate_precision_radial_clock(today_distribution_data, clock_color_map)

    chart_container_frame = ft.Container(content=frame_content_view, expand=True, alignment=ft.alignment.Alignment(0, 0))
    legend_viewport_frame = ft.Container(content=build_dynamic_legend(), padding=ft.Padding(top=5, bottom=0, left=0, right=0))

    left_timer_card = create_glass_card(
        content_control=ft.Column([status_badge, timer_text, ft.Container(content=progress_bar, padding=10), ft.Row([start_btn, stop_btn, reset_btn], alignment=ft.MainAxisAlignment.CENTER, spacing=8), ft.Container(content=skip_break_btn, padding=5)], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
        theme_name=state["active_theme"], width=380, height=310
    )

    right_chart_card = create_glass_card(
        content_control=ft.Column([chart_title_label, ft.Container(height=10), chart_container_frame, ft.Divider(height=15, color="rgba(255,255,255,0.08)"), legend_viewport_frame]),
        theme_name=state["active_theme"], expand=True
    )

    if state["timer_running"]:
        start_btn.disabled, stop_btn.disabled = True, False
        selected_task = state["selected_task"]
        active_color = _get_task_color(selected_task)
        if state["current_mode"] == "Focus":
            timer_text.color = active_color
            status_badge.value = "Status: Continuing Focus Pool... 🎯"
        elif state["current_mode"] == "Short Break":
            timer_text.color = "#FF1744"
            status_badge.value = "Status: Auto Short Break! ⚡"
            start_btn.visible, stop_btn.visible, skip_break_btn.visible = False, False, True
        else:
            timer_text.color = "#D500F9"
            status_badge.value = "Status: Auto Long Break! ☕"
            start_btn.visible, stop_btn.visible, skip_break_btn.visible = False, False, True

    toggle_inputs(disabled=state["timer_running"])
    update_timer_display()

    # --- UPDATED: REMOVED THEME_DROPDOWN FROM THE LAYOUT BLOCK ARRAYS ---
    main_page_layout = ft.Row([
        ft.Column([
            ft.Text("Timer Configuration Engine", size=16, weight=ft.FontWeight.W_600, color="#00FFFF"), 
            task_dropdown, # theme_dropdown has been removed cleanly from here!
            ft.Container(
                content=ft.Row([focus_input, short_break_input, long_break_input, interval_input], spacing=8, alignment=ft.MainAxisAlignment.CENTER),
                padding=ft.Padding(top=5, right=0, bottom=5, left=0)
            ),
            left_timer_card
        ], spacing=10, width=380),
        ft.VerticalDivider(width=30, color="rgba(255,255,255,0.1)"),
        ft.Column([ft.Row([ft.Text("Performance Analytics", size=18, weight=ft.FontWeight.W_600, color="#00FFFF"), view_toggle], alignment=ft.MainAxisAlignment.SPACE_BETWEEN), ft.Container(content=ft.Row([ft.Column([ft.Text("TOTAL TRACKED TODAY", size=10, color="#FFFFFF", weight=ft.FontWeight.BOLD), total_time_badge]), ft.VerticalDivider(width=20, color="rgba(255,255,255,0.1)"), ft.Text("Real-time distributed metrics linking specific focus sessions to your task color objectives.", size=12, color="#FFFFFF", expand=True)], alignment=ft.MainAxisAlignment.SPACE_BETWEEN), bgcolor="rgba(255, 255, 255, 0.05)", padding=12, border_radius=10, blur=10, border=ft.Border(top=ft.BorderSide(1, "rgba(255,255,255,0.1)"), bottom=ft.BorderSide(1, "rgba(255,255,255,0.1)"), left=ft.BorderSide(1, "rgba(255,255,255,0.1)"), right=ft.BorderSide(1, "rgba(255,255,255,0.1)"))), right_chart_card], expand=True, spacing=10)
    ], expand=True)

    return main_page_layout