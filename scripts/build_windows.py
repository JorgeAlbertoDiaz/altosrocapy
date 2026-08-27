# Build de AltosRoca para Windows: compila los .exe y los copia al destino.
#
# Uso (desde la raiz del proyecto, en Windows):
#   py scripts\build_windows.py                        # orquesta: exe 64 bits moderno
#   py scripts\build_windows.py --win7                 # orquesta: exe 64 bits + exe win7 x86
#   py scripts\build_windows.py --bits 64 --dest "D:\mi-carpeta"
#   py scripts\build_windows.py --check dist-windows\AltosRoca.exe
#
# Modo orquestador (default, solo Windows con launcher `py`): detecta los
# Pythons instalados con `py -0p` y compila solo:
#   - variante moderna de 64 bits (Python 3.9+ x64), siempre
#   - variante win7 de maxima compatibilidad (Python 3.8 x86), con `--win7`
# El exe win7-x86 corre hasta en Windows 7 de 32 bits; el de 64 bits no corre
# en SO de 32 bits.
#
# Requisitos: PyInstaller (`py -m pip install pyinstaller`). Para el exe win7
# se necesita un Python 3.8 de 32 bits instalado y registrado en `py`; el
# script fuerza las dependencias compatibles con 3.8 (fpdf2<2.8.4, openpyxl<4).
#
# IMPORTANTE (arquitectura): PyInstaller NO es cross-compiler. La arquitectura
# del .exe resultante la fija el intérprete de Python que ejecuta este script:
#   - Python 64-bit  -> exe 64-bit  (NO corre en un Windows de 32 bits)
#   - Python 32-bit  -> exe 32-bit  (corre en Windows de 32 y 64 bits)

import argparse
import os
import platform
import re
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
REQUIRED_IMPORTS = {
    "pyinstaller": "PyInstaller",
    "openpyxl": "openpyxl",
    "fpdf2": "fpdf",
    "tkcalendar": "tkcalendar",
}


def _pins() -> dict:
    """Intentos de instalacion por version de Python (pip con pin de version).

    La app debe poder correr en Windows 7 x86, lo que obliga a compilar con
    Python 3.8 (3.9+ dejo de soportar Windows 7). Varias libs dejaron de
    soportar 3.8 en versiones recientes, asi que en 3.8 se fuerzan versiones
    compatibles:
      - fpdf2 >= 2.8.4 dejo de soportar Python 3.8  -> fpdf2<2.8.4
      - openpyxl 3.1.x soporta Python 3.8            -> openpyxl<4
    """
    import sys
    if sys.version_info[:2] == (3, 8):
        return {
            "pyinstaller": None,
            "openpyxl": "openpyxl<4",
            "fpdf2": "fpdf2<2.8.4",
            "tkcalendar": None,
        }
    return {k: None for k in REQUIRED_IMPORTS}


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
    pins = _pins()
    to_install = []
    for package in missing:
        spec = pins.get(package)
        to_install.append(spec if spec else package)
    print(f"== Instalando dependencias faltantes: {', '.join(to_install)} ==")
    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", "--quiet", *to_install],
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


def build(name: str, windowed: bool, dist_dir: str, work_dir: str, bits: str) -> None:
    # Nombre con sufijo de arquitectura para que convivan x86 y x64 en la misma
    # carpeta (p. ej. AltosRoca-x64.exe y AltosRoca-x86.exe), mas el nombre plano
    # como alias del nativo para no romper compatibilidad con docs/scripts.
    names = [name, f"{name}-{bits}"]
    for out_name in names:
        _build_one(out_name, windowed, dist_dir, work_dir)
    print(f"   {name}.exe (nativo {bits}) -> {pe_arch(os.path.join(dist_dir, f'{name}.exe'))}")


def _build_one(name: str, windowed: bool, dist_dir: str, work_dir: str) -> None:
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


def discover_pythons() -> list:
    """Lista los Pythons instalados via el launcher `py` (Windows).

    Devuelve una lista de dicts: {tag, bits, version(2-tupla)}. Vacía si el
    launcher `py` no está disponible. Tolera los formatos `-3.12-64` y
    `-V:3.12-64`` del output de `py -0p`.
    """
    try:
        proc = subprocess.run(["py", "-0p"], capture_output=True, text=True)
    except (OSError, FileNotFoundError):
        return []
    if proc.returncode != 0:
        return []
    found = []
    pat = re.compile(r"-V?:(\d+)\.(\d+)(?:-(\d+))?")
    for line in proc.stdout.splitlines():
        line = line.strip().lstrip("*").strip()
        if not line:
            continue
        m = pat.search(line)
        if not m:
            continue
        major, minor = int(m.group(1)), int(m.group(2))
        bits = m.group(3) or ""
        # recomponer el tag exacto que espera `py`: -3.8-32 / -3.13-64
        if bits:
            tag = f"-{major}.{minor}-{bits}"
        else:
            tag = f"-{major}.{minor}"
        found.append({"tag": tag, "bits": bits, "version": (major, minor)})
    return found


