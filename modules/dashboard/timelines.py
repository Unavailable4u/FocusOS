import flet as ft
from datetime import datetime, timedelta

# --- ISOLATED GRAPH LOOKUP PALETTES ---
FOCUS_COLOR_MAP = {
    "general study": "#00FFFF",  
    "study": "#00FFFF",          
    "analog exa": "#95A5A6",     
    "esr.khuluiyhg": "#7F8C8D",
    "tyaystyryt": "#FF4081",     
    "other": "#546E7A"
}

EXPENSE_COLOR_MAP = {
    "study": "#00FFFF",          
    "food": "#FF1744",           
    "transport": "#D500F9",      
    "tyr": "#FF9100",            
    "ggh": "#FF4081",            
    "other": "#95A5A6"
}

def get_focus_color(task_name):
    if not task_name: return "#546E7A"
    return FOCUS_COLOR_MAP.get(str(task_name).strip().lower(), "#546E7A")

def get_expense_color(cat_name):
    if not cat_name: return "#95A5A6"
    return EXPENSE_COLOR_MAP.get(str(cat_name).strip().lower(), "#95A5A6")

def get_task_color(name_string):
    clean_str = str(name_string).strip().lower()
    if clean_str in EXPENSE_COLOR_MAP:
        return get_expense_color(clean_str)
    return get_focus_color(clean_str)

def clean_date_string(raw_date):
    """Ensures input dates are zero-padded to match YYYY-MM-DD exactly."""
    try:
        if isinstance(raw_date, str):
            parts = raw_date.strip().split('-')
            if len(parts) == 3:
                return f"{int(parts[0]):04d}-{int(parts[1]):02d}-{int(parts[2]):02d}"
    except Exception:
        pass
    return str(raw_date).strip()


