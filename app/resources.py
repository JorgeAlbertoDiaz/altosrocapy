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
