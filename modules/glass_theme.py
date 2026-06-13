import flet as ft

GLASS_THEMES = {
    "Glass Cyan": {"card_bg": "rgba(20, 30, 45, 0.45)", "border": "rgba(102, 252, 241, 0.25)"},
    "Glass Amethyst": {"card_bg": "rgba(30, 20, 45, 0.45)", "border": "rgba(187, 134, 252, 0.25)"},
    "Glass Slate": {"card_bg": "rgba(25, 25, 25, 0.5)", "border": "rgba(255, 255, 255, 0.15)"}
}

# Isolated global placeholder hook for your background container reference
_wallpaper_container_ref = None

def register_wallpaper_container(container: ft.Container):
    """Registers the root layout frame so background images can change dynamically."""
    global _wallpaper_container_ref
    _wallpaper_container_ref = container

def update_background_wallpaper(image_path: str):
    """Safely updates the background image without breaking control layouts."""
    global _wallpaper_container_ref
    if _wallpaper_container_ref:
        _wallpaper_container_ref.image = ft.DecorationImage(src=image_path, fit=ft.BoxFit.COVER)
        _wallpaper_container_ref.bgcolor = None
        _wallpaper_container_ref.update()

def create_glass_card(content_control, theme_name="Glass Cyan", width=None, height=None, expand=False):
    """Generates frosted glass panels matching native layout constraints."""
    colors = GLASS_THEMES.get(theme_name, GLASS_THEMES["Glass Cyan"])
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
            top=ft.BorderSide(1, colors["border"]), bottom=ft.BorderSide(1, colors["border"]),
            left=ft.BorderSide(1, colors["border"]), right=ft.BorderSide(1, colors["border"])
        )
    )