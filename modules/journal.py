import flet as ft
import sys
import os
from datetime import datetime

try:
    import data_manager as dm
except ModuleNotFoundError:
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    import data_manager as dm


# ── Data helpers ──────────────────────────────────────────────────────────────

def add_journal_entry(date: str, mood: int, went_well: str, blockers: str) -> None:
    """Upsert a journal entry for the given date."""
    data = dm.load_data()
    if "journal" not in data:
        data["journal"] = []

    for entry in data["journal"]:
        if entry.get("date") == date:
            entry["mood"]       = mood
            entry["went_well"]  = went_well
            entry["blockers"]   = blockers
            dm.save_data(data)
            return

    data["journal"].append({
        "date":       date,
        "mood":       mood,
        "went_well":  went_well,
        "blockers":   blockers,
    })
    dm.save_data(data)


def get_journal_entries() -> list[dict]:
    """Return all journal entries sorted newest-first."""
    data = dm.load_data()
    return sorted(
        data.get("journal", []),
        key=lambda e: e.get("date", ""),
        reverse=True,
    )


# ── Mood metadata ─────────────────────────────────────────────────────────────

_MOODS: dict[int, tuple[str, str, str]] = {
    1: ("😞", "Rough",  "#FF5252"),
    2: ("😕", "Low",    "#FF9100"),
    3: ("😐", "Okay",   "#FFD740"),
    4: ("🙂", "Good",   "#69F0AE"),
    5: ("😄", "Great",  "#00FFFF"),
}


def _mood_color(value: int) -> str:
    return _MOODS.get(value, ("", "", "#FFD740"))[2]


def _mood_label(value: int) -> str:
    emoji, word, _ = _MOODS.get(value, ("😐", "Okay", "#FFD740"))
    return f"{emoji}  {word}"


# ── Public builder ────────────────────────────────────────────────────────────

