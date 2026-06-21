import re
import flet as ft

# ── Theme definitions ─────────────────────────────────────────────────────────
# Each entry holds a base card_bg and border colour.
# Alpha values here are the *default* opacity; get_active_glass_theme() can
# override the card_bg alpha with the user's glass_opacity setting.

GLASS_THEMES = {
    "Glass Cyan": {
        "card_bg": "rgba(20, 30, 45, 0.45)",
        "border":  "rgba(102, 252, 241, 0.25)",
    },
    "Glass Amethyst": {
        "card_bg": "rgba(30, 20, 45, 0.45)",
        "border":  "rgba(187, 134, 252, 0.25)",
    },
    "Glass Slate": {
        "card_bg": "rgba(25, 25, 25, 0.50)",
        "border":  "rgba(255, 255, 255, 0.15)",
    },
    "Glass Forest": {
        "card_bg": "rgba(10, 28, 18, 0.50)",
        "border":  "rgba(72, 199, 116, 0.28)",
    },
    "Glass Midnight": {
        "card_bg": "rgba(8, 8, 24, 0.55)",
        "border":  "rgba(100, 120, 255, 0.28)",
    },
    "Glass Ember": {
        "card_bg": "rgba(40, 15, 10, 0.48)",
        "border":  "rgba(255, 120, 60, 0.28)",
    },
}

DEFAULT_THEME   = "Glass Cyan"
DEFAULT_OPACITY = 0.45   # matches the original Cyan base alpha


# ── Wallpaper hook ────────────────────────────────────────────────────────────

_wallpaper_container_ref = None


def register_wallpaper_container(container: ft.Container) -> None:
    """Registers the root layout frame so background images can change dynamically."""
    global _wallpaper_container_ref
    _wallpaper_container_ref = container


def update_background_wallpaper(image_path: str) -> None:
    """Safely updates the background image without breaking control layouts."""
    global _wallpaper_container_ref
    if _wallpaper_container_ref:
        if image_path:
            _wallpaper_container_ref.image = ft.DecorationImage(
                src=image_path, fit=ft.BoxFit.COVER
            )
            _wallpaper_container_ref.bgcolor = None
        else:
            # Reset path: no image selected — restore the original dark
            # background instead of leaving the layout fully transparent.
            _wallpaper_container_ref.image = None
            _wallpaper_container_ref.bgcolor = "#0B0E14"
        _wallpaper_container_ref.update()


# ── Alpha helpers ─────────────────────────────────────────────────────────────

def _parse_rgba(rgba_str: str) -> tuple[int, int, int, float] | None:
    """
    Parses "rgba(r, g, b, a)" → (r, g, b, a).
    Returns None if the string doesn't match.
    """
    m = re.match(
        r"rgba\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*([0-9.]+)\s*\)",
        rgba_str.strip(),
    )
    if not m:
        return None
    return int(m[1]), int(m[2]), int(m[3]), float(m[4])


def _set_alpha(rgba_str: str, alpha: float) -> str:
    """Returns a new rgba string with *alpha* substituted in."""
    parsed = _parse_rgba(rgba_str)
    if parsed is None:
        return rgba_str  # can't parse — leave unchanged
    r, g, b, _ = parsed
    return f"rgba({r}, {g}, {b}, {alpha:.2f})"


# ── Public API ────────────────────────────────────────────────────────────────

def get_active_glass_theme() -> dict:
    """
    Reads ``data_manager.get_settings()`` and returns the resolved
    ``{"card_bg": ..., "border": ...}`` dict for the active theme.

    Settings keys consumed
    ----------------------
    glass_theme   : str   – key into GLASS_THEMES (default: "Glass Cyan")
    glass_opacity : float – card background alpha, 0.2–0.7
                            (default: theme's own base alpha)

    The border colour is *not* affected by glass_opacity so the edge glow
    stays readable regardless of how transparent the card body is.
    """
    try:
        import data_manager as dm
        settings = dm.get_settings()
    except Exception:
        settings = {}

    theme_name = settings.get("glass_theme", DEFAULT_THEME)
    theme      = GLASS_THEMES.get(theme_name, GLASS_THEMES[DEFAULT_THEME])

    opacity = settings.get("glass_opacity", None)

    if opacity is not None:
        try:
            opacity = float(opacity)
            opacity = max(0.2, min(0.7, opacity))   # clamp to valid range
            card_bg = _set_alpha(theme["card_bg"], opacity)
        except (TypeError, ValueError):
            card_bg = theme["card_bg"]
    else:
        card_bg = theme["card_bg"]

    return {"card_bg": card_bg, "border": theme["border"]}


def create_glass_card(
    content_control,
    theme_name: str = "Glass Cyan",
    width=None,
    height=None,
    expand: bool = False,
) -> ft.Container:
    """
    Generates a frosted-glass panel.

    If callers pass ``theme_name=None`` the *active* theme from settings is
    used automatically — convenient for new widgets that should always track
    the global preference.
    """
    if theme_name is None:
        colors = get_active_glass_theme()
    else:
        colors = GLASS_THEMES.get(theme_name, GLASS_THEMES[DEFAULT_THEME])

    return ft.Container(
        content=content_control,
        bgcolor=colors["card_bg"],
        padding=25,
        border_radius=16,
        width=width,
        height=height,
        expand=expand,
        blur=15,
        border=ft.Border(
            top=ft.BorderSide(1, colors["border"]),
            bottom=ft.BorderSide(1, colors["border"]),
            left=ft.BorderSide(1, colors["border"]),
            right=ft.BorderSide(1, colors["border"]),
        ),
    )