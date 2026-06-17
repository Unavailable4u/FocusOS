import flet as ft
from datetime import datetime
import data_manager as dm

# ── Mood metadata ─────────────────────────────────────────────────────────────
_MOODS = {
    1: ("😞", "Rough",     "#FF5252"),
    2: ("😕", "Low",       "#FF9100"),
    3: ("😐", "Okay",      "#FFD740"),
    4: ("🙂", "Good",      "#69F0AE"),
    5: ("😄", "Great",     "#00FFFF"),
}

def _mood_label(value: int) -> str:
    emoji, word, _ = _MOODS.get(value, ("😐", "Okay", "#FFD740"))
    return f"{emoji}  {word}"

def _mood_color(value: int) -> str:
    return _MOODS.get(value, ("", "", "#FFD740"))[2]


def build_journal(page: ft.Page) -> ft.Control:
    today_str = datetime.now().strftime("%Y-%m-%d")

    # ── Editor state ─────────────────────────────────────────────────────────
    current_mood  = {"value": 3}
    save_feedback = ft.Text("", size=12, color="#69F0AE")

    mood_indicator = ft.Text(
        _mood_label(3), size=15, weight=ft.FontWeight.W_600,
        color=_mood_color(3),
    )

    mood_slider = ft.Slider(
        min=1, max=5, divisions=4, value=3,
        active_color="#00FFFF", inactive_color="rgba(255,255,255,0.12)",
        thumb_color="#00FFFF",
        expand=True,
    )

    journal_input = ft.TextField(
        multiline=True, min_lines=5, max_lines=10,
        hint_text="Write your thoughts for today…",
        hint_style=ft.TextStyle(color="grey600"),
        border_color="rgba(255,255,255,0.15)",
        focused_border_color="#00FFFF",
        bgcolor="#1E2631",
        color="white",
        text_size=14,
        expand=True,
        border_radius=8,
    )

    def on_mood_change(e):
        v = int(round(e.control.value))
        current_mood["value"]  = v
        mood_indicator.value   = _mood_label(v)
        mood_indicator.color   = _mood_color(v)
        try:
            mood_indicator.update()
        except Exception:
            pass

    mood_slider.on_change = on_mood_change

    # ── Entry list ────────────────────────────────────────────────────────────
    entries_column = ft.Column(spacing=10, scroll=ft.ScrollMode.AUTO, expand=True)

    def _entry_card(entry: dict) -> ft.Container:
        mood_val  = int(entry.get("mood", 3))
        date_str  = entry.get("date", "")
        text_body = entry.get("text", "").strip()
        emoji, word, color = _MOODS.get(mood_val, ("😐", "Okay", "#FFD740"))

        try:
            display_date = datetime.strptime(date_str, "%Y-%m-%d").strftime("%B %d, %Y")
        except ValueError:
            display_date = date_str

        is_today = (date_str == today_str)
        border_color = "#00FFFF" if is_today else "rgba(255,255,255,0.08)"

        return ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Text(display_date, size=12, color="grey500",
                            weight=ft.FontWeight.W_500),
                    ft.Container(expand=True),
                    ft.Container(
                        content=ft.Text(f"{emoji} {word}", size=12,
                                        weight=ft.FontWeight.W_600, color=color),
                        bgcolor=f"{color}1A",   # 10 % tint
                        border_radius=20,
                        padding=ft.Padding(10, 4, 10, 4),
                    ),
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                ft.Text(
                    text_body if text_body else "(no text)",
                    size=13, color="white" if text_body else "grey600",
                    max_lines=6, overflow=ft.TextOverflow.ELLIPSIS,
                ),
            ], spacing=6),
            bgcolor="#1E2631",
            border_radius=10,
            padding=14,
            border=ft.border.all(1, border_color),
        )

    def _reload_entries():
        data    = dm.load_data()
        entries = sorted(
            data.get("journal", []),
            key=lambda e: e.get("date", ""),
            reverse=True,
        )
        entries_column.controls = [_entry_card(e) for e in entries]
        try:
            entries_column.update()
        except Exception:
            pass

    def _prefill_today():
        """If today already has an entry, populate the editor with it."""
        data = dm.load_data()
        for entry in data.get("journal", []):
            if entry.get("date") == today_str:
                journal_input.value     = entry.get("text", "")
                v                       = int(entry.get("mood", 3))
                current_mood["value"]   = v
                mood_slider.value       = v
                mood_indicator.value    = _mood_label(v)
                mood_indicator.color    = _mood_color(v)
                break

    def save_entry(e):
        text = journal_input.value or ""
        mood = current_mood["value"]

        data = dm.load_data()
        if "journal" not in data:
            data["journal"] = []

        # Upsert: update today's entry if it exists, else append
        for existing in data["journal"]:
            if existing.get("date") == today_str:
                existing["mood"] = mood
                existing["text"] = text
                break
        else:
            data["journal"].append({
                "date": today_str,
                "mood": mood,
                "text": text,
            })

        dm.save_data(data)

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
            ft.Row([
                ft.Text("Mood:", size=13, color="grey400"),
                mood_indicator,
            ], spacing=10),
            ft.Row([
                ft.Text("😞", size=16), mood_slider, ft.Text("😄", size=16),
            ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            ft.Container(height=4),
            journal_input,
            ft.Container(height=6),
            ft.Row([save_btn, save_feedback], spacing=12,
                   vertical_alignment=ft.CrossAxisAlignment.CENTER),
        ], spacing=6),
        bgcolor="#151B25",
        border_radius=12,
        padding=18,
        border=ft.border.all(1, "rgba(255,255,255,0.08)"),
    )

    # ── Past entries section ──────────────────────────────────────────────────
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