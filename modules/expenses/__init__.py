import flet as ft
import flet_charts as fch
import os
from datetime import datetime, timedelta
import data_manager as dm
from .engine import load_expense_data, save_expense_data, get_filter_date_range, get_filter_banner_string, get_filtered_expenses
from modules.color_palette import get_expense_color
from modules.file_dialogs import pick_save_path   # ← P4-T3

# Budget progress bar colours
_BUDGET_OK      = "#00E676"   # green  — under 80 %
_BUDGET_WARNING = "#FF9100"   # orange — 80–99 %
_BUDGET_OVER    = "#FF1744"   # red    — 100 %+


def _budget_bar_color(ratio: float) -> str:
    if ratio >= 1.0:
        return _BUDGET_OVER
    if ratio >= 0.8:
        return _BUDGET_WARNING
    return _BUDGET_OK


def build_expenses(page: ft.Page, initial_query: str = None):
    editing_index        = -1
    current_filter_mode  = "Day"
    selected_anchor_date = datetime.now().date()
    currency_symbol      = dm.get_currency_symbol()
    search_query          = (initial_query or "").strip().lower()

    def populate_dropdowns():
        data = load_expense_data()
        cats = data.get("categories", ["Study", "Food", "Transport", "Other"])
        category_dropdown.options    = [ft.dropdown.Option(c) for c in cats]
        manage_cat_dropdown.options  = [ft.dropdown.Option(c) for c in cats]
        if cats:
            if category_dropdown.value    not in cats: category_dropdown.value    = cats[0]
            if manage_cat_dropdown.value  not in cats: manage_cat_dropdown.value  = cats[0]
        # Keep the inline budget field's value/label in sync with whichever
        # category is currently selected in manage_cat_dropdown.
        _sync_budget_field_to_selected_cat()

    # ── FILTER DATE PICKER ────────────────────────────────────────────────────
    _pending_anchor = {"value": None}

    def handle_anchor_date_change(e):
        if e.control.value:
            _pending_anchor["value"] = e.control.value

    def handle_anchor_date_dismiss(e):
        nonlocal selected_anchor_date
        raw = _pending_anchor["value"]
        if raw is None:
            return
        picked = (raw.date() + timedelta(days=1)
                  if hasattr(raw, "date") and callable(raw.date)
                  else raw + timedelta(days=1))
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

    # ── ENTRY DATE PICKER ─────────────────────────────────────────────────────
    _pending_entry = {"value": None}

    def handle_entry_date_change(e):
        if e.control.value:
            _pending_entry["value"] = e.control.value

    def handle_entry_date_dismiss(e):
        raw = _pending_entry["value"]
        if raw is None:
            return
        picked = (raw.date() + timedelta(days=1)
                  if hasattr(raw, "date") and callable(raw.date)
                  else raw + timedelta(days=1))
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

    # ── P4-T3: export via user-chosen save location ───────────────────────────
    def export_expenses_csv(e):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        suggested = f"focusos_expenses_{timestamp}.csv"

        def on_save_result(path: str | None) -> None:
            if not path:
                return  # user cancelled — silent no-op

            if not path.lower().endswith(".csv"):
                path += ".csv"

            ok = dm.export_expenses_csv(path)

            if ok:
                count = len(load_expense_data().get("expenses", []))
                msg   = f"Exported {count} expense(s) → {path}"
                color = "#81C784"
            else:
                msg   = f"Export failed — could not write to {path}"
                color = "#FF4B4B"

            page.open(ft.SnackBar(
                content=ft.Text(msg, color="#FFFFFF"),
                bgcolor=color,
                duration=4000,
            ))
            page.update()

        pick_save_path(
            page,
            on_result=on_save_result,
            suggested_name=suggested,
            allowed_extensions=["csv"],
        )
    # ─────────────────────────────────────────────────────────────────────────

    # ── FILTER MODE & NAVIGATION ──────────────────────────────────────────────
    def filter_mode_shifted(e):
        nonlocal current_filter_mode
        idx = e.control.selected_index
        current_filter_mode = "Day" if idx == 0 else ("Week" if idx == 1 else "Month")
        refresh_expense_view()

    def step_backward(e):
        nonlocal selected_anchor_date
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
            editing_index   = -1
            submit_btn.text = "Log Transaction"
            submit_btn.icon = ft.Icons.MONETIZATION_ON_ROUNDED

        save_expense_data(data)
        expense_title.value       = ""
        expense_amount.value      = ""
        expense_amount.error_text = None
        selected_anchor_date = datetime.strptime(saved_date_str, "%Y-%m-%d").date()
        refresh_expense_view()

    # ── BUDGET HELPERS ────────────────────────────────────────────────────────
    # NOTE: per-category budgets live in goals["category_budgets"] — this is
    # the single source of truth across the whole app (set_category_budget /
    # get_category_budget in data_manager.py). The legacy data["budgets"]
    # dict is no longer read or written here; data_manager.initialize_db()
    # migrates any old values over automatically.

    def _sync_budget_field_to_selected_cat():
        """Fills the inline budget field with the currently-set budget
        (if any) for whichever category is selected in manage_cat_dropdown."""
        cat = manage_cat_dropdown.value
        if not cat:
            inline_budget_input.value = ""
            inline_budget_input.label = f"Budget ({currency_symbol})"
            return
        existing = dm.get_category_budget(cat)
        inline_budget_input.value = str(int(existing)) if existing else ""
        inline_budget_input.label = f"Budget for {cat} ({currency_symbol})"

    def manage_cat_dropdown_changed(e):
        _sync_budget_field_to_selected_cat()
        try:
            inline_budget_input.update()
        except Exception:
            pass

    def save_budget_clicked(e):
        """Saves the budget entered in the inline field for whichever
        category is selected in manage_cat_dropdown."""
        cat = manage_cat_dropdown.value
        raw = (inline_budget_input.value or "").strip()
        if not cat or not raw:
            return
        try:
            amt = float(raw)
        except ValueError:
            return
        dm.set_category_budget(cat, amt)
        refresh_expense_view()

    def _get_current_month_spent_by_cat() -> dict:
        """
        Returns {category: total_amount} for expenses recorded in the
        current calendar month only — budgets are monthly, so the progress
        bars must compare against this month's spend, not all-time totals.
        """
        month_prefix = datetime.now().strftime("%Y-%m")
        data = load_expense_data()
        totals = {}
        for exp in data.get("expenses", []):
            if str(exp.get("date", "")).startswith(month_prefix):
                cat = exp.get("category", "Other")
                totals[cat] = totals.get(cat, 0.0) + float(exp.get("amount", 0.0))
        return totals

    def build_budget_progress_panel(cats: list, category_budgets: dict, month_totals: dict, currency_symbol: str):
        """
        For every category that has a budget set (in goals["category_budgets"]),
        render a labelled progress bar showing this month's spend vs budget.
        """
        rows = []
        for cat in cats:
            budget = category_budgets.get(cat, 0)
            if budget <= 0:
                continue
            spent  = month_totals.get(cat, 0.0)
            ratio  = min(spent / budget, 1.0) if budget > 0 else 0.0
            color  = _budget_bar_color(spent / budget if budget > 0 else 0)
            pct    = int((spent / budget) * 100) if budget > 0 else 0

            status_text = (f"{currency_symbol}{int(spent)} / {currency_symbol}{int(budget)}  ({pct}%)"
                           + (" ⚠ OVER BUDGET" if spent > budget else ""))

            rows.append(ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Container(width=10, height=10,
                                     bgcolor=get_expense_color(cat), border_radius=2),
                        ft.Text(cat, size=12, color="#E0E0E0",
                                weight=ft.FontWeight.W_600, expand=True),
                        ft.Text(status_text, size=11,
                                color=color, weight=ft.FontWeight.W_500),
                    ], spacing=6),
                    ft.ProgressBar(
                        value=ratio,
                        color=color,
                        bgcolor="rgba(255,255,255,0.08)",
                        height=6,
                        border_radius=3,
                    ),
                ], spacing=5),
                padding=ft.Padding(0, 4, 0, 4),
            ))

        if not rows:
            return ft.Container(
                content=ft.Text(
                    "No budgets set yet. Pick a category above and add one.",
                    size=11, color="grey500", italic=True,
                ),
                padding=ft.Padding(4, 6, 4, 6),
            )

        return ft.Column(controls=rows, spacing=4)

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
                    color=get_expense_color(category), radius=40,
                    title_style=ft.TextStyle(size=11, color="#FFFFFF",
                                              weight=ft.FontWeight.BOLD)
                ))
        if not sections:
            sections.append(fch.PieChartSection(value=1, title="0%",
                                                 color="#243142", radius=30))
        return sections

    def build_legend_row(filtered_items, cats, currency_symbol: str):
        totals = {c: 0.0 for c in cats}
        for _, exp in filtered_items:
            cat = exp.get("category", "Other")
            if cat in totals: totals[cat] += exp.get("amount", 0.0)
        items = []
        for cat, total in totals.items():
            if total > 0:
                items.append(ft.Row([
                    ft.Container(width=10, height=10,
                                 bgcolor=get_expense_color(cat), border_radius=2),
                    ft.Text(f"{cat} ({currency_symbol}{int(total)})", size=11, color="#E0E0E0"),
                ], spacing=4))
        return ft.Row(controls=items, alignment=ft.MainAxisAlignment.CENTER,
                      spacing=10, wrap=True)

    def build_itemized_ledger(filtered_items, cats, currency_symbol: str):
        grouped_items = {c: [] for c in cats}
        for original_idx, exp in filtered_items:
            cat = exp.get("category", "Other")
            if cat not in grouped_items: grouped_items[cat] = []
            grouped_items[cat].append((original_idx, exp))

        grand_total  = sum(item[1].get("amount", 0.0) for item in filtered_items)
        entry_count  = len(filtered_items)
        grand_banner = ft.Container(
            content=ft.Row([
                ft.Icon(ft.Icons.RECEIPT_LONG_ROUNDED, color="#66FCF1", size=18),
                ft.Text(
                    f"Total Expenses: {currency_symbol}{int(grand_total)}  "
                    f"({entry_count} {'entry' if entry_count == 1 else 'entries'})",
                    size=14, weight=ft.FontWeight.BOLD, color="#66FCF1",
                ),
            ], spacing=8),
            bgcolor="#0D1117",
            padding=ft.Padding(12, 8, 12, 8),
            border_radius=8,
            border=ft.Border(
                ft.BorderSide(1, "#243142"),
                ft.BorderSide(1, "#243142"),
                ft.BorderSide(1, "#243142"),
                ft.BorderSide(2, "#66FCF1"),
            ),
        )

        ledger_blocks = [grand_banner]

        for category, items in grouped_items.items():
            if not items: continue
            block_subtotal = sum(item[1].get("amount", 0.0) for item in items)
            item_rows = []

            for original_idx, item in items:
                def make_edit_handler(index=original_idx, t=item["title"],
                                      a=item["amount"], c=item["category"],
                                      d=item.get("date", "")):
                    def handle(e):
                        nonlocal editing_index
                        editing_index            = index
                        expense_title.value      = t
                        expense_amount.value     = str(int(a))
                        category_dropdown.value  = c
                        expense_date_input.value = d
                        submit_btn.text          = "Save Modifications"
                        submit_btn.icon          = ft.Icons.EDIT_ROUNDED
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
                        ft.Text(f"{currency_symbol}{int(item.get('amount'))}", size=14,
                                weight=ft.FontWeight.W_500, color="#66FCF1"),
                        ft.IconButton(ft.Icons.EDIT_OUTLINED, icon_size=16,
                                      icon_color="#45A29E", on_click=make_edit_handler()),
                        ft.IconButton(ft.Icons.DELETE_OUTLINE_ROUNDED, icon_size=16,
                                      icon_color="#FF4B4B", on_click=make_delete_handler()),
                    ], spacing=0),
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN))

            ledger_blocks.append(ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Row([
                            ft.Icon(ft.Icons.LABEL_IMPORTANT_ROUNDED,
                                    color=get_expense_color(category), size=18),
                            ft.Text(category, size=15, weight=ft.FontWeight.BOLD,
                                    color=get_expense_color(category)),
                        ]),
                        ft.Text(f"Subtotal: {currency_symbol}{int(block_subtotal)}", size=13,
                                weight=ft.FontWeight.W_600, color="#FFFFFF"),
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    ft.Divider(height=5, color="#1F2833"),
                    ft.Column(controls=item_rows, spacing=2),
                ]),
                bgcolor="#1A212B", padding=10, border_radius=8,
                border=ft.Border(
                    ft.BorderSide(1, "#243142"), ft.BorderSide(1, "#243142"),
                    ft.BorderSide(1, get_expense_color(category)), ft.BorderSide(1, "#243142"),
                ),
            ))

        if len(ledger_blocks) == 1:
            return ft.Column(controls=[
                grand_banner,
                ft.Container(content=ft.Text("No records found.", color="grey500"),
                             alignment=ft.Alignment(0, 0), padding=20),
            ], spacing=8)

        return ft.Column(controls=ledger_blocks, spacing=10,
                         scroll=ft.ScrollMode.ADAPTIVE)

    # ── STYLED TREND BAR CHART ────────────────────────────────────────────────
    def build_styled_trend_graph(filtered_items, currency_symbol: str):
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
                content=ft.Text("No data to plot", color="grey500",
                                size=12, italic=True),
                alignment=ft.alignment.Alignment(0, 0), padding=20,
            )

        show_avg = current_filter_mode in ("Week", "Month")
        avg_val  = sum(day_totals.values()) / len(day_totals) if day_totals else 0.0
        max_val  = max(day_totals.values()) if day_totals else 1.0
        if show_avg:
            max_val = max(max_val, avg_val)

        MAX_BAR_H = 120
        columns   = []

        def _make_bar_column(day_stamp, total_amt, cats_today,
                             label_text, bar_color_override=None):
            total_bar_h = max(6, int((total_amt / max_val) * MAX_BAR_H)) if max_val else 6
            segments    = []

            if bar_color_override:
                segments.append(ft.Container(
                    width=32, height=total_bar_h,
                    bgcolor=bar_color_override,
                    border_radius=ft.BorderRadius(3, 3, 0, 0),
                    tooltip=f"Daily Average: {currency_symbol}{int(total_amt)}",
                ))
            else:
                sorted_cats = sorted(cats_today.items(), key=lambda x: x[0].lower())
                last_cat    = sorted_cats[-1][0] if sorted_cats else None
                for cat_name, cat_amt in sorted_cats:
                    if cat_amt > 0:
                        seg_h = max(4, int((cat_amt / total_amt) * total_bar_h))
                        segments.append(ft.Container(
                            width=32, height=seg_h,
                            bgcolor=get_expense_color(cat_name),
                            border_radius=(ft.BorderRadius(3, 3, 0, 0)
                                          if cat_name == last_cat else 0),
                            tooltip=f"{cat_name}: {currency_symbol}{int(cat_amt)}",
                        ))

            transparent_h = MAX_BAR_H - total_bar_h
            return ft.Column([
                ft.Container(width=32, height=transparent_h, bgcolor="transparent"),
                ft.Container(
                    content=ft.Text(f"{currency_symbol}{int(total_amt)}", size=8, color="#FFFFFF",
                                    weight=ft.FontWeight.BOLD,
                                    text_align=ft.TextAlign.CENTER),
                    width=36, alignment=ft.alignment.Alignment(0, 0),
                ),
                ft.Column(controls=segments, spacing=0,
                          alignment=ft.MainAxisAlignment.END),
                ft.Text(label_text, size=9, color="#8E9AA6",
                        weight=ft.FontWeight.BOLD),
            ], spacing=2, horizontal_alignment=ft.CrossAxisAlignment.CENTER)

        for day_stamp in sorted(day_totals.keys()):
            total_amt  = day_totals[day_stamp]
            cats_today = day_categories.get(day_stamp, {})
            try:
                day_label = datetime.strptime(day_stamp, "%Y-%m-%d").strftime("%d")
            except ValueError:
                day_label = day_stamp[-2:]
            columns.append(_make_bar_column(day_stamp, total_amt, cats_today, day_label))

        if show_avg and avg_val > 0:
            columns.append(ft.Column([
                ft.Container(width=1, height=MAX_BAR_H + 20, bgcolor="#243142"),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER))
            columns.append(_make_bar_column(
                "avg", avg_val, {}, "AVG", bar_color_override="#45A29E",
            ))

        return ft.Container(
            content=ft.Column([
                ft.Text("Daily Spend Breakdown", size=12, color="#8E9AA6",
                        weight=ft.FontWeight.W_600),
                ft.Container(
                    content=ft.Row(controls=columns, spacing=6,
                                   scroll=ft.ScrollMode.ADAPTIVE),
                    padding=ft.Padding(4, 6, 4, 2),
                ),
            ], spacing=4),
            bgcolor="#11151D", border_radius=8, padding=10,
        )

    # ── CATEGORY & BUDGET MANAGEMENT ──────────────────────────────────────────
    def add_new_cat_trigger(e):
        if custom_cat_input.value:
            clean_cat = custom_cat_input.value.strip()
            data = load_expense_data()
            if "categories" not in data:
                data["categories"] = ["Study", "Food", "Transport", "Other"]
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
                data["expenses"] = [exp for exp in data.get("expenses", [])
                                    if exp.get("category") != target_cat]
                save_expense_data(data)
                # Budget cleanup goes through the same goals/category_budgets
                # path as every other budget write — keeps storage unified.
                dm.set_category_budget(target_cat, 0)
            refresh_expense_view()

    def toggle_settings_drawer(e):
        settings_compartment.visible = not settings_compartment.visible
        settings_btn.icon_color = "#FF4B4B" if settings_compartment.visible else "#66FCF1"
        settings_btn.icon = (ft.Icons.CLOSE_ROUNDED if settings_compartment.visible
                             else ft.Icons.SETTINGS_SUGGEST_ROUNDED)
        page.update()

    def handle_search_change(e):
        nonlocal search_query
        search_query = (search_field.value or "").strip().lower()
        refresh_expense_view()

    # ── MAIN REFRESH ─────────────────────────────────────────────────────────
    def refresh_expense_view():
        nonlocal currency_symbol
        currency_symbol = dm.get_currency_symbol()

        data         = load_expense_data()
        all_expenses = data.get("expenses", [])
        cats         = data.get("categories", ["Study", "Food", "Transport", "Other"])
        category_budgets = dm.get_goals().get("category_budgets", {})

        filtered_items = get_filtered_expenses(all_expenses, current_filter_mode,
                                               selected_anchor_date)
        if search_query:
            filtered_items = [
                item for item in filtered_items
                if search_query in item[1].get("title", "").lower()
            ]

        populate_dropdowns()
        chart_canvas.sections      = get_pie_sections(filtered_items, cats)
        filter_status_banner.value = get_filter_banner_string(current_filter_mode,
                                                               selected_anchor_date)

        total_spent       = sum(item[1].get("amount", 0.0) for item in filtered_items)
        total_badge.value = f"Selected Total: {currency_symbol}{int(total_spent)}"

        legend_container.content      = build_legend_row(filtered_items, cats, currency_symbol)
        ledger_container.content      = build_itemized_ledger(filtered_items, cats, currency_symbol)
        trend_graph_container.content = build_styled_trend_graph(filtered_items, currency_symbol)

        # Budget progress — uses THIS MONTH's totals (budgets are monthly),
        # compared against goals["category_budgets"] (single source of truth).
        month_totals = _get_current_month_spent_by_cat()
        budget_panel_container.content = build_budget_progress_panel(
            cats, category_budgets, month_totals, currency_symbol
        )

        try:
            filter_status_banner.update(); total_badge.update()
            trend_graph_container.update(); chart_canvas.update()
            legend_container.update(); ledger_container.update()
            budget_panel_container.update(); inline_budget_input.update()
        except Exception:
            pass

    # ── UI CONTROLS ───────────────────────────────────────────────────────────
    search_field = ft.TextField(
        label="Search expenses...", label_style=ft.TextStyle(color="#45A29E"),
        border_color="#243142", prefix_icon=ft.Icons.SEARCH_ROUNDED, width=200,
        value=initial_query or "",
        on_change=handle_search_change)
    expense_title      = ft.TextField(
        label="Transaction Description...",
        label_style=ft.TextStyle(color="#45A29E"), border_color="#243142")
    expense_amount     = ft.TextField(
        label="Amount...",
        label_style=ft.TextStyle(color="#45A29E"), border_color="#243142", width=150)
    category_dropdown  = ft.Dropdown(
        label="Category",
        label_style=ft.TextStyle(color="#45A29E"), border_color="#243142", width=160)
    expense_date_input = ft.TextField(
        label="Entry Date (YYYY-MM-DD)",
        label_style=ft.TextStyle(color="#45A29E"),
        border_color="#243142", width=280, height=48, text_size=13,
        value=selected_anchor_date.strftime("%Y-%m-%d"))
    btn_entry_date_picker = ft.IconButton(
        icon=ft.Icons.CALENDAR_TODAY_ROUNDED, icon_color="#45A29E", icon_size=20,
        on_click=trigger_entry_calendar, tooltip="Select date for this entry")

    custom_cat_input    = ft.TextField(
        label="Add New...",
        label_style=ft.TextStyle(color="#45A29E"), border_color="#243142", width=160)
    manage_cat_dropdown = ft.Dropdown(
    label="Category",
    label_style=ft.TextStyle(color="#45A29E"), border_color="#243142", width=140)
    manage_cat_dropdown.on_change = manage_cat_dropdown_changed

    # Inline per-category budget field — sits next to manage_cat_dropdown and
    # always reflects/edits the budget for whichever category is selected
    # there. Saves via dm.set_category_budget(), the single source of truth.
    inline_budget_input = ft.TextField(
        label=f"Budget ({currency_symbol})",
        label_style=ft.TextStyle(color="#45A29E"), border_color="#243142",
        width=130, height=44, text_size=12, keyboard_type=ft.KeyboardType.NUMBER)

    submit_btn = ft.FilledButton(
        "Log Transaction", icon=ft.Icons.MONETIZATION_ON_ROUNDED,
        style=ft.ButtonStyle(bgcolor="#1F2833", color="#66FCF1"),
        on_click=add_expense_clicked)
    total_badge         = ft.Text(f"Selected Total: {currency_symbol}0", size=18,
                                   weight=ft.FontWeight.W_700, color="#66FCF1")
    settings_btn        = ft.IconButton(
        ft.Icons.SETTINGS_SUGGEST_ROUNDED, icon_color="#66FCF1",
        on_click=toggle_settings_drawer)
    # P4-T3: export_feedback Text removed — SnackBar handles feedback now
    export_btn          = ft.IconButton(
        ft.Icons.DOWNLOAD_ROUNDED, icon_color="#45A29E",
        tooltip="Export expenses to CSV", on_click=export_expenses_csv)
    filter_status_banner = ft.Text("", size=12, color="#45A29E",
                                    weight=ft.FontWeight.BOLD)

    interval_filter_toggle = ft.CupertinoSegmentedButton(
        controls=[
            ft.Text("Day Log",      size=11, weight=ft.FontWeight.W_600,
                    width=70, text_align=ft.TextAlign.CENTER),
            ft.Text("Weekly Split", size=11, weight=ft.FontWeight.W_600,
                    width=80, text_align=ft.TextAlign.CENTER),
            ft.Text("Monthly View", size=11, weight=ft.FontWeight.W_600,
                    width=80, text_align=ft.TextAlign.CENTER),
        ],
        selected_index=0, selected_color="#66FCF1", unselected_color="#1E2631",
        border_color="rgba(255,255,255,0.15)", on_change=filter_mode_shifted,
    )

    btn_calendar_picker = ft.IconButton(
        icon=ft.Icons.CALENDAR_MONTH_ROUNDED, icon_color="#66FCF1",
        icon_size=22, on_click=trigger_anchor_calendar)
    btn_time_prev = ft.IconButton(
        icon=ft.Icons.KEYBOARD_ARROW_LEFT_ROUNDED, icon_color="#66FCF1",
        icon_size=22, on_click=step_backward)
    btn_time_next = ft.IconButton(
        icon=ft.Icons.KEYBOARD_ARROW_RIGHT_ROUNDED, icon_color="#66FCF1",
        icon_size=22, on_click=step_forward)

    # Budget progress panel (lives in main right column, always visible)
    budget_panel_container = ft.Container(expand=True)

    settings_compartment = ft.Container(
        content=ft.Column([
            # ── Category management ────────────────────────────────────────
            ft.Text("Manage Categories", size=14,
                    weight=ft.FontWeight.BOLD, color="#66FCF1"),
            ft.Row([
                custom_cat_input,
                ft.IconButton(ft.Icons.ADD_BOX_ROUNDED,
                              icon_color="#66FCF1", on_click=add_new_cat_trigger),
            ]),
            # manage_cat_dropdown now does double duty: select a category to
            # delete it, or to view/edit its monthly budget inline, right here.
            ft.Row([
                manage_cat_dropdown,
                inline_budget_input,
                ft.IconButton(ft.Icons.SAVE_ROUNDED,
                              icon_color="#66FCF1",
                              tooltip="Save budget for selected category",
                              on_click=save_budget_clicked),
                ft.IconButton(ft.Icons.DELETE_FOREVER_ROUNDED,
                              icon_color="#FF4B4B",
                              tooltip="Delete selected category",
                              on_click=delete_cat_trigger),
            ], spacing=6),
            ft.Text("Set budget to 0 to remove it for that category.", size=10,
                    color="grey500", italic=True),
        ], spacing=8),
        bgcolor="#11151D", padding=15, border_radius=12,
        visible=False, width=380,
        border=ft.Border(
            ft.BorderSide(1, "#243142"), ft.BorderSide(1, "#243142"),
            ft.BorderSide(1, "#66FCF1"), ft.BorderSide(1, "#243142"),
        ),
    )

    chart_canvas          = fch.PieChart(sections=[], sections_space=3,
                                          center_space_radius=35, height=130)
    chart_frame           = ft.Container(content=chart_canvas, width=150, height=130)
    legend_container      = ft.Container(padding=5)
    ledger_container      = ft.Container(expand=True)
    trend_graph_container = ft.Container(expand=True)

    populate_dropdowns()
    refresh_expense_view()

    master_layout = ft.Row([
        # ── Left column: input form + settings ────────────────────────────
        ft.Column([
            ft.Row([
                ft.Text("Expense Allocation Console", size=18,
                        weight=ft.FontWeight.W_600, color="#45A29E"),
                ft.Row([export_btn, settings_btn], spacing=0),
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN, width=380),
            # export_feedback row intentionally removed — SnackBar handles it now
            ft.Container(
                content=ft.Column([
                    expense_title,
                    ft.Row([expense_amount, category_dropdown], spacing=10),
                    ft.Row([expense_date_input, btn_entry_date_picker],
                           spacing=4, alignment=ft.MainAxisAlignment.CENTER),
                    ft.Container(content=submit_btn, padding=5),
                    ft.Divider(height=10, color="#243142"),
                    ft.Row([btn_time_prev, filter_status_banner,
                            btn_calendar_picker, btn_time_next],
                           alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    interval_filter_toggle,
                ], alignment=ft.MainAxisAlignment.CENTER,
                   horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                bgcolor="#151A22", padding=20, border_radius=16,
                width=380, height=375,
                border=ft.Border(
                    ft.BorderSide(1, "#243142"), ft.BorderSide(1, "#243142"),
                    ft.BorderSide(1, "#243142"), ft.BorderSide(1, "#243142"),
                ),
            ),
            settings_compartment,
        ], spacing=10, width=380),

        ft.VerticalDivider(width=30, color="#1F2833"),

        # ── Right column: charts + ledger + budget bars ───────────────────
        ft.Column([
            ft.Row([
                ft.Text("Categorical Distribution Engine", size=18,
                        weight=ft.FontWeight.W_600, color="#45A29E"),
                ft.Row([search_field, total_badge], spacing=12),
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Container(
                content=ft.Column([
                    ft.Row([chart_frame, trend_graph_container],
                           alignment=ft.MainAxisAlignment.SPACE_BETWEEN, spacing=15),
                    legend_container,
                    ft.Divider(height=8, color="#243142"),
                    # ── Budget progress bars ───────────────────────────────
                    ft.Text("Monthly Budget Tracker", size=13,
                            weight=ft.FontWeight.W_600, color="#8E9AA6"),
                    budget_panel_container,
                    ft.Divider(height=8, color="#243142"),
                    ft.Text("Itemized Ledger Summary", size=14,
                            weight=ft.FontWeight.W_600, color="#8E9AA6"),
                    ft.Divider(height=10, color="#243142"),
                    ledger_container,
                ], expand=True, spacing=5),
                padding=20, bgcolor="#151A22", border_radius=16, expand=True,
                border=ft.Border(
                    ft.BorderSide(1, "#243142"), ft.BorderSide(1, "#243142"),
                    ft.BorderSide(1, "#243142"), ft.BorderSide(1, "#243142"),
                ),
            ),
        ], expand=True, spacing=10),
    ], expand=True)

    return master_layout