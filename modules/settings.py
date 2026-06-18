import flet as ft
from datetime import datetime

import data_manager as dm
from .color_palette import (
    SWATCH_PALETTE,
    get_task_color,
    get_expense_color,
)
from .file_dialogs import pick_save_path, pick_open_file, pick_image
from .glass_theme import GLASS_THEMES, DEFAULT_OPACITY


# ── Shared swatch-picker factory ──────────────────────────────────────────────

def _make_swatch_row(
    current_color: str,
    on_pick,          # callable(hex_str) → None
    hex_field_ref,    # ft.Ref[ft.TextField] — shared hex entry
) -> ft.Row:
    """
    Returns a Row of 12 colored square swatches.
    Clicking a swatch calls on_pick(hex) and updates the shared hex field.
    A small ✓ ring marks the currently active color.
    """
    swatches = []
    for color in SWATCH_PALETTE:
        is_active = color.upper() == (current_color or "").upper()
        swatches.append(
            ft.Container(
                width=24,
                height=24,
                border_radius=4,
                bgcolor=color,
                border=ft.Border(ft.BorderSide(2, "white" if is_active else "transparent"), ft.BorderSide(2, "white" if is_active else "transparent"), ft.BorderSide(2, "white" if is_active else "transparent"), ft.BorderSide(2, "white" if is_active else "transparent")),
                tooltip=color,
                on_click=lambda e, c=color: _swatch_clicked(e, c, on_pick, hex_field_ref),
            )
        )
    return ft.Row(swatches, spacing=4, wrap=True)


def _swatch_clicked(e, color: str, on_pick, hex_field_ref):
    on_pick(color)
    if hex_field_ref.current:
        hex_field_ref.current.value = color
        hex_field_ref.current.update()


# ── Per-item color row ────────────────────────────────────────────────────────

