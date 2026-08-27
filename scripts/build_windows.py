# Build de AltosRoca para Windows: compila los .exe y los copia al destino.
#
# Uso (desde la raiz del proyecto):
#   py scripts\build_windows.py
#   py scripts\build_windows.py --dest "D:\mi-carpeta"
#   py scripts\build_windows.py --check dist-windows\AltosRoca.exe
#
# Requisitos: Python 3.12+ y PyInstaller (`py -m pip install pyinstaller`).
#
# IMPORTANTE (arquitectura): PyInstaller NO es cross-compiler. La arquitectura
# del .exe resultante la fija el intérprete de Python que ejecuta este script:
#   - Python 64-bit  -> exe 64-bit  (NO corre en un Windows de 32 bits)
#   - Python 32-bit  -> exe 32-bit  (corre en Windows de 32 y 64 bits)
# Si el exe debe correr en un Windows de 32 bits (p. ej. AMD Sempron 145),
# compilar con un Python de 32 bits (x86) instalado en Windows.

import argparse
import os
import platform
import shutil
import struct
import subprocess
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOGO = os.path.join(PROJECT_ROOT, "temps", "logo.png")
ICON = os.path.join(PROJECT_ROOT, "temps", "logo.ico")

# Arquitectura del .exe generado por este intérprete.
ARCH = {"32bit": "32 bits (x86)", "64bit": "64 bits (x64)"}.get(
    platform.architecture()[0], platform.architecture()[0])

BUILDS = [
    {"name": "AltosRoca", "windowed": True},
    {"name": "AltosRocaDebug", "windowed": False},
]

# Dependencies required by the app AND by the build itself.
REQUIRED_PACKAGES = ["pyinstaller", "openpyxl", "fpdf2", "tkcalendar"]
REQUIRED_IMPORTS = {
    "pyinstaller": "PyInstaller",
    "openpyxl": "openpyxl",
    "fpdf2": "fpdf",
    "tkcalendar": "tkcalendar",
}


def ensure_dependencies() -> None:
    """Install any missing package into THIS interpreter.

    The 'py' launcher may resolve to several Python installs; building with
    one that lacks PyInstaller/app deps fails confusingly. This keeps the
    script self-healing no matter which interpreter runs it.
    """
    import importlib

    missing = []
    for package, module in REQUIRED_IMPORTS.items():
        try:
            importlib.import_module(module)
        except ImportError:
            missing.append(package)
    if not missing:
        return
    print(f"== Instalando dependencias faltantes: {', '.join(missing)} ==")
    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", "--quiet", *missing],
    )
    if result.returncode != 0:
        raise SystemExit("Fallo la instalacion de dependencias con pip")


def pe_arch(path: str) -> str:
    """Return the architecture of a PE .exe from its header.

    0x8664 -> x86-64 (64-bit), 0x14c -> x86 (32-bit), 0xaa64 -> ARM64.
    """
    try:
        with open(path, "rb") as f:
            d = f.read(4096)
    except OSError:
        return "no accesible"
    if d[:2] != b"MZ":
        return "no es un ejecutable PE"
    pe_off = struct.unpack("<I", d[0x3C:0x40])[0]
    if d[pe_off:pe_off + 4] != b"PE\0\0":
        return "firma PE no encontrada"
    machine = struct.unpack("<H", d[pe_off + 4:pe_off + 6])[0]
    if machine == 0x8664:
        return "64 bits (x64)"
    if machine == 0x14C:
        return "32 bits (x86)"
    if machine == 0xAA64:
        return "ARM64"
    return f"desconocida (0x{machine:x})"


def kill_running():
    subprocess.run(
        ["taskkill", "/F", "/IM", "AltosRoca.exe"],
        capture_output=True,
    )
    subprocess.run(
        ["taskkill", "/F", "/IM", "AltosRocaDebug.exe"],
        capture_output=True,
    )


def build(name: str, windowed: bool, dist_dir: str, work_dir: str) -> None:
    cmd = [sys.executable, "-m", "PyInstaller", "--noconfirm", "--onefile"]
    if windowed:
        cmd.append("--windowed")
    cmd += ["--name", name, f"--add-data={LOGO};temps", f"--icon={ICON}"]
    cmd += ["--distpath", dist_dir, "--workpath", work_dir]
    cmd += [os.path.join(PROJECT_ROOT, "app", "login.py")]
    print(f"== Compilando {name}.exe ==")
    result = subprocess.run(cmd, cwd=PROJECT_ROOT)
    if result.returncode != 0:
        raise SystemExit(f"Fallo la compilacion de {name}.exe")
    exe = os.path.join(dist_dir, f"{name}.exe")
    print(f"   {name}.exe -> {pe_arch(exe)}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compila AltosRoca para Windows e inspecciona arquitectura.")
    parser.add_argument(
        "--dest",
        default=r"C:\altos roca\dist-windows",
        help="Carpeta destino de los exe y la DB",
    )
    parser.add_argument(
        "--check",
        metavar="EXE",
        help="Solo inspecciona la arquitectura de un .exe y sale sin compilar.",
    )
    args = parser.parse_args()

    if args.check:
        print(f"{args.check}: {pe_arch(args.check)}")
        return

    ensure_dependencies()

    dist_dir = os.path.join(PROJECT_ROOT, "dist-windows")
    work_dir = os.path.join(PROJECT_ROOT, "build", "tmp")

    print(f"== Python que compila: {sys.executable}")
    print(f"   Arquitectura del .exe resultante: {ARCH} ==")

    for spec in BUILDS:
        build(spec["name"], spec["windowed"], dist_dir, work_dir)

    print("== Copiando al destino ==")
    kill_running()
    os.makedirs(args.dest, exist_ok=True)
    os.makedirs(os.path.join(args.dest, "data"), exist_ok=True)
    shutil.copy2(os.path.join(dist_dir, "AltosRoca.exe"), args.dest)
    shutil.copy2(os.path.join(dist_dir, "AltosRocaDebug.exe"), args.dest)
    db = os.path.join(PROJECT_ROOT, "data", "altosroca.db")
    shutil.copy2(db, os.path.join(args.dest, "data"))

    print(f"== Listo. Ejecutables y DB en: {args.dest} ==")


if __name__ == "__main__":
    main()