def build_journal(page: ft.Page) -> ft.Control:
    today_str = datetime.now().strftime("%Y-%m-%d")

    # ── Editor state ──────────────────────────────────────────────────────────
    current_mood = {"value": 3}

    save_feedback = ft.Text("", size=12, color="#69F0AE")

    # ── Mood selector (5 tappable emoji buttons) ──────────────────────────────
    # NOTE: ft.IconButton in this Flet version does not accept a `content`
    # kwarg, so emoji glyphs can't be shown via IconButton (it only renders
    # built-in icon glyphs via `icon=`). Containers give us the same
    # tappable-button feel (ink ripple + on_click) while letting us render
    # arbitrary text/emoji content.
    mood_buttons: list[ft.Container] = []

    def _refresh_mood_buttons(selected: int) -> None:
        for btn in mood_buttons:
            idx = btn.data
            emoji, _, color = _MOODS[idx]
            is_sel = (idx == selected)
            btn.content.color = color if is_sel else "rgba(255,255,255,0.25)"
            btn.content.size  = 34 if is_sel else 28
            btn.tooltip       = _mood_label(idx)
            try:
                btn.update()
            except Exception:
                pass

    def _make_mood_click(idx: int):
        def _on_click(e):
            current_mood["value"] = idx
            save_feedback.value   = ""
            try:
                save_feedback.update()
            except Exception:
                pass
            _refresh_mood_buttons(idx)
        return _on_click

    for i in range(1, 6):
        emoji, _, color = _MOODS[i]
        btn = ft.Container(
            content=ft.Text(emoji, size=28, color="rgba(255,255,255,0.25)"),
            tooltip=_mood_label(i),
            data=i,
            on_click=_make_mood_click(i),
            ink=True,
            border_radius=20,
            padding=4,
            alignment=ft.alignment.Alignment(0, 0),
        )
        mood_buttons.append(btn)

    _refresh_mood_buttons(3)   # default selection

    mood_row = ft.Row(
        [ft.Text("How are you feeling?", size=13, color="grey400")] +
        mood_buttons,
        spacing=6,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )

    # ── Text fields ───────────────────────────────────────────────────────────
    _TF_COMMON = dict(
        multiline=True, min_lines=3, max_lines=6,
        border_color="rgba(255,255,255,0.15)",
        focused_border_color="#00FFFF",
        bgcolor="#1E2631",
        color="white",
        text_size=14,
        expand=True,
        border_radius=8,
    )

    went_well_input = ft.TextField(
        label="What went well today?",
        label_style=ft.TextStyle(color="#45A29E"),
        hint_text="Wins, progress, moments of gratitude…",
        hint_style=ft.TextStyle(color="grey600"),
        **_TF_COMMON,
    )

    blockers_input = ft.TextField(
        label="Any blockers?",
        label_style=ft.TextStyle(color="#45A29E"),
        hint_text="Challenges, distractions, things to fix…",
        hint_style=ft.TextStyle(color="grey600"),
        **_TF_COMMON,
    )

    # ── Entry list ────────────────────────────────────────────────────────────
    entries_column = ft.Column(spacing=10, scroll=ft.ScrollMode.AUTO, expand=True)

    def _entry_card(entry: dict) -> ft.Container:
        mood_val   = int(entry.get("mood", 3))
        date_str   = entry.get("date", "")
        went_well  = (entry.get("went_well") or entry.get("text") or "").strip()
        blockers   = (entry.get("blockers") or "").strip()
        emoji, word, color = _MOODS.get(mood_val, ("😐", "Okay", "#FFD740"))

        try:
            display_date = datetime.strptime(date_str, "%Y-%m-%d").strftime("%B %d, %Y")
        except ValueError:
            display_date = date_str

        is_today     = (date_str == today_str)
        border_color = "#00FFFF" if is_today else "rgba(255,255,255,0.08)"

        body_parts: list[ft.Control] = []

        if went_well:
            body_parts += [
                ft.Text("✅  What went well", size=11, color="#69F0AE",
                        weight=ft.FontWeight.W_600),
                ft.Text(went_well, size=13, color="white",
                        max_lines=4, overflow=ft.TextOverflow.ELLIPSIS),
            ]
        if blockers:
            body_parts += [
                ft.Container(height=4),
                ft.Text("🚧  Blockers", size=11, color="#FF9100",
                        weight=ft.FontWeight.W_600),
                ft.Text(blockers, size=13, color="grey400",
                        max_lines=4, overflow=ft.TextOverflow.ELLIPSIS),
            ]
        if not body_parts:
            body_parts.append(
                ft.Text("(no content)", size=13, color="grey600", italic=True)
            )

        return ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Text(display_date, size=12, color="grey500",
                            weight=ft.FontWeight.W_500),
                    ft.Container(expand=True),
                    ft.Container(
                        content=ft.Text(f"{emoji} {word}", size=12,
                                        weight=ft.FontWeight.W_600, color=color),
                        bgcolor=f"{color}1A",
                        border_radius=20,
                        padding=ft.Padding(10, 4, 10, 4),
                    ),
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                ft.Divider(height=8, color="rgba(255,255,255,0.06)"),
                *body_parts,
            ], spacing=4),
            bgcolor="#1E2631",
            border_radius=10,
            padding=14,
            border=ft.Border.all(1, border_color),
        )

    def _reload_entries() -> None:
        entries_column.controls = [_entry_card(e) for e in get_journal_entries()]
        try:
            entries_column.update()
        except Exception:
            pass

    def _prefill_today() -> None:
        """Populate editor fields if today already has an entry."""
        for entry in get_journal_entries():
            if entry.get("date") == today_str:
                went_well_input.value  = entry.get("went_well") or entry.get("text", "")
                blockers_input.value   = entry.get("blockers", "")
                v = int(entry.get("mood", 3))
                current_mood["value"]  = v
                _refresh_mood_buttons(v)
                break

    # ── Save handler ──────────────────────────────────────────────────────────
    def save_entry(e):
        add_journal_entry(
            date       = today_str,
            mood       = current_mood["value"],
            went_well  = went_well_input.value or "",
            blockers   = blockers_input.value  or "",
        )
        save_feedback.value = "✓  Entry saved"
        try:
            save_feedback.update()
        except Exception:
            pass
        _reload_entries()

    save_btn = ft.ElevatedButton(
        "Save Entry",
        icon=ft.Icons.SAVE_ROUNDED,
        bgcolor="#1E2631",
        color="#00FFFF",
        style=ft.ButtonStyle(
            side=ft.BorderSide(1, "#00FFFF"),
            shape=ft.RoundedRectangleBorder(radius=8),
        ),
        on_click=save_entry,
    )

    # ── Editor panel ──────────────────────────────────────────────────────────
    editor_panel = ft.Container(
        content=ft.Column([
            ft.Text("Today's Entry", size=15, weight=ft.FontWeight.W_600,
                    color="#45A29E"),
            ft.Text(datetime.now().strftime("%A, %B %d %Y"),
                    size=12, color="grey500"),
            ft.Container(height=4),
            mood_row,
            ft.Container(height=4),
            went_well_input,
            ft.Container(height=6),
            blockers_input,
            ft.Container(height=8),
            ft.Row([save_btn, save_feedback], spacing=12,
                   vertical_alignment=ft.CrossAxisAlignment.CENTER),
        ], spacing=6),
        bgcolor="#151B25",
        border_radius=12,
        padding=18,
        border=ft.Border.all(1, "rgba(255,255,255,0.08)"),
    )

    # ── Past entries panel ────────────────────────────────────────────────────
    history_panel = ft.Column([
        ft.Container(height=4),
        ft.Text("Past Entries", size=15, weight=ft.FontWeight.W_600,
                color="#45A29E"),
        ft.Container(height=4),
        entries_column,
    ], expand=True, spacing=0)

    # Initialise
    _prefill_today()
    _reload_entries()

    return ft.Column([
        ft.Container(
            content=ft.Text("Daily Journal", size=22,
                            weight=ft.FontWeight.W_600, color="#45A29E"),
            bgcolor="#1E2631",
            padding=ft.Padding(4, 10, 4, 10),
        ),
        ft.Container(height=8),
        editor_panel,
        ft.Container(height=4),
        history_panel,
    ], expand=True, scroll=ft.ScrollMode.ALWAYS, spacing=0)