def _make_color_row(
    label: str,
    current_color: str,
    on_save,          # callable(name, hex) → None
    name_key: str,    # the name to pass to on_save
    page: ft.Page,
) -> ft.Container:
    """
    One row: colored swatch preview  ·  label  ·  12 swatches  ·  hex TextField
    """
    hex_ref = ft.Ref[ft.TextField]()

    preview = ft.Container(
        width=18,
        height=18,
        border_radius=4,
        bgcolor=current_color,
    )

    def on_pick(hex_color: str):
        preview.bgcolor = hex_color
        preview.update()
        on_save(name_key, hex_color)

    def on_hex_submit(e):
        val = (hex_ref.current.value or "").strip()
        if len(val) in (6, 7):
            hex_color = val if val.startswith("#") else f"#{val}"
            on_pick(hex_color)

    swatch_row = _make_swatch_row(current_color, on_pick, hex_ref)

    hex_field = ft.TextField(
        ref=hex_ref,
        value=current_color,
        width=90,
        hint_text="#RRGGBB",
        max_length=7,
        on_submit=on_hex_submit,
        on_blur=on_hex_submit,
        text_size=12,
        content_padding=ft.Padding(left=8, top=6, right=8, bottom=6),
    )

    return ft.Container(
        content=ft.Column(
            [
                ft.Row(
                    [preview, ft.Text(label, size=13, expand=True)],
                    spacing=8,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                ft.Row(
                    [swatch_row, hex_field],
                    spacing=12,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
            ],
            spacing=6,
        ),
        padding=ft.Padding(left=0, top=8, right=0, bottom=8),
    )


# ── Color-overrides section builder ──────────────────────────────────────────

def _build_color_overrides_section(page: ft.Page) -> ft.Container:
    data = dm.load_data()
    task_titles   = [t["title"] for t in data.get("tasks", [])]
    categories    = data.get("categories", ["Study", "Food", "Transport", "Other"])
    task_ov       = dm.get_task_color_overrides()
    cat_ov        = dm.get_category_color_overrides()

    def save_task_color(name: str, hex_color: str):
        dm.set_task_color_override(name, hex_color)

    def save_cat_color(name: str, hex_color: str):
        dm.set_category_color_override(name, hex_color)

    task_rows = [
        _make_color_row(
            label=title,
            current_color=task_ov.get(title, get_task_color(title)),
            on_save=save_task_color,
            name_key=title,
            page=page,
        )
        for title in task_titles
    ] or [ft.Text("No tasks yet.", size=13, color="grey600")]

    cat_rows = [
        _make_color_row(
            label=cat,
            current_color=cat_ov.get(cat, get_expense_color(cat)),
            on_save=save_cat_color,
            name_key=cat,
            page=page,
        )
        for cat in categories
    ]

    return ft.Container(
        content=ft.Column(
            [
                ft.Text("Color overrides", size=16, weight=ft.FontWeight.W_600),
                ft.Text(
                    "Choose custom colors for focus tasks and expense categories. "
                    "Click a swatch or type a hex value.",
                    size=13,
                    color="grey600",
                ),
                ft.Divider(height=1, color="rgba(255,255,255,0.05)"),
                ft.Text("Focus tasks", size=14, weight=ft.FontWeight.W_500),
                *task_rows,
                ft.Divider(height=1, color="rgba(255,255,255,0.05)"),
                ft.Text("Expense categories", size=14, weight=ft.FontWeight.W_500),
                *cat_rows,
            ],
            spacing=6,
        ),
        bgcolor="#11151D",
        border_radius=12,
        padding=20,
    )


# ── Glass theme section ───────────────────────────────────────────────────────

def _build_glass_theme_section(page: ft.Page) -> ft.Container:
    """
    Dropdown to pick the active glass theme + slider to set card opacity.
    Writes ``glass_theme`` and ``glass_opacity`` into settings.
    """
    settings        = dm.get_settings()
    current_theme   = settings.get("glass_theme",   list(GLASS_THEMES.keys())[0])
    current_opacity = float(settings.get("glass_opacity", DEFAULT_OPACITY))

    # ── Preview swatch ────────────────────────────────────────────────────────

    def _preview_bgcolor(theme_name: str, opacity: float) -> str:
        from .glass_theme import _set_alpha
        base = GLASS_THEMES.get(theme_name, GLASS_THEMES[current_theme])["card_bg"]
        return _set_alpha(base, opacity)

    preview_box = ft.Container(
        width=120,
        height=40,
        border_radius=8,
        bgcolor=_preview_bgcolor(current_theme, current_opacity),
        blur=8,
        border=ft.Border(ft.BorderSide(1, GLASS_THEMES.get(current_theme, {}).get("border", "rgba(255,255,255,0.2)")), ft.BorderSide(1, GLASS_THEMES.get(current_theme, {}).get("border", "rgba(255,255,255,0.2)")), ft.BorderSide(1, GLASS_THEMES.get(current_theme, {}).get("border", "rgba(255,255,255,0.2)")), ft.BorderSide(1, GLASS_THEMES.get(current_theme, {}).get("border", "rgba(255,255,255,0.2)"))),
        tooltip="Live preview",
    )

    opacity_label = ft.Text(
        f"Opacity: {current_opacity:.0%}",
        size=13,
        color="grey400",
    )

    # mutable state to keep dropdown and slider in sync
    _state = {"theme": current_theme, "opacity": current_opacity}

    def _refresh_preview():
        preview_box.bgcolor = _preview_bgcolor(_state["theme"], _state["opacity"])
        _b = GLASS_THEMES.get(_state["theme"], {}).get("border", "rgba(255,255,255,0.2)")
        preview_box.border  = ft.Border(ft.BorderSide(1, _b), ft.BorderSide(1, _b), ft.BorderSide(1, _b), ft.BorderSide(1, _b))
        opacity_label.value = f"Opacity: {_state['opacity']:.0%}"
        preview_box.update()
        opacity_label.update()

    # ── Dropdown ──────────────────────────────────────────────────────────────

    def on_theme_change(e):
        _state["theme"] = e.control.value
        dm.save_settings({"glass_theme": _state["theme"]})
        _refresh_preview()

    theme_dropdown = ft.Dropdown(
        label="Glass theme",
        value=current_theme,
        width=220,
        options=[ft.dropdown.Option(k) for k in GLASS_THEMES.keys()],
    )
    theme_dropdown.on_change = on_theme_change

    # ── Opacity slider ────────────────────────────────────────────────────────

    def on_opacity_change(e):
        _state["opacity"] = round(float(e.control.value), 2)
        dm.save_settings({"glass_opacity": _state["opacity"]})
        _refresh_preview()

    opacity_slider = ft.Slider(
        min=0.2,
        max=0.7,
        divisions=10,
        value=current_opacity,
        label="{value}",
        expand=True,
    )
    opacity_slider.on_change = on_opacity_change

    return ft.Container(
        content=ft.Column(
            [
                ft.Text("Glass theme", size=16, weight=ft.FontWeight.W_600),
                ft.Text(
                    "Applies to all glass cards across the app. "
                    "Changes take effect when you next open each page.",
                    size=13,
                    color="grey600",
                ),
                ft.Row([theme_dropdown, preview_box], spacing=16,
                       vertical_alignment=ft.CrossAxisAlignment.CENTER),
                ft.Row(
                    [
                        ft.Text("Opacity", size=13, width=60),
                        opacity_slider,
                        opacity_label,
                    ],
                    spacing=10,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
            ],
            spacing=10,
        ),
        bgcolor="#11151D",
        border_radius=12,
        padding=20,
    )


# ── Background / Wallpaper section ───────────────────────────────────────────

def _build_wallpaper_section(page: ft.Page) -> ft.Container:
    """
    Renders a wallpaper card with two ways to set a background:

    1. Bundled presets — 4 clickable thumbnails (forest, mountaints, night_city,
       ocean) sourced from assets/wallpapers/.  The active preset gets a white
       border ring.  If a file is missing at runtime the tile shows a labelled
       colour swatch instead so the UI never breaks.

    2. Custom upload — "Browse…" button that opens an image picker, copies the
       chosen file into assets/wallpapers/, persists the path, and applies it
       live via glass_theme.update_background_wallpaper().

    A "Reset to Default" text-button (hidden when no wallpaper is set) clears
    the path and restores the plain bgcolor.

    Note on night_city.avif: AVIF decoding works on modern Linux/macOS/Win11.
    If you see a blank tile on an older machine, convert it to night_city.jpg.
    """
    import os
    import shutil
    from .glass_theme import update_background_wallpaper

    WALLPAPER_DIR = os.path.join("assets", "wallpapers")

    # ── Bundled preset definitions ─────────────────────────────────────────────
    # (label, filename, fallback_color)
    PRESETS: list[tuple[str, str, str]] = [
        ("Forest",     "forest.jpg",      "#1B3A2D"),
        ("Mountains",  "mountaints.jpg",  "#2C3E50"),
        ("Night City", "night_city.jpg",  "#0D0D2B"),
        ("Ocean",      "ocean.jpg",       "#0A3560"),
    ]

    # ── Shared state ──────────────────────────────────────────────────────────

    settings     = dm.get_settings()
    current_path = settings.get("background_image_path", "")

    status_text = ft.Text("", size=12, color="green400")

    current_label = ft.Text(
        os.path.basename(current_path) if current_path else "No wallpaper set",
        size=12,
        color="grey400",
        italic=not bool(current_path),
    )

    reset_btn = ft.TextButton(
        "Reset to Default",
        icon=ft.Icons.RESTORE_ROUNDED,
        visible=bool(current_path),
    )

    # Refs to each preset tile Container so we can update their borders
    preset_tile_refs: list[ft.Ref] = [ft.Ref[ft.Container]() for _ in PRESETS]

    def _set_status(msg: str, ok: bool = True) -> None:
        status_text.value = msg
        status_text.color = "green400" if ok else "red400"
        status_text.update()

    def _active_border() -> ft.Border:
        s = ft.BorderSide(2, "white")
        return ft.Border(s, s, s, s)

    def _inactive_border() -> ft.Border:
        s = ft.BorderSide(1, "rgba(255,255,255,0.15)")
        return ft.Border(s, s, s, s)

    def _refresh_ui(new_path: str) -> None:
        """Update label, reset button, and preset tile highlight borders."""
        current_label.value  = os.path.basename(new_path) if new_path else "No wallpaper set"
        current_label.italic = not bool(new_path)
        current_label.update()

        reset_btn.visible = bool(new_path)
        reset_btn.update()

        # Highlight whichever preset tile matches new_path (if any)
        for ref, (_, filename, _) in zip(preset_tile_refs, PRESETS):
            if ref.current is None:
                continue
            preset_full = os.path.join(WALLPAPER_DIR, filename)
            is_active   = bool(new_path) and (
                os.path.normpath(new_path) == os.path.normpath(preset_full)
            )
            ref.current.border = _active_border() if is_active else _inactive_border()
            ref.current.update()

    # ── Core apply logic (shared by presets and custom upload) ────────────────

    def _apply_path(dest_path: str, label: str) -> None:
        dm.set_background_image_path(dest_path)
        try:
            update_background_wallpaper(dest_path)
        except Exception:
            pass  # best-effort live update
        _refresh_ui(dest_path)
        _set_status(f"Wallpaper set to {label}", ok=True)

    # ── Preset tiles ──────────────────────────────────────────────────────────

    def _make_preset_tile(
        label: str,
        filename: str,
        fallback_color: str,
        tile_ref: ft.Ref,
    ) -> ft.Container:
        preset_path = os.path.join(WALLPAPER_DIR, filename)
        file_exists = os.path.isfile(preset_path)

        is_active = bool(current_path) and (
            os.path.normpath(current_path) == os.path.normpath(preset_path)
        )

        # Inner content: real thumbnail if file exists, coloured swatch otherwise
        if file_exists:
            inner = ft.Image(
                src=preset_path,
                width=110,
                height=70,
                fit=ft.BoxFit.COVER,
                border_radius=ft.BorderRadius(6, 6, 0, 0),
            )
        else:
            inner = ft.Container(
                width=110,
                height=70,
                bgcolor=fallback_color,
                border_radius=ft.BorderRadius(6, 6, 0, 0),
                content=ft.Icon(
                    ft.Icons.IMAGE_NOT_SUPPORTED_OUTLINED,
                    size=20,
                    color="rgba(255,255,255,0.3)",
                ),
                alignment=ft.Alignment(0, 0),
            )

        def on_preset_click(e, _path=preset_path, _label=label, _exists=file_exists):
            if not _exists:
                _set_status(f"{_label} image not found in assets/wallpapers/", ok=False)
                return
            _apply_path(_path, _label)

        return ft.Container(
            ref=tile_ref,
            width=110,
            border_radius=8,
            border=_active_border() if is_active else _inactive_border(),
            clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
            on_click=on_preset_click,
            tooltip=label,
            content=ft.Column(
                [
                    inner,
                    ft.Container(
                        content=ft.Text(
                            label,
                            size=11,
                            text_align=ft.TextAlign.CENTER,
                            color="white",
                            weight=ft.FontWeight.W_500,
                        ),
                        bgcolor="rgba(0,0,0,0.55)",
                        padding=ft.Padding(left=4, top=3, right=4, bottom=3),
                        alignment=ft.Alignment(0, 0),
                        width=110,
                    ),
                ],
                spacing=0,
                tight=True,
            ),
        )

    preset_tiles = ft.Row(
        [
            _make_preset_tile(label, filename, color, ref)
            for (label, filename, color), ref in zip(PRESETS, preset_tile_refs)
        ],
        spacing=10,
        wrap=True,
    )

    # ── Custom upload ─────────────────────────────────────────────────────────

    def _on_image_picked(src_path: str | None) -> None:
        if not src_path:
            return
        try:
            os.makedirs(WALLPAPER_DIR, exist_ok=True)
        except OSError as exc:
            _set_status(f"Cannot create wallpaper folder: {exc}", ok=False)
            return

        filename  = os.path.basename(src_path)
        dest_path = os.path.join(WALLPAPER_DIR, filename)
        try:
            shutil.copy2(src_path, dest_path)
        except OSError as exc:
            _set_status(f"Copy failed: {exc}", ok=False)
            return

        _apply_path(dest_path, filename)

    def on_browse_click(e) -> None:
        pick_image(page, on_result=_on_image_picked)

    # ── Reset ─────────────────────────────────────────────────────────────────

    def on_reset_click(e) -> None:
        dm.clear_background_image_path()
        try:
            update_background_wallpaper("")
        except Exception:
            pass
        _refresh_ui("")
        _set_status("Background reset to default.", ok=True)

    reset_btn.on_click = on_reset_click

    # ── Layout ────────────────────────────────────────────────────────────────

    return ft.Container(
        content=ft.Column(
            [
                ft.Text("Background", size=16, weight=ft.FontWeight.W_600),
                ft.Text(
                    "Pick a preset or upload your own image.",
                    size=13,
                    color="grey600",
                ),
                # ── Preset thumbnails ─────────────────────────────────────
                ft.Text("Presets", size=13, weight=ft.FontWeight.W_500,
                        color="grey300"),
                preset_tiles,
                ft.Divider(height=1, color="rgba(255,255,255,0.06)"),
                # ── Custom upload row ─────────────────────────────────────
                ft.Text("Custom", size=13, weight=ft.FontWeight.W_500,
                        color="grey300"),
                ft.Row(
                    [
                        ft.Text("Active:", size=13, color="grey400"),
                        current_label,
                    ],
                    spacing=6,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                ft.Row(
                    [
                        ft.ElevatedButton(
                            "Browse…",
                            icon=ft.Icons.FOLDER_OPEN_ROUNDED,
                            on_click=on_browse_click,
                        ),
                        reset_btn,
                    ],
                    spacing=12,
                ),
                status_text,
            ],
            spacing=10,
        ),
        bgcolor="#11151D",
        border_radius=12,
        padding=20,
    )


# ── Backup / Restore section ──────────────────────────────────────────────────

def _build_backup_restore_section(page: ft.Page) -> ft.Container:
    """
    Renders a card with two buttons:
      • Backup Data   → pick_save_path → dm.backup_data(dest)
      • Restore Data  → pick_open_file → validate → confirm dialog → dm.restore_data(src)
    A status Text widget surfaces success / error feedback inline.
    """

    status_text = ft.Text("", size=13, color="green400")

    def _set_status(msg: str, ok: bool = True) -> None:
        status_text.value = msg
        status_text.color = "green400" if ok else "red400"
        status_text.update()

    # ── Backup ────────────────────────────────────────────────────────────────

    def _on_backup_result(dest_path: str | None) -> None:
        if not dest_path:
            return  # user cancelled
        try:
            dm.backup_data(dest_path)
            _set_status(f"Backup saved to {dest_path}", ok=True)
        except OSError as exc:
            _set_status(f"Backup failed: {exc}", ok=False)

    def on_backup_click(e) -> None:
        suggested = f"focusos_backup_{datetime.now().strftime('%Y-%m-%d')}.json"
        pick_save_path(
            page,
            on_result=_on_backup_result,
            suggested_name=suggested,
            allowed_extensions=["json"],
        )

    # ── Restore ───────────────────────────────────────────────────────────────

    def _do_restore(src_path: str) -> None:
        ok, reason = dm.restore_data(src_path)
        if ok:
            _set_status("Data restored successfully. Restart the app to see changes.", ok=True)
        else:
            _set_status(f"Restore failed: {reason}", ok=False)

    def _show_confirm_dialog(src_path: str) -> None:
        def on_confirm(e):
            page.close(dlg)
            _do_restore(src_path)

        def on_cancel(e):
            page.close(dlg)
            _set_status("Restore cancelled.", ok=True)

        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text("Overwrite current data?"),
            content=ft.Text(
                "Restoring will replace all your current tasks, expenses, and "
                "focus logs with the contents of the selected file. "
                "This cannot be undone.",
                size=13,
            ),
            actions=[
                ft.TextButton("Cancel", on_click=on_cancel),
                ft.FilledButton(
                    "Restore",
                    on_click=on_confirm,
                    style=ft.ButtonStyle(bgcolor=ft.Colors.RED_700),
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        page.open(dlg)

    def _on_restore_result(src_path: str | None) -> None:
        if not src_path:
            return  # user cancelled

        ok, reason = dm.validate_backup(src_path)
        if not ok:
            _set_status(f"Invalid backup file: {reason}", ok=False)
            return

        _show_confirm_dialog(src_path)

    def on_restore_click(e) -> None:
        pick_open_file(
            page,
            on_result=_on_restore_result,
            allowed_extensions=["json"],
        )

    # ── Layout ────────────────────────────────────────────────────────────────

    return ft.Container(
        content=ft.Column(
            [
                ft.Text("Backup & Restore", size=16, weight=ft.FontWeight.W_600),
                ft.Text(
                    "Save a copy of your data.json, or replace it with a previously "
                    "saved backup.",
                    size=13,
                    color="grey600",
                ),
                ft.Row(
                    [
                        ft.ElevatedButton(
                            "Backup Data",
                            icon=ft.Icons.DOWNLOAD_ROUNDED,
                            on_click=on_backup_click,
                        ),
                        ft.ElevatedButton(
                            "Restore Data",
                            icon=ft.Icons.UPLOAD_ROUNDED,
                            on_click=on_restore_click,
                        ),
                    ],
                    spacing=12,
                ),
                status_text,
            ],
            spacing=10,
        ),
        bgcolor="#11151D",
        border_radius=12,
        padding=20,
    )


# ── Main entry-point ──────────────────────────────────────────────────────────

def build_settings(page: ft.Page):
    """Settings view — profile, pomodoro defaults, and color overrides."""

    settings = dm.get_settings()

    def save_profile_name(e):
        dm.save_settings({"profile_name": name_field.value.strip()})

    def save_currency_symbol(e):
        val = (currency_field.value or "").strip()
        dm.save_settings({"currency_symbol": val if val else "৳"})

    name_field = ft.TextField(
        label="Display name",
        hint_text="e.g. Alex",
        value=settings.get("profile_name", ""),
        width=320,
        on_change=save_profile_name,
        on_blur=save_profile_name,
    )

    currency_field = ft.TextField(
        label="Currency symbol",
        hint_text="৳",
        value=settings.get("currency_symbol", "৳"),
        width=90,
        max_length=3,
        on_change=save_currency_symbol,
        on_blur=save_currency_symbol,
    )

    profile_section = ft.Container(
        content=ft.Column(
            [
                ft.Text("Profile", size=16, weight=ft.FontWeight.W_600),
                ft.Text(
                    "Used for the dashboard greeting and currency labels.",
                    size=13,
                    color="grey600",
                ),
                ft.Row([name_field, currency_field], spacing=12),
            ],
            spacing=8,
        ),
        bgcolor="#11151D",
        border_radius=12,
        padding=20,
    )

    default_durations = settings.get("default_durations", {})

    def save_default_durations(e):
        try:
            focus_val    = float(focus_default_field.value)    if focus_default_field.value    else 150
            short_val    = float(short_default_field.value)    if short_default_field.value    else 5
            long_val     = float(long_default_field.value)     if long_default_field.value     else 15
            interval_val = int(interval_default_field.value)   if interval_default_field.value else 3
        except ValueError:
            return
        dm.save_settings({
            "default_durations": {
                "focus":    focus_val,
                "short":    short_val,
                "long":     long_val,
                "interval": interval_val,
            }
        })

    focus_default_field = ft.TextField(
        label="Work (Min)",
        value=str(default_durations.get("focus", 150)),
        width=110,
        on_change=save_default_durations,
        on_blur=save_default_durations,
    )
    short_default_field = ft.TextField(
        label="Short break (Min)",
        value=str(default_durations.get("short", 5)),
        width=110,
        on_change=save_default_durations,
        on_blur=save_default_durations,
    )
    long_default_field = ft.TextField(
        label="Long break (Min)",
        value=str(default_durations.get("long", 15)),
        width=110,
        on_change=save_default_durations,
        on_blur=save_default_durations,
    )
    interval_default_field = ft.TextField(
        label="Interval",
        value=str(default_durations.get("interval", 3)),
        width=110,
        on_change=save_default_durations,
        on_blur=save_default_durations,
    )

    pomodoro_defaults_section = ft.Container(
        content=ft.Column(
            [
                ft.Text("Pomodoro defaults", size=16, weight=ft.FontWeight.W_600),
                ft.Text(
                    "Starting values for the Pomodoro timer's configuration fields.",
                    size=13,
                    color="grey600",
                ),
                ft.Row(
                    [
                        focus_default_field,
                        short_default_field,
                        long_default_field,
                        interval_default_field,
                    ],
                    spacing=12,
                ),
            ],
            spacing=8,
        ),
        bgcolor="#11151D",
        border_radius=12,
        padding=20,
    )

    color_overrides_section = _build_color_overrides_section(page)
    backup_restore_section  = _build_backup_restore_section(page)
    glass_theme_section     = _build_glass_theme_section(page)
    wallpaper_section       = _build_wallpaper_section(page)

    header = ft.Column(
        [
            ft.Text("Settings", size=28, weight=ft.FontWeight.BOLD),
            ft.Text("Configure FocusOS to your liking.", size=14, color="grey400"),
        ],
        spacing=4,
    )

    placeholder_section = ft.Container(
        content=ft.Column(
            [
                ft.Icon(ft.Icons.CONSTRUCTION_ROUNDED, size=32, color="grey600"),
                ft.Text(
                    "More settings coming",
                    size=16,
                    weight=ft.FontWeight.W_600,
                    color="grey400",
                ),
                ft.Text(
                    "This section is under construction. Check back soon.",
                    size=13,
                    color="grey600",
                ),
            ],
            spacing=8,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        bgcolor="#11151D",
        border_radius=12,
        padding=30,
        alignment=ft.Alignment(0, 0),
    )

    return ft.Column(
        [
            header,
            ft.Divider(height=1, color="rgba(255,255,255,0.05)"),
            profile_section,
            pomodoro_defaults_section,
            glass_theme_section,
            wallpaper_section,
            backup_restore_section,
            color_overrides_section,
            placeholder_section,
        ],
        spacing=20,
        expand=True,
    )