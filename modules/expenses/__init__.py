import flet as ft
import flet_charts as fch
from datetime import datetime, timedelta
from .engine import load_expense_data, save_expense_data, get_filter_date_range, get_filter_banner_string, get_filtered_expenses
from .widgets import get_cat_color, build_daily_trend_graph

def build_expenses(page: ft.Page):
    editing_index        = -1
    current_filter_mode  = "Day"
    # selected_anchor_date is ALWAYS a plain date object — never datetime
    selected_anchor_date = datetime.now().date()

    def populate_dropdowns():
        data = load_expense_data()
        cats = data.get("categories", ["Study", "Food", "Transport", "Other"])
        category_dropdown.options    = [ft.dropdown.Option(c) for c in cats]
        manage_cat_dropdown.options  = [ft.dropdown.Option(c) for c in cats]
        if cats:
            if category_dropdown.value   not in cats: category_dropdown.value   = cats[0]
            if manage_cat_dropdown.value not in cats: manage_cat_dropdown.value = cats[0]

    # ── FILTER DATE PICKER (bottom section) ──────────────────────────────────
    # Same UTC-midnight fix as dashboard: store on on_change, apply on on_dismiss.
    _pending_anchor = {"value": None}

    def handle_anchor_date_change(e):
        if e.control.value:
            _pending_anchor["value"] = e.control.value

    def handle_anchor_date_dismiss(e):
        nonlocal selected_anchor_date
        raw = _pending_anchor["value"]
        if raw is None:
            return
        # Normalise: get plain date and add 1 day to correct Flet UTC-midnight shift
        if hasattr(raw, "date") and callable(raw.date):
            picked = raw.date() + timedelta(days=1)
        else:
            picked = raw + timedelta(days=1)
        selected_anchor_date = picked
        refresh_expense_view()
        _pending_anchor["value"] = None

    anchor_picker_dialog = ft.DatePicker(
        first_date=datetime(2020, 1, 1), last_date=datetime(2030, 12, 31),
        on_change=handle_anchor_date_change,
        on_dismiss=handle_anchor_date_dismiss,
    )
    if anchor_picker_dialog not in page.overlay:
        page.overlay.append(anchor_picker_dialog)

    def trigger_anchor_calendar(e):
        anchor_picker_dialog.open = True
        page.update()

    # ── ENTRY DATE PICKER (log transaction form) ─────────────────────────────
    _pending_entry = {"value": None}

    def handle_entry_date_change(e):
        if e.control.value:
            _pending_entry["value"] = e.control.value

    def handle_entry_date_dismiss(e):
        raw = _pending_entry["value"]
        if raw is None:
            return
        if hasattr(raw, "date") and callable(raw.date):
            picked = raw.date() + timedelta(days=1)
        else:
            picked = raw + timedelta(days=1)
        expense_date_input.value = picked.strftime("%Y-%m-%d")
        try: expense_date_input.update()
        except Exception: pass
        _pending_entry["value"] = None

    entry_picker_dialog = ft.DatePicker(
        first_date=datetime(2020, 1, 1), last_date=datetime(2030, 12, 31),
        on_change=handle_entry_date_change,
        on_dismiss=handle_entry_date_dismiss,
    )
    if entry_picker_dialog not in page.overlay:
        page.overlay.append(entry_picker_dialog)

    def trigger_entry_calendar(e):
        entry_picker_dialog.open = True
        page.update()

    # ── FILTER MODE & NAVIGATION ─────────────────────────────────────────────
    def filter_mode_shifted(e):
        nonlocal current_filter_mode
        idx = e.control.selected_index
        current_filter_mode = "Day" if idx == 0 else ("Week" if idx == 1 else "Month")
        refresh_expense_view()

    def step_backward(e):
        nonlocal selected_anchor_date
        # FIX: no restriction on going to past dates — user should be able to
        # navigate backwards freely to review old records.
        if current_filter_mode == "Day":
            selected_anchor_date -= timedelta(days=1)
        elif current_filter_mode == "Week":
            selected_anchor_date -= timedelta(days=7)
        else:
            selected_anchor_date -= timedelta(days=30)
        refresh_expense_view()

    def step_forward(e):
        nonlocal selected_anchor_date
        if current_filter_mode == "Day":
            selected_anchor_date += timedelta(days=1)
        elif current_filter_mode == "Week":
            selected_anchor_date += timedelta(days=7)
        else:
            selected_anchor_date += timedelta(days=30)
        refresh_expense_view()

    # ── LOG TRANSACTION ───────────────────────────────────────────────────────
    def add_expense_clicked(e):
        nonlocal editing_index, selected_anchor_date
        if not expense_title.value or not expense_amount.value:
            return
        try:
            amt = float(expense_amount.value)
        except ValueError:
            expense_amount.error_text = "Enter a valid number"
            page.update()
            return

        saved_date_str = expense_date_input.value.strip()
        # Validate the date string before saving
        try:
            datetime.strptime(saved_date_str, "%Y-%m-%d")
        except ValueError:
            saved_date_str = datetime.now().strftime("%Y-%m-%d")
            expense_date_input.value = saved_date_str

        data = load_expense_data()
        if "expenses" not in data:
            data["expenses"] = []

        if editing_index == -1:
            data["expenses"].append({
                "title":    expense_title.value,
                "amount":   amt,
                "category": category_dropdown.value,
                "date":     saved_date_str,
            })
        else:
            if 0 <= editing_index < len(data["expenses"]):
                data["expenses"][editing_index] = {
                    "title":    expense_title.value,
                    "amount":   amt,
                    "category": category_dropdown.value,
                    "date":     saved_date_str,
                }
            editing_index      = -1
            submit_btn.text    = "Log Transaction"
            submit_btn.icon    = ft.Icons.MONETIZATION_ON_ROUNDED

        save_expense_data(data)

        expense_title.value        = ""
        expense_amount.value       = ""
        expense_amount.error_text  = None

        # FIX: sync the FILTER anchor to the date just saved so the view
        # immediately shows that day's data including the new entry.
        selected_anchor_date = datetime.strptime(saved_date_str, "%Y-%m-%d").date()
        refresh_expense_view()

    # ── CHART HELPERS ─────────────────────────────────────────────────────────
    def get_pie_sections(filtered_items, cats):
        totals = {c: 0.0 for c in cats}
        for _, exp in filtered_items:
            cat = exp.get("category", "Other")
            if cat in totals: totals[cat] += exp.get("amount", 0.0)
        overall_total = sum(totals.values())
        sections = []
        for category, total_amount in totals.items():
            if total_amount > 0:
                pct = (total_amount / overall_total) * 100 if overall_total > 0 else 0
                sections.append(fch.PieChartSection(
                    value=total_amount, title=f"{pct:.1f}%",
                    color=get_cat_color(category), radius=40,
                    title_style=ft.TextStyle(size=11, color="#FFFFFF", weight=ft.FontWeight.BOLD)
                ))
        if not sections:
            sections.append(fch.PieChartSection(value=1, title="0%", color="#243142", radius=30))
        return sections

    def build_legend_row(filtered_items, cats):
        totals = {c: 0.0 for c in cats}
        for _, exp in filtered_items:
            cat = exp.get("category", "Other")
            if cat in totals: totals[cat] += exp.get("amount", 0.0)
        legend_items = []
        for cat, total in totals.items():
            if total > 0:
                legend_items.append(ft.Row([
                    ft.Container(width=10, height=10, bgcolor=get_cat_color(cat), border_radius=2),
                    ft.Text(f"{cat} (৳{int(total)})", size=11, color="#E0E0E0")
                ], spacing=4))
        return ft.Row(controls=legend_items, alignment=ft.MainAxisAlignment.CENTER, spacing=10, wrap=True)

    def build_itemized_ledger(filtered_items, cats):
        grouped_items = {c: [] for c in cats}
        for original_idx, exp in filtered_items:
            cat = exp.get("category", "Other")
            if cat not in grouped_items: grouped_items[cat] = []
            grouped_items[cat].append((original_idx, exp))

        ledger_blocks = []
        for category, items in grouped_items.items():
            if not items: continue
            block_subtotal = sum(item[1].get("amount", 0.0) for item in items)
            item_rows = []
            for original_idx, item in items:
                def make_edit_handler(index=original_idx, t=item["title"], a=item["amount"], c=item["category"], d=item.get("date", "")):
                    def handle(e):
                        nonlocal editing_index
                        editing_index              = index
                        expense_title.value        = t
                        expense_amount.value       = str(int(a))
                        category_dropdown.value    = c
                        expense_date_input.value   = d
                        submit_btn.text            = "Save Modifications"
                        submit_btn.icon            = ft.Icons.EDIT_ROUNDED
                        page.update()
                    return handle

                def make_delete_handler(index=original_idx):
                    def handle(e):
                        data_del = load_expense_data()
                        if 0 <= index < len(data_del.get("expenses", [])):
                            data_del["expenses"].pop(index)
                            save_expense_data(data_del)
                        refresh_expense_view()
                    return handle

                item_rows.append(ft.Row([
                    ft.Row([
                        ft.Icon(ft.Icons.ARROW_RIGHT_ALT_ROUNDED, size=14, color="grey500"),
                        ft.Text(f"{item.get('title')}", size=14, color="#E0E0E0"),
                    ], spacing=4),
                    ft.Row([
                        ft.Text(f"৳{int(item.get('amount'))}", size=14, weight=ft.FontWeight.W_500, color="#66FCF1"),
                        ft.IconButton(ft.Icons.EDIT_OUTLINED,           icon_size=16, icon_color="#45A29E", on_click=make_edit_handler()),
                        ft.IconButton(ft.Icons.DELETE_OUTLINE_ROUNDED,  icon_size=16, icon_color="#FF4B4B", on_click=make_delete_handler()),
                    ], spacing=0),
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN))

            ledger_blocks.append(ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Row([ft.Icon(ft.Icons.LABEL_IMPORTANT_ROUNDED, color=get_cat_color(category), size=18), ft.Text(category, size=15, weight=ft.FontWeight.BOLD, color=get_cat_color(category))]),
                        ft.Text(f"Subtotal: ৳{int(block_subtotal)}", size=13, weight=ft.FontWeight.W_600, color="#FFFFFF"),
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    ft.Divider(height=5, color="#1F2833"),
                    ft.Column(controls=item_rows, spacing=2),
                ]),
                bgcolor="#1A212B", padding=10, border_radius=8,
                border=ft.Border(ft.BorderSide(1, "#243142"), ft.BorderSide(1, "#243142"), ft.BorderSide(1, get_cat_color(category)), ft.BorderSide(1, "#243142"))
            ))

        if not ledger_blocks:
            return ft.Container(content=ft.Text("No records found.", color="grey500"), alignment=ft.Alignment(0, 0), padding=20)
        return ft.Column(controls=ledger_blocks, spacing=10, scroll=ft.ScrollMode.ADAPTIVE)

    # ── STYLED TREND BAR CHART ────────────────────────────────────────────────
    def build_styled_trend_graph(filtered_items):
        """Improved bar chart: taller bars, category colours, rounded tops, amount labels."""
        day_totals     = {}
        day_categories = {}
        for _, exp in filtered_items:
            date_str = exp.get("date", datetime.now().strftime("%Y-%m-%d"))
            amt      = float(exp.get("amount", 0.0))
            cat      = exp.get("category", "Other")
            day_totals[date_str]     = day_totals.get(date_str, 0.0) + amt
            if date_str not in day_categories: day_categories[date_str] = {}
            day_categories[date_str][cat] = day_categories[date_str].get(cat, 0.0) + amt

        if not day_totals:
            return ft.Container(
                content=ft.Text("No data to plot", color="grey500", size=12, italic=True),
                alignment=ft.alignment.Alignment(0, 0), padding=20
            )

        max_val  = max(day_totals.values()) if day_totals else 1.0
        columns  = []
        MAX_BAR_H = 120

        for day_stamp in sorted(day_totals.keys()):
            total_amt      = day_totals[day_stamp]
            total_bar_h    = max(6, int((total_amt / max_val) * MAX_BAR_H))
            cats_today     = day_categories.get(day_stamp, {})
            segments       = []

            for cat_name, cat_amt in sorted(cats_today.items(), key=lambda x: x[0].lower()):
                if cat_amt > 0:
                    seg_h = max(4, int((cat_amt / total_amt) * total_bar_h))
                    segments.append(ft.Container(
                        width=32, height=seg_h,
                        bgcolor=get_cat_color(cat_name),
                        border_radius=ft.BorderRadius(3, 3, 0, 0) if cat_name == list(cats_today.keys())[-1] else 0,
                        tooltip=f"{cat_name}: ৳{int(cat_amt)}"
                    ))

            transparent_h = MAX_BAR_H - total_bar_h
            try:
                day_label = datetime.strptime(day_stamp, "%Y-%m-%d").strftime("%d")
            except ValueError:
                day_label = day_stamp[-2:]

            columns.append(ft.Column([
                ft.Container(width=32, height=transparent_h, bgcolor="transparent"),
                ft.Container(
                    content=ft.Text(f"৳{int(total_amt)}", size=8, color="#FFFFFF", weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER),
                    width=36, alignment=ft.alignment.Alignment(0, 0)
                ),
                ft.Column(controls=segments, spacing=0, alignment=ft.MainAxisAlignment.END),
                ft.Text(day_label, size=9, color="#8E9AA6", weight=ft.FontWeight.BOLD),
            ], spacing=2, horizontal_alignment=ft.CrossAxisAlignment.CENTER))

        return ft.Container(
            content=ft.Column([
                ft.Text("Daily Spend Breakdown", size=12, color="#8E9AA6", weight=ft.FontWeight.W_600),
                ft.Container(
                    content=ft.Row(controls=columns, spacing=6, scroll=ft.ScrollMode.ADAPTIVE),
                    padding=ft.Padding(4, 6, 4, 2)
                ),
            ], spacing=4),
            bgcolor="#11151D", border_radius=8, padding=10,
        )

    # ── CATEGORY MANAGEMENT ───────────────────────────────────────────────────
    def add_new_cat_trigger(e):
        if custom_cat_input.value:
            clean_cat = custom_cat_input.value.strip()
            data = load_expense_data()
            if "categories" not in data: data["categories"] = ["Study", "Food", "Transport", "Other"]
            if clean_cat not in data["categories"]:
                data["categories"].append(clean_cat)
                save_expense_data(data)
            custom_cat_input.value = ""
            refresh_expense_view()

    def delete_cat_trigger(e):
        if manage_cat_dropdown.value:
            target_cat = manage_cat_dropdown.value
            data = load_expense_data()
            if target_cat in data.get("categories", []):
                data["categories"].remove(target_cat)
                data["expenses"] = [exp for exp in data.get("expenses", []) if exp.get("category") != target_cat]
                save_expense_data(data)
            refresh_expense_view()

    def toggle_settings_drawer(e):
        settings_compartment.visible = not settings_compartment.visible
        settings_btn.icon_color      = "#FF4B4B" if settings_compartment.visible else "#66FCF1"
        settings_btn.icon            = ft.Icons.CLOSE_ROUNDED if settings_compartment.visible else ft.Icons.SETTINGS_SUGGEST_ROUNDED
        page.update()

    # ── MAIN REFRESH ─────────────────────────────────────────────────────────
    def refresh_expense_view():
        # FIX: removed the forced reset to today — users must be able to view
        # past dates freely. No clamping of selected_anchor_date.
        data         = load_expense_data()
        all_expenses = data.get("expenses", [])
        cats         = data.get("categories", ["Study", "Food", "Transport", "Other"])

        # selected_anchor_date is always a plain date — pass it directly
        filtered_items = get_filtered_expenses(all_expenses, current_filter_mode, selected_anchor_date)

        populate_dropdowns()
        chart_canvas.sections    = get_pie_sections(filtered_items, cats)
        filter_status_banner.value = get_filter_banner_string(current_filter_mode, selected_anchor_date)

        total_spent        = sum(item[1].get("amount", 0.0) for item in filtered_items)
        total_badge.value  = f"Selected Total: ৳{int(total_spent)}"

        legend_container.content      = build_legend_row(filtered_items, cats)
        ledger_container.content      = build_itemized_ledger(filtered_items, cats)
        trend_graph_container.content = build_styled_trend_graph(filtered_items)

        try:
            filter_status_banner.update(); total_badge.update()
            trend_graph_container.update(); chart_canvas.update()
            legend_container.update(); ledger_container.update()
        except Exception:
            pass

    # ── UI CONTROLS ───────────────────────────────────────────────────────────
    expense_title      = ft.TextField(label="Transaction Description...", label_style=ft.TextStyle(color="#45A29E"), border_color="#243142")
    expense_amount     = ft.TextField(label="Amount...",                  label_style=ft.TextStyle(color="#45A29E"), border_color="#243142", width=150)
    category_dropdown  = ft.Dropdown(label="Category",                    label_style=ft.TextStyle(color="#45A29E"), border_color="#243142", width=160)

    expense_date_input = ft.TextField(
        label="Entry Date (YYYY-MM-DD)", label_style=ft.TextStyle(color="#45A29E"),
        border_color="#243142", width=280, height=48, text_size=13,
        value=selected_anchor_date.strftime("%Y-%m-%d")
    )
    btn_entry_date_picker = ft.IconButton(
        icon=ft.Icons.CALENDAR_TODAY_ROUNDED, icon_color="#45A29E", icon_size=20,
        on_click=trigger_entry_calendar, tooltip="Select date for this entry"
    )

    custom_cat_input    = ft.TextField(label="Add New...", label_style=ft.TextStyle(color="#45A29E"), border_color="#243142", width=160)
    manage_cat_dropdown = ft.Dropdown(label="Erase...",   label_style=ft.TextStyle(color="#45A29E"), border_color="#243142", width=160)

    submit_btn          = ft.FilledButton("Log Transaction", icon=ft.Icons.MONETIZATION_ON_ROUNDED, style=ft.ButtonStyle(bgcolor="#1F2833", color="#66FCF1"), on_click=add_expense_clicked)
    total_badge         = ft.Text("Selected Total: ৳0", size=18, weight=ft.FontWeight.W_700, color="#66FCF1")
    settings_btn        = ft.IconButton(ft.Icons.SETTINGS_SUGGEST_ROUNDED, icon_color="#66FCF1", on_click=toggle_settings_drawer)
    filter_status_banner = ft.Text("", size=12, color="#45A29E", weight=ft.FontWeight.BOLD)

    interval_filter_toggle = ft.CupertinoSegmentedButton(
        controls=[
            ft.Text("Day Log",      size=11, weight=ft.FontWeight.W_600, width=70,  text_align=ft.TextAlign.CENTER),
            ft.Text("Weekly Split", size=11, weight=ft.FontWeight.W_600, width=80,  text_align=ft.TextAlign.CENTER),
            ft.Text("Monthly View", size=11, weight=ft.FontWeight.W_600, width=80,  text_align=ft.TextAlign.CENTER),
        ],
        selected_index=0, selected_color="#66FCF1", unselected_color="#1E2631",
        border_color="rgba(255,255,255,0.15)", on_change=filter_mode_shifted,
    )

    btn_calendar_picker = ft.IconButton(icon=ft.Icons.CALENDAR_MONTH_ROUNDED,        icon_color="#66FCF1", icon_size=22, on_click=trigger_anchor_calendar)
    btn_time_prev       = ft.IconButton(icon=ft.Icons.KEYBOARD_ARROW_LEFT_ROUNDED,   icon_color="#66FCF1", icon_size=22, on_click=step_backward)
    btn_time_next       = ft.IconButton(icon=ft.Icons.KEYBOARD_ARROW_RIGHT_ROUNDED,  icon_color="#66FCF1", icon_size=22, on_click=step_forward)

    settings_compartment = ft.Container(
        content=ft.Column([
            ft.Text("Manage Categories Panel", size=14, weight=ft.FontWeight.BOLD, color="#66FCF1"),
            ft.Row([custom_cat_input, ft.IconButton(ft.Icons.ADD_BOX_ROUNDED, icon_color="#66FCF1", on_click=add_new_cat_trigger)]),
            ft.Row([manage_cat_dropdown, ft.IconButton(ft.Icons.DELETE_FOREVER_ROUNDED, icon_color="#FF4B4B", on_click=delete_cat_trigger)]),
        ], spacing=8),
        bgcolor="#11151D", padding=15, border_radius=12, visible=False, width=380,
        border=ft.Border(ft.BorderSide(1, "#243142"), ft.BorderSide(1, "#243142"), ft.BorderSide(1, "#66FCF1"), ft.BorderSide(1, "#243142"))
    )

    chart_canvas          = fch.PieChart(sections=[], sections_space=3, center_space_radius=35, height=130)
    chart_frame           = ft.Container(content=chart_canvas, width=150, height=130)
    legend_container      = ft.Container(padding=5)
    ledger_container      = ft.Container(expand=True)
    trend_graph_container = ft.Container(expand=True)

    populate_dropdowns()
    refresh_expense_view()

    master_layout = ft.Row([
        ft.Column([
            ft.Row([ft.Text("Expense Allocation Console", size=18, weight=ft.FontWeight.W_600, color="#45A29E"), settings_btn], alignment=ft.MainAxisAlignment.SPACE_BETWEEN, width=380),
            ft.Container(
                content=ft.Column([
                    expense_title,
                    ft.Row([expense_amount, category_dropdown], spacing=10),
                    ft.Row([expense_date_input, btn_entry_date_picker], spacing=4, alignment=ft.MainAxisAlignment.CENTER),
                    ft.Container(content=submit_btn, padding=5),
                    ft.Divider(height=10, color="#243142"),
                    ft.Row([btn_time_prev, filter_status_banner, btn_calendar_picker, btn_time_next], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    interval_filter_toggle,
                ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                bgcolor="#151A22", padding=20, border_radius=16, width=380, height=375,
                border=ft.Border(ft.BorderSide(1, "#243142"), ft.BorderSide(1, "#243142"), ft.BorderSide(1, "#243142"), ft.BorderSide(1, "#243142"))
            ),
            settings_compartment,
        ], spacing=10, width=380),
        ft.VerticalDivider(width=30, color="#1F2833"),
        ft.Column([
            ft.Row([ft.Text("Categorical Distribution Engine", size=18, weight=ft.FontWeight.W_600, color="#45A29E"), total_badge], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Container(
                content=ft.Column([
                    ft.Row([chart_frame, trend_graph_container], alignment=ft.MainAxisAlignment.SPACE_BETWEEN, spacing=15),
                    legend_container,
                    ft.Text("Itemized Ledger Summary", size=14, weight=ft.FontWeight.W_600, color="#8E9AA6"),
                    ft.Divider(height=10, color="#243142"),
                    ledger_container,
                ], expand=True, spacing=5),
                padding=20, bgcolor="#151A22", border_radius=16, expand=True,
                border=ft.Border(ft.BorderSide(1, "#243142"), ft.BorderSide(1, "#243142"), ft.BorderSide(1, "#243142"), ft.BorderSide(1, "#243142"))
            ),
        ], expand=True, spacing=10),
    ], expand=True)

    return master_layout