def build_chrono_timeline_graph(current_interval, distribution_dict):
    graph_columns = []
    max_hour_total = 1
    for k, val in distribution_dict.items():
        if isinstance(val, dict): max_hour_total = max(max_hour_total, sum(val.values()))
        elif isinstance(val, (int, float)): max_hour_total = max(max_hour_total, val)

    if current_interval == "Daily": sorted_keys = [str(h) for h in range(24)]
    elif current_interval == "Weekly": sorted_keys = list(distribution_dict.keys())
    else: sorted_keys = sorted(list(distribution_dict.keys()), key=lambda x: int(x) if x.isdigit() else x)

    for axis_key in sorted_keys:
        hour_data = distribution_dict.get(axis_key, {})
        stacked_segments = []
        total_mins = sum(hour_data.values()) if isinstance(hour_data, dict) else 0

        if total_mins > 0:
            total_bar_height = max(6, int((total_mins / max_hour_total) * 135))
            transparent_space_height = 135 - total_bar_height
            for task_name, mins in sorted(hour_data.items(), key=lambda x: str(x[0]).strip().lower()):
                if mins > 0:
                    stacked_segments.append(ft.Container(width=22, height=max(4, int((mins / total_mins) * total_bar_height)), bgcolor=get_focus_color(task_name), border_radius=2, tooltip=f"{axis_key} - {task_name}: {int(mins)}m"))
        else:
            transparent_space_height = 131
            stacked_segments.append(ft.Container(width=22, height=4, bgcolor="rgba(255,255,255,0.02)", border_radius=2))

        display_label = f"{int(axis_key):02d}h" if current_interval == "Daily" else axis_key
        graph_columns.append(
            ft.Column([
                ft.Container(width=22, height=transparent_space_height, bgcolor="transparent"),
                ft.Column(controls=stacked_segments, spacing=1, alignment=ft.MainAxisAlignment.END),
                ft.Text(display_label, size=9, color="#8E9AA6", weight=ft.FontWeight.BOLD)
            ], spacing=4, horizontal_alignment=ft.CrossAxisAlignment.CENTER)
        )

    return ft.Container(
        content=ft.Column([
            ft.Row([ft.Text("Distributed Chronological Focus Timeline Grid", size=13, weight=ft.FontWeight.W_600, color="#FFFFFF"), ft.Text("Historical Density Logs", size=10, color="#45A29E")], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Divider(height=12, color="rgba(255,255,255,0.05)"),
            ft.Container(content=ft.Row(controls=graph_columns, alignment=ft.MainAxisAlignment.SPACE_BETWEEN, scroll=ft.ScrollMode.ADAPTIVE), padding=ft.Padding(5, 8, 5, 2))
        ]),
        bgcolor="#151A22", padding=16, border_radius=10,
        border=ft.Border(ft.BorderSide(1, "rgba(255,255,255,0.05)"), ft.BorderSide(1, "rgba(255,255,255,0.05)"), ft.BorderSide(1, "rgba(255,255,255,0.05)"), ft.BorderSide(1, "rgba(255,255,255,0.05)"))
    )


# --- FIXED: SOLID VARIANT EXPENSE FILTER DATA EXTRACTION ARRAY LOOP ---
def build_expense_trend_graph(target_dates, raw_expenses_list):
    # Normalize our comparison array date strings
    clean_targets = [clean_date_string(d) for d in target_dates]
    day_totals = {d: 0.0 for d in clean_targets}
    day_categories = {d: {} for d in clean_targets}
    
    for exp in raw_expenses_list:
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
            
    max_val = max(day_totals.values()) if day_totals and max(day_totals.values()) > 0 else 1.0
    columns = []

    for day_stamp in sorted(day_totals.keys()):
        total_amt = day_totals[day_stamp]
        total_bar_height = max(4, int((total_amt / max_val) * 135))
        stacked_segments = []
        cats_on_this_day = day_categories.get(day_stamp, {})
        actual_segments_height = 0
        
        if total_amt > 0 and cats_on_this_day:
            # Sorted alphabetically by lowercase string to match charts.py horizontal progress bars exactly
            for cat_name, cat_amt in sorted(cats_on_this_day.items(), key=lambda x: str(x[0]).strip().lower()):
                if cat_amt > 0:
                    segment_height = max(4, int((cat_amt / total_amt) * total_bar_height))
                    actual_segments_height += segment_height
                    segment_color = get_expense_color(cat_name)
                    stacked_segments.append(ft.Container(width=22, height=segment_height, bgcolor=segment_color, border_radius=2, tooltip=f"{cat_name}: ৳{int(cat_amt)}"))
            transparent_space_height = max(0, 135 - actual_segments_height)
        else:
            transparent_space_height = 131
            stacked_segments.append(ft.Container(width=22, height=4, bgcolor="rgba(255,255,255,0.02)", border_radius=2))
        
        try: parsed_label = datetime.strptime(day_stamp, "%Y-%m-%d").strftime("%d")
        except ValueError: parsed_label = day_stamp[-2:]

        columns.append(
            ft.Column([
                ft.Container(width=22, height=transparent_space_height, bgcolor="transparent"),
                ft.Column(controls=stacked_segments, spacing=1, alignment=ft.MainAxisAlignment.END),
                ft.Text(parsed_label, size=9, color="#8E9AA6", weight=ft.FontWeight.BOLD)
            ], spacing=4, horizontal_alignment=ft.CrossAxisAlignment.CENTER)
        )
        
    return ft.Container(
        content=ft.Column([
            ft.Row([ft.Text("Categorical Resource Expenditures Trend Timeline", size=13, weight=ft.FontWeight.W_600, color="#FFFFFF"), ft.Text("Financial Capital Burns", size=10, color="#FF9100")], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Divider(height=12, color="rgba(255,255,255,0.05)"),
            ft.Container(content=ft.Row(controls=columns, alignment=ft.MainAxisAlignment.SPACE_BETWEEN, scroll=ft.ScrollMode.ADAPTIVE), padding=ft.Padding(5, 8, 5, 2))
        ]),
        bgcolor="#151A22", padding=16, border_radius=10,
        border=ft.Border(ft.BorderSide(1, "rgba(255,255,255,0.05)"), ft.BorderSide(1, "rgba(255,255,255,0.05)"), ft.BorderSide(1, "rgba(255,255,255,0.05)"), ft.BorderSide(1, "rgba(255,255,255,0.05)"))
    )


def build_monthly_horizontal_focus_graph(raw_hourly_distribution_data):
    base_today = datetime.now()
    monthly_dates = [(base_today - timedelta(days=i)).strftime("%Y-%m-%d") for i in reversed(range(30))]
    
    SECONDS_IN_DAY = 86400
    scrollable_day_rows = []

    for day_stamp in monthly_dates:
        day_hours_data = raw_hourly_distribution_data.get(day_stamp, {})
        timeline_segments = []
        
        sorted_hours = sorted([int(h) for h in day_hours_data.keys()]) if isinstance(day_hours_data, dict) else []
        last_processed_second = 0

        for current_hour in sorted_hours:
            h_str = str(current_hour)
            tasks_dict = day_hours_data.get(h_str, {})
            if not isinstance(tasks_dict, dict): continue
            
            for task_name, duration_mins in tasks_dict.items():
                if duration_mins <= 0: continue
                
                session_start_second = current_hour * 3600
                session_duration_seconds = int(duration_mins * 60)
                session_end_second = min(SECONDS_IN_DAY, session_start_second + session_duration_seconds)
                
                if session_start_second > last_processed_second:
                    gap_duration = session_start_second - last_processed_second
                    timeline_segments.append(ft.Container(expand=gap_duration, height=14, bgcolor="rgba(255,255,255,0.03)"))
                
                actual_duration = session_end_second - max(last_processed_second, session_start_second)
                if actual_duration > 0:
                    timeline_segments.append(
                        ft.Container(
                            expand=actual_duration,
                            height=14,
                            bgcolor=get_focus_color(task_name),
                            border_radius=1,
                            tooltip=f"Date: {day_stamp}\nFocus Type: {task_name}\nDuration: {int(duration_mins)}m"
                        )
                    )
                last_processed_second = session_end_second

        if last_processed_second < SECONDS_IN_DAY:
            timeline_segments.append(ft.Container(expand=SECONDS_IN_DAY - last_processed_second, height=14, bgcolor="rgba(255,255,255,0.03)"))
        if not timeline_segments:
            timeline_segments.append(ft.Container(expand=SECONDS_IN_DAY, height=14, bgcolor="rgba(255,255,255,0.03)"))

        try: display_axis_label = datetime.strptime(day_stamp, "%Y-%m-%d").strftime("%b %d")
        except ValueError: display_axis_label = day_stamp[-5:]

        scrollable_day_rows.append(
            ft.Container(
                content=ft.Row([
                    ft.Container(content=ft.Text(display_axis_label, size=10, color="#8E9AA6", weight=ft.FontWeight.BOLD), width=55, alignment=ft.Alignment(-1, 0)),
                    ft.Row(controls=timeline_segments, spacing=0, alignment=ft.MainAxisAlignment.START, expand=True)
                ], spacing=3, alignment=ft.MainAxisAlignment.START),
                padding=ft.Padding(0, 0, 0, 4),
                border=ft.Border(bottom=ft.BorderSide(1, "rgba(255,255,255,0.06)"))
            )
        )

    static_bottom_axis_controls = [ft.Container(width=55)]
    for h in range(24):
        static_bottom_axis_controls.append(ft.Container(content=ft.Text(f"{h:02d}h", size=8, color="#8E9AA6", weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER), expand=True))

    return ft.Container(
        content=ft.Column([
            ft.Row([ft.Text("Static 30-Day Focus Horizon Matrix (High-Fidelity Chrono Map)", size=13, weight=ft.FontWeight.W_600, color="#FFFFFF"), ft.Text("Monthly Focus Map", size=10, color="#00FFFF")], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Divider(height=12, color="rgba(255,255,255,0.05)"),
            ft.Container(content=ft.Column(controls=scrollable_day_rows, spacing=4, scroll=ft.ScrollMode.ALWAYS, auto_scroll=True), height=165, padding=ft.Padding(0, 2, 5, 2)),
            ft.Divider(height=8, color="rgba(255,255,255,0.03)"),
            ft.Row(controls=static_bottom_axis_controls, spacing=0, alignment=ft.MainAxisAlignment.START)
        ]),
        bgcolor="#151A22", padding=16, border_radius=10,
        border=ft.Border(ft.BorderSide(1, "rgba(255,255,255,0.05)"), ft.BorderSide(1, "rgba(255,255,255,0.05)"), ft.BorderSide(1, "rgba(255,255,255,0.05)"), ft.BorderSide(1, "rgba(255,255,255,0.05)"))
    )