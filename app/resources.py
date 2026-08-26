"""Shared resource resolution for dev and frozen (PyInstaller) runs."""

import os
import sys


def resource_path(*parts: str) -> str:
    """Absolute path to a bundled resource, both in dev and frozen mode.

    Frozen (onefile): files land under sys._MEIPASS preserving the
    --add-data destination (e.g. temps/logo.png -> _MEIPASS/temps/logo.png).
    Dev: project root is two levels above this file's directory.
    """
    if getattr(sys, "frozen", False):
        base = sys._MEIPASS  # noqa: SLF001 - documented PyInstaller attr
    else:
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, *parts)


def get_logo_path() -> str:
    """Path to the company logo; empty string if the file does not exist."""
    path = resource_path("temps", "logo.png")
    return path if os.path.isfile(path) else ""


def load_logo(max_w: int | None = None, max_h: int | None = None):
    """Load the logo scaled down to fit max_w x max_h (keeps aspect ratio).

    Returns a tk.PhotoImage or None if unavailable. The caller must keep
    a reference to the returned image to avoid garbage collection.
    """
    path = get_logo_path()
    if not path:
        return None
    import tkinter as tk

    try:
        img = tk.PhotoImage(file=path)
    except tk.TclError:
        return None
    if max_w and max_h:
        w, h = img.width(), img.height()
        # Ceil division: shrink just enough to fit the box.
        factor = max(1, -(-w // max_w), -(-h // max_h))
        if factor > 1:
            img = img.subsample(factor, factor)
    return img


def apply_app_icon(window):
    """Set the app icon on the window (and its future children)."""
    img = load_logo()
    if img is not None:
        try:
            window.iconphoto(True, img)
        except Exception:
            pass


def force_taskbar_button(window):
    """Make an overrideredirect(True) window show a taskbar button.

    Borderless windows are not managed by Windows and get no taskbar
    entry; briefly re-managing the window registers it.
    """
    def _toggle():
        try:
            window.overrideredirect(False)
            window.iconify()
            window.overrideredirect(True)
            window.deiconify()
        except Exception:
            pass

    window.update_idletasks()
    window.after(50, _toggle)
