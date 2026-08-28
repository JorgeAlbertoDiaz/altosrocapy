# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['//wsl.localhost/Debian/home/jorge/Proyectos/altosrocapy/app/login.py'],
    pathex=[],
    binaries=[],
    datas=[('//wsl.localhost/Debian/home/jorge/Proyectos/altosrocapy/temps/logo.png', 'temps')],
    hiddenimports=['cv2', 'pygame.camera', 'pygame._camera'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='AltosRoca',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['//wsl.localhost/Debian/home/jorge/Proyectos/altosrocapy/temps/logo.ico'],
)
