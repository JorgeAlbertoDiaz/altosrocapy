r"""System-date override for testing filters without changing Windows clock.

Usage (PowerShell):
    $env:ALTOSROCA_HOY = "20/07/2026"; .\AltosRoca.exe

If the variable is not set (or invalid), the real system date is used.
"""

import datetime
import os

ENV_VAR = "ALTOSROCA_HOY"


def hoy() -> datetime.date:
    raw = os.environ.get(ENV_VAR, "")
    if raw:
        for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
            try:
                return datetime.datetime.strptime(raw, fmt).date()
            except ValueError:
                continue
    return datetime.date.today()
