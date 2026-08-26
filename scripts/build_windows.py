# Build de AltosRoca para Windows: compila los .exe y los copia al destino.
#
# Uso (desde la raiz del proyecto):
#   py scripts\build_windows.py
#   py scripts\build_windows.py --dest "D:\mi-carpeta"
#
# Requisitos: Python 3.12+ y PyInstaller (`py -m pip install pyinstaller`).

import argparse
import os
import shutil
import subprocess
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOGO = os.path.join(PROJECT_ROOT, "temps", "logo.png")

BUILDS = [
    {"name": "AltosRoca", "windowed": True},
    {"name": "AltosRocaDebug", "windowed": False},
]


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
    cmd += ["--name", name, f"--add-data={LOGO};temps"]
    cmd += ["--distpath", dist_dir, "--workpath", work_dir]
    cmd += [os.path.join(PROJECT_ROOT, "app", "login.py")]
    print(f"== Compilando {name}.exe ==")
    result = subprocess.run(cmd, cwd=PROJECT_ROOT)
    if result.returncode != 0:
        raise SystemExit(f"Fallo la compilacion de {name}.exe")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--dest",
        default=r"C:\altos roca\dist-windows",
        help="Carpeta destino de los exe y la DB",
    )
    args = parser.parse_args()

    dist_dir = os.path.join(PROJECT_ROOT, "dist-windows")
    work_dir = os.path.join(PROJECT_ROOT, "build", "tmp")

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
