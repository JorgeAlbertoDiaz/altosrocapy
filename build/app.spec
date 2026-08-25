# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for AltosRoca (Windows, onefile, windowed).
#
# CAVEAT on the datas entry below: in onefile mode, bundled data files are
# extracted to the temporary _MEIPASS extraction dir at runtime, NOT placed
# next to the executable. app/db.py resolves the DB from the exe directory
# (data/altosroca.db), so for a truly portable deployment you should ship
# data/altosroca.db alongside AltosRoca.exe (see build/README.md and the
# zip produced by the GitHub Actions workflow). The datas entry keeps the
# DB available inside the bundle as a fallback.

a = Analysis(
    ["../app/login.py"],
    pathex=[".."],
    binaries=[],
    datas=[("../data/altosroca.db", "data")],
    hiddenimports=[],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="AltosRoca",
    debug=False,
    strip=False,
    upx=False,
    console=False,
)