def find_python(pythons: list, bits: str, min_version=(3, 8)) -> str | None:
    """Elige un tag de `py` para la arquitectura y minimo de version pedidos.

    Prefiere versiones mas viejas de la misma arquitectura: para el exe win7
    (x86) se quiere Python 3.8 (la ultima que soporta Windows 7), no uno mas
    nuevo que romperia esa compatibilidad.
    """
    candidates = [p for p in pythons if p["bits"] == bits and p["version"] >= min_version]
    if not candidates:
        return None
    candidates.sort(key=lambda p: p["version"])
    return candidates[0]["tag"]


def _spawn(tag: str, args: list) -> None:
    """Re-invoca este mismo script con el Python indicado por `py <tag>`."""
    cmd = ["py", tag, os.path.join(PROJECT_ROOT, "scripts", "build_windows.py"), *args]
    print(f"\n== Delegando a Python {tag} ==")
    result = subprocess.run(cmd, cwd=PROJECT_ROOT)
    if result.returncode != 0:
        raise SystemExit(f"La compilacion con Python {tag} fallo (ver arriba)")


def orchestrate(args) -> None:
    """Orquestra la compilacion de varias arquitecturas desde un solo comando.

    Solo tiene sentido en Windows con el launcher `py`. Compila la variante
    moderna de 64 bits (siempre) y, si se pide `--win7`, ademas la variante de
    maxima compatibilidad con Windows 7 de 32 bits (Python 3.8 x86).
    """
    pythons = discover_pythons()
    if not pythons:
        print("No se detecto el launcher `py` de Windows; compilando solo con el Python actual.")
        run_build(args, "64" if platform.architecture()[0] == "64bit" else "32")
        return

    # Variante moderna: 64 bits.
    tag64 = find_python(pythons, "64", (3, 9))
    if tag64:
        _spawn(tag64, ["--bits", "64", "--dest", args.dest, "--spawned"])
    else:
        print("No hay Python de 64 bits con `py`; se omite la variante moderna.")

    # Variante win7 (max compat): 32 bits con Python 3.8.
    if args.win7:
        tag32 = find_python(pythons, "32", (3, 8))
        if tag32:
            _spawn(tag32, ["--bits", "32", "--dest", args.dest, "--spawned"])
        else:
            print(
                "No se encontro un Python 3.8 de 32 bits en `py`. Instalalo y "
                "volve a correr con --win7, o compila manualmente:\n"
                "  py -3.8-32 scripts\\build_windows.py --bits 32"
            )


def run_build(args, bits: str) -> None:
    """Compila la arquitectura indicada con el Python que ejecuta este script."""
    ensure_dependencies()

    dist_dir = os.path.join(PROJECT_ROOT, "dist-windows")
    work_dir = os.path.join(PROJECT_ROOT, "build", "tmp")

    print(f"== Python que compila: {sys.executable}")
    print(f"   Arquitectura del .exe resultante: {ARCH} ==")

    for spec in BUILDS:
        build(spec["name"], spec["windowed"], dist_dir, work_dir, bits)

    print("== Copiando al destino ==")
    kill_running()
    os.makedirs(args.dest, exist_ok=True)
    os.makedirs(os.path.join(args.dest, "data"), exist_ok=True)
    for name in ("AltosRoca", "AltosRocaDebug"):
        for arch_name in (f"{name}.exe", f"{name}-{bits}.exe"):
            src = os.path.join(dist_dir, arch_name)
            if os.path.exists(src):
                shutil.copy2(src, args.dest)
    db = os.path.join(PROJECT_ROOT, "data", "altosroca.db")
    shutil.copy2(db, os.path.join(args.dest, "data"))

    print(f"== Listo. Ejecutables y DB en: {args.dest} ==")


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
    parser.add_argument(
        "--bits",
        choices=["32", "64"],
        help=(
            "Arquitectura requerida del .exe. Usa el Python actual. Si no se da, "
            "en Windows orquesta la compilacion de 64 bits (y de 32 bits si se "
            "pasa --win7) usando el launcher `py`."
        ),
    )
    parser.add_argument(
        "--win7",
        action="store_true",
        help=(
            "Ademas de la variante moderna de 64 bits, compilar la de maxima "
            "compatibilidad con Windows 7 de 32 bits (Python 3.8 x86)."
        ),
    )
    parser.add_argument(
        "--spawned",
        action="store_true",
        help="Uso interno: invocado por el orquestador con `py <tag>`; no volver a orquestar.",
    )
    args = parser.parse_args()

    if args.check:
        print(f"{args.check}: {pe_arch(args.check)}")
        return

    running_bits = "64" if platform.architecture()[0] == "64bit" else "32"

    # Modo orquestador (solo Windows): sin --bits explícito y no invocado por otro py.
    if not args.bits and not args.spawned and os.name == "nt":
        orchestrate(args)
        return

    if args.bits and args.bits != running_bits:
        raise SystemExit(
            f"El Python que ejecuta este script es de {running_bits} bits ({ARCH}), "
            f"pero se pidio --bits {args.bits}. Compilalo con el Python del mismo "
            f"bitness (py -3-{args.bits} scripts\\build_windows.py), o usalo sin "
            f"--bits para que el script orqueste solo."
        )
    bits = args.bits or running_bits
    run_build(args, bits)


if __name__ == "__main__":
    main()
