"""
modules/file_dialogs.py
-----------------------
Thin wrappers around ft.FilePicker so feature modules never have to touch
page.overlay or picker lifecycle themselves.

Usage
-----
from modules.file_dialogs import pick_open_file, pick_save_path

# Open a single file
pick_open_file(
    page,
    on_result=lambda path: print("selected:", path),   # path is str | None
    allowed_extensions=["json"],
)

# Choose a save location
pick_save_path(
    page,
    on_result=lambda path: print("save to:", path),    # path is str | None
    suggested_name="backup.json",
    allowed_extensions=["json"],
)

Callbacks always receive exactly one argument: the resolved path string, or
None if the user cancelled or the picker returned no result.
"""

from __future__ import annotations
import flet as ft


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _ensure_overlay(page: ft.Page, picker: ft.FilePicker) -> None:
    """Add *picker* to page.overlay only if it isn't already there."""
    if picker not in page.overlay:
        page.overlay.append(picker)
        try:
            page.update()
        except Exception:
            pass


def _make_picker(on_result_cb) -> ft.FilePicker:
    """
    Build a FilePicker whose on_result fires the caller's callback with a
    plain path string (or None).  We wire both on_result and on_save_result
    to the same normaliser so a single picker instance can handle either
    dialog type without requiring the caller to distinguish them.
    """
    def _normalise(e: ft.FilePickerResultEvent) -> None:
        path: str | None = None
        # Save-dialog result lands in e.path; open-dialog in e.files
        if hasattr(e, "path") and e.path:
            path = e.path
        elif hasattr(e, "files") and e.files:
            path = e.files[0].path
        on_result_cb(path)

    picker = ft.FilePicker(
        on_result=_normalise,
        on_upload=None,         # not used here
    )
    return picker


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def pick_open_file(
    page: ft.Page,
    on_result,
    allowed_extensions: list[str] | None = None,
) -> None:
    """
    Show an OS open-file dialog.

    Parameters
    ----------
    page               : ft.Page
        The active Flet page (needed for overlay registration).
    on_result          : callable(path: str | None) -> None
        Called once the user picks a file or cancels.
        *path* is the absolute file path, or None on cancel.
    allowed_extensions : list[str] | None
        e.g. ["json", "csv"].  None means all files are shown.
    """
    picker = _make_picker(on_result)
    _ensure_overlay(page, picker)

    file_type = (
        ft.FilePickerFileType.CUSTOM
        if allowed_extensions
        else ft.FilePickerFileType.ANY
    )

    picker.pick_files(
        allow_multiple=False,
        file_type=file_type,
        allowed_extensions=allowed_extensions or [],
    )


def pick_save_path(
    page: ft.Page,
    on_result,
    suggested_name: str = "file.txt",
    allowed_extensions: list[str] | None = None,
) -> None:
    """
    Show an OS save-file dialog.

    Parameters
    ----------
    page               : ft.Page
        The active Flet page (needed for overlay registration).
    on_result          : callable(path: str | None) -> None
        Called once the user confirms a path or cancels.
        *path* is the chosen absolute file path, or None on cancel.
    suggested_name     : str
        Default filename pre-filled in the dialog (e.g. "backup_2025-06-18.json").
    allowed_extensions : list[str] | None
        e.g. ["json", "csv"].  None means no extension filter is applied.
    """
    picker = _make_picker(on_result)
    _ensure_overlay(page, picker)

    picker.save_file(
        file_name=suggested_name,
        file_type=(
            ft.FilePickerFileType.CUSTOM
            if allowed_extensions
            else ft.FilePickerFileType.ANY
        ),
        allowed_extensions=allowed_extensions or [],
    )


def pick_open_files(
    page: ft.Page,
    on_result,
    allowed_extensions: list[str] | None = None,
) -> None:
    """
    Show an OS open-file dialog that allows selecting multiple files.

    Parameters
    ----------
    page               : ft.Page
    on_result          : callable(paths: list[str]) -> None
        Called with a (possibly empty) list of absolute file paths.
        Empty list means the user cancelled.
    allowed_extensions : list[str] | None
    """
    def _multi_normalise(e: ft.FilePickerResultEvent) -> None:
        paths: list[str] = []
        if hasattr(e, "files") and e.files:
            paths = [f.path for f in e.files if f.path]
        on_result(paths)

    picker = ft.FilePicker(on_result=_multi_normalise)
    _ensure_overlay(page, picker)

    file_type = (
        ft.FilePickerFileType.CUSTOM
        if allowed_extensions
        else ft.FilePickerFileType.ANY
    )

    picker.pick_files(
        allow_multiple=True,
        file_type=file_type,
        allowed_extensions=allowed_extensions or [],
    )


def pick_image(
    page: ft.Page,
    on_result,
) -> None:
    """
    Convenience wrapper for image-only open dialogs (background picker, avatars).

    Parameters
    ----------
    on_result : callable(path: str | None) -> None
    """
    picker = _make_picker(on_result)
    _ensure_overlay(page, picker)

    picker.pick_files(
        allow_multiple=False,
        file_type=ft.FilePickerFileType.IMAGE,
        allowed_extensions=[],
    )