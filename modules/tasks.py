import flet as ft
import sys
import os
import csv
from datetime import datetime

try:
    import data_manager as dm
except ModuleNotFoundError:
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    import data_manager as dm

def build_tasks(page: ft.Page):
    editing_task_id = -1
    expanded_comments = {}

    QUADRANT_CONFIGS = {
        1: {"label": "Urgent & Important", "color": "#FF4B4B"},      # Red
        2: {"label": "Important, Not Urgent", "color": "#66FCF1"},   # Cyan
        3: {"label": "Urgent, Not Important", "color": "#FF9800"},   # Orange
        4: {"label": "Backlog / Eliminate", "color": "#95A5A6"}      # Slate Gray
    }

    def get_task_invested_time(task_title):
        data = dm.load_data()
        distribution = data.get("hourly_task_distribution", {})
        total_minutes = 0
        for date_str, hours_dict in distribution.items():
            if isinstance(hours_dict, dict):
                for hour_str, tasks_dict in hours_dict.items():
                    if isinstance(tasks_dict, dict):
                        total_minutes += tasks_dict.get(task_title, 0)
        return int(total_minutes)

    def format_total_time(total_minutes):
        if total_minutes == 0:
            return "0m"
        hours = total_minutes // 60
        mins = total_minutes % 60
        if hours > 0:
            return f"{hours}h {mins}m" if mins > 0 else f"{hours}h"
        return f"{mins}m"

    def export_tasks_csv(e):
        data = dm.load_data()
        tasks = data.get("tasks", [])
        desktop_dir = os.path.expanduser("~/Desktop")
        try:
            os.makedirs(desktop_dir, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filepath = os.path.join(desktop_dir, f"focusos_export_{timestamp}.csv")
            with open(filepath, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["ID", "Title", "Quadrant", "Completed", "Due Date", "Comment", "Invested Minutes"])
                for task in tasks:
                    writer.writerow([
                        task.get("id", ""),
                        task.get("title", ""),
                        task.get("quadrant", ""),
                        task.get("completed", False),
                        task.get("due_date", "") or "",
                        task.get("comment", "") or "",
                        get_task_invested_time(task.get("title", "")),
                    ])
            export_feedback.value = f"Exported {len(tasks)} task(s) to {filepath}"
            export_feedback.color = "#81C784"
        except Exception as ex:
            export_feedback.value = f"Export failed: {ex}"
            export_feedback.color = "#FF4B4B"
        page.update()

    def add_task_clicked(e):
        nonlocal editing_task_id
        if not task_input.value:
            return
        
        title = task_input.value
        quadrant = int(quadrant_dropdown.value if quadrant_dropdown.value else 1)
        comment_text = comment_input.value.strip() if comment_input.value else ""
        due_date_text = due_date_display.value.strip() if due_date_display.value else ""
        due_date_value = due_date_text if due_date_text else None
        
        if editing_task_id == -1:
            dm.add_task(title, quadrant, due_date=due_date_value)
            if comment_text:
                data = dm.load_data()
                tasks = data.get("tasks", [])
                if tasks:
                    tasks[-1]["comment"] = comment_text
                    dm.save_data(data)
        else:
            data = dm.load_data()
            tasks = data.get("tasks", [])
            for task in tasks:
                if task.get("id") == editing_task_id:
                    task["title"] = title
                    task["quadrant"] = quadrant
                    task["comment"] = comment_text
                    task["due_date"] = due_date_value
                    break
            dm.save_data(data)
            
            editing_task_id = -1
            submit_btn.text = "Add to Matrix"
            submit_btn.icon = ft.Icons.ADD_ROUNDED

        task_input.value = ""
        comment_input.value = ""
        due_date_display.value = ""
        refresh_matrix_boards(is_initial_load=False)

    def make_task_tile(task, config, compact_view=False):
        task_id = task["id"]
        task_title = task.get("title", "Untitled Task")
        has_comment = "comment" in task and task["comment"]
        invested_mins = get_task_invested_time(task_title)
        due_date_str = task.get("due_date")
        today_str = datetime.now().strftime("%Y-%m-%d")
        is_overdue = bool(due_date_str) and not task["completed"] and due_date_str < today_str

        if compact_view:
            status_label = f"{invested_mins}m" if invested_mins > 0 else ""
        else:
            if task["completed"]:
                status_label = f"Completed ({invested_mins}m)"
            elif invested_mins > 0:
                status_label = f"Ongoing ({invested_mins}m)"
            else:
                status_label = "Not Started"
            if due_date_str:
                status_label = f"{status_label} • Due {due_date_str}" if status_label else f"Due {due_date_str}"

        def make_edit_handler(t_id=task_id, title=task_title, quad=task.get("quadrant", 1), comm=task.get("comment", ""), due=task.get("due_date", "")):
            def handle(e):
                nonlocal editing_task_id
                editing_task_id = t_id
                task_input.value = title
                quadrant_dropdown.value = str(quad)
                comment_input.value = comm
                due_date_display.value = due if due else ""
                submit_btn.text = "Save Modifications"
                submit_btn.icon = ft.Icons.EDIT_ROUNDED
                page.update()
            return handle

        def make_delete_handler(t_id=task_id):
            def handle(e):
                data_del = dm.load_data()
                data_del["tasks"] = [t for t in data_del.get("tasks", []) if t.get("id") != t_id]
                dm.save_data(data_del)
                refresh_matrix_boards(is_initial_load=False)
            return handle

        def make_toggle_handler(t_id=task_id):
            def handle(e):
                dm.toggle_task_completion(t_id)
                refresh_matrix_boards(is_initial_load=False)
            return handle

        def make_comment_handler(t_id=task_id):
            def handle(e):
                expanded_comments[t_id] = not expanded_comments.get(t_id, False)
                refresh_matrix_boards(is_initial_load=False)
            return handle

        bulletin_icon = ft.IconButton(
            icon=ft.Icons.CHECK_CIRCLE_ROUNDED if task["completed"] else ft.Icons.RADIO_BUTTON_UNCHECKED_ROUNDED,
            icon_color="#81C784" if task["completed"] else config["color"],
            icon_size=16,
            on_click=make_toggle_handler()
        )

        trailing_controls = ft.Row([
            ft.IconButton(ft.Icons.COMMENT_ROUNDED, icon_size=16, icon_color="#45A29E" if not task["completed"] else "rgba(255,255,255,0.1)", on_click=make_comment_handler()) if has_comment and not compact_view else ft.Container(),
            ft.IconButton(ft.Icons.EDIT_OUTLINED, icon_size=16, icon_color="#45A29E", on_click=make_edit_handler()),
            ft.IconButton(ft.Icons.DELETE_OUTLINE_ROUNDED, icon_size=16, icon_color="#FF4B4B", on_click=make_delete_handler()),
        ], spacing=0, alignment=ft.MainAxisAlignment.END, width=110 if (has_comment and not compact_view) else (80 if not compact_view else 60))

        text_decor = ft.TextDecoration.LINE_THROUGH if (task["completed"] and not compact_view) else None

        title_row_controls = [
            ft.Text(
                task_title, 
                size=13 if compact_view else 14, 
                color="grey500" if task["completed"] else ("#FF4B4B" if is_overdue else "#FFFFFF"),
                style=ft.TextStyle(decoration=text_decor),
                expand=True
            )
        ]
        if is_overdue:
            title_row_controls.append(
                ft.Container(
                    content=ft.Text("⚠ Overdue", size=9, weight=ft.FontWeight.BOLD, color="#FF4B4B"),
                    padding=ft.Padding(left=6, right=6, top=1, bottom=1),
                    bgcolor="rgba(255,75,75,0.12)",
                    border_radius=4
                )
            )

        task_details = ft.Row([
            ft.Column([
                ft.Row(title_row_controls, spacing=6, expand=True),
                ft.Text(status_label, size=10 if compact_view else 11, color="grey600" if task["completed"] else "#8E9AA6") if status_label else ft.Container()
            ], spacing=1, expand=True),
            trailing_controls
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN, expand=True)

        core_item_row = ft.Row([bulletin_icon, task_details], alignment=ft.MainAxisAlignment.START, expand=True)

        if has_comment and expanded_comments.get(task_id, False) and not compact_view:
            return ft.Column([
                core_item_row,
                ft.Container(
                    content=ft.Text(task["comment"], size=12, color="#8E9AA6", italic=True),
                    padding=ft.Padding(top=0, right=10, bottom=6, left=44)
                ),
                ft.Divider(height=1, color="rgba(255,255,255,0.03)")
            ], spacing=2)
        
        return ft.Column([core_item_row, ft.Divider(height=1, color="rgba(255,255,255,0.03)")], spacing=0)

    def build_priority_block(quad_num, config):
        data = dm.load_data()
        tasks = data.get("tasks", [])
        quad_tasks = [t for t in tasks if t.get("quadrant") == quad_num]
        
        if not quad_tasks:
            return ft.Container()

        total_minutes = 0
        item_rows = []
        for task in quad_tasks:
            total_minutes += get_task_invested_time(task.get("title", ""))
            item_rows.append(make_task_tile(task, config, compact_view=False))

        readable_time = format_total_time(total_minutes)

        return ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Row([
                        ft.Icon(ft.Icons.LABEL_IMPORTANT_ROUNDED, color=config["color"], size=18),
                        ft.Text(config["label"], size=14, weight=ft.FontWeight.BOLD, color=config["color"]),
                    ]),
                    ft.Text(f"Total: {len(quad_tasks)} ({readable_time})", size=11, color="grey500")
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                ft.Divider(height=8, color="#1F2833"),
                ft.Column(controls=item_rows, spacing=4)
            ]),
            bgcolor="#151A22", padding=12, border_radius=10,
            border=ft.Border(top=ft.BorderSide(2, config["color"]), bottom=ft.BorderSide(1, "#243142"), left=ft.BorderSide(1, "#243142"), right=ft.BorderSide(1, "#243142"))
        )

    def build_compact_status_block(title_text, filter_type, accent_color):
        data = dm.load_data()
        tasks = data.get("tasks", [])
        
        filtered_items = []
        total_minutes = 0
        
        for task in tasks:
            invested = get_task_invested_time(task.get("title", ""))
            quad_num = task.get("quadrant", 1)
            config = QUADRANT_CONFIGS.get(quad_num, QUADRANT_CONFIGS[1])
            
            is_match = False
            if filter_type == "completed" and task["completed"]:
                is_match = True
            elif filter_type == "ongoing" and not task["completed"] and invested > 0:
                is_match = True
            elif filter_type == "not_started" and not task["completed"] and invested == 0:
                is_match = True

            if is_match:
                total_minutes += invested
                filtered_items.append(make_task_tile(task, config, compact_view=True))

        if not filtered_items:
            return ft.Container()

        readable_time = format_total_time(total_minutes)

        return ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Icon(ft.Icons.GRID_VIEW_ROUNDED, color=accent_color, size=16),
                    # FIXED: Changed from high-order em-dash to standard standard layout colon separator
                    ft.Text(f"{title_text} ({len(filtered_items)}) : {readable_time}", size=14, weight=ft.FontWeight.BOLD, color=accent_color),
                ], spacing=8),
                ft.Divider(height=8, color="#1F2833"),
                ft.Column(controls=filtered_items, spacing=2)
            ]),
            bgcolor="#11151D", padding=12, border_radius=10,
            border=ft.Border(top=ft.BorderSide(1, accent_color), bottom=ft.BorderSide(1, "#243142"), left=ft.BorderSide(1, "#243142"), right=ft.BorderSide(1, "#243142"))
        )

    def refresh_matrix_boards(is_initial_load=True):
        left_blocks = []
        for q_num in [1, 2, 3, 4]:
            block = build_priority_block(q_num, QUADRANT_CONFIGS[q_num])
            if not isinstance(block, ft.Container) or block.content:
                left_blocks.append(block)
        
        if not left_blocks:
            left_pane.content = ft.Container(content=ft.Text("No active records inside priority matrix.", color="grey500", italic=True), alignment=ft.alignment.Alignment(0,0))
        else:
            left_pane.content = ft.Column(controls=left_blocks, spacing=12, scroll=ft.ScrollMode.ADAPTIVE)

        right_blocks = [
            build_compact_status_block("Not Started Status Logs", "not_started", "#95A5A6"),
            build_compact_status_block("Ongoing Work Processes", "ongoing", "#66FCF1"),
            build_compact_status_block("Completed Tasks Ledger", "completed", "#81C784")
        ]
        right_blocks = [b for b in right_blocks if b.content]
        
        if not right_blocks:
            right_pane.content = ft.Container(content=ft.Text("No records log distributions.", color="grey500", italic=True), alignment=ft.alignment.Alignment(0,0))
        else:
            right_pane.content = ft.Column(controls=right_blocks, spacing=12, scroll=ft.ScrollMode.ADAPTIVE)

        if not is_initial_load:
            page.update()

    # --- UI CONTROLS ENGINE ---
    task_input = ft.TextField(label="Create New Task Objective...", label_style=ft.TextStyle(color="#45A29E"), border_color="#243142", expand=True)
    comment_input = ft.TextField(label="Add Optional Comment / Note...", label_style=ft.TextStyle(color="#45A29E"), border_color="#243142", width=260)
    quadrant_dropdown = ft.Dropdown(
        label="Assign Priority Quadrant", label_style=ft.TextStyle(color="#45A29E"), border_color="#243142", value="1",
        options=[
            ft.dropdown.Option("1", "Q1: Urgent & Important"), ft.dropdown.Option("2", "Q2: Important, Not Urgent"),
            ft.dropdown.Option("3", "Q3: Urgent, Not Important"), ft.dropdown.Option("4", "Q4: Backlog / Eliminate"),
        ], width=240
    )

    def handle_date_picked(e):
        if due_date_picker.value:
            due_date_display.value = due_date_picker.value.strftime("%Y-%m-%d")
            page.update()

    def clear_due_date(e):
        due_date_display.value = ""
        page.update()

    due_date_picker = ft.DatePicker(
        first_date=datetime(2020, 1, 1),
        last_date=datetime(2100, 12, 31),
        on_change=handle_date_picked,
    )
    page.overlay.append(due_date_picker)

    due_date_display = ft.TextField(
        label="Due Date (optional)", label_style=ft.TextStyle(color="#45A29E"),
        border_color="#243142", width=150, read_only=True, value=""
    )

    due_date_picker_row = ft.Row([
        due_date_display,
        ft.IconButton(ft.Icons.CALENDAR_MONTH_ROUNDED, icon_color="#45A29E", tooltip="Pick due date", on_click=lambda e: due_date_picker.pick_date()),
        ft.IconButton(ft.Icons.CLOSE_ROUNDED, icon_color="#8E9AA6", icon_size=16, tooltip="Clear due date", on_click=clear_due_date),
    ], spacing=0)

    submit_btn = ft.FilledButton("Add to Matrix", icon=ft.Icons.ADD_ROUNDED, style=ft.ButtonStyle(bgcolor="#1F2833", color="#66FCF1"), on_click=add_task_clicked)
    export_btn = ft.IconButton(ft.Icons.DOWNLOAD_ROUNDED, icon_color="#45A29E", tooltip="Export tasks to CSV", on_click=export_tasks_csv)
    export_feedback = ft.Text("", size=11, color="#8E9AA6")

    left_pane = ft.Container(expand=True, padding=2)
    right_pane = ft.Container(width=420, padding=2)

    refresh_matrix_boards(is_initial_load=True)

    dual_view_matrix = ft.Row([
        left_pane,
        ft.VerticalDivider(width=20, thickness=1, color="rgba(255,255,255,0.05)"),
        right_pane
    ], expand=True)

    return ft.Column([
        ft.Row([
            ft.Text("Itemized Matrix Priority Ledger Summary", size=22, weight=ft.FontWeight.W_600, color="#45A29E"),
            export_btn,
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
        ft.Row([task_input, comment_input, quadrant_dropdown, due_date_picker_row, submit_btn], spacing=10),
        export_feedback,
        ft.Divider(height=15, color="#243142"),
        dual_view_matrix
    ], expand=True)