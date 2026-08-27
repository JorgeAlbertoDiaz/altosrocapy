"""socios_foto — gestión de fotos de socios.

La foto se guarda como archivo externo junto a la DB, con path relativo,
particionado por el último dígito del Documento, estandarizado a JPEG
cuadrado 1:1 de ~320x320, con placeholder (silueta) si el archivo no existe.
"""

import os
import re
from pathlib import Path

try:
    from PIL import Image, ImageOps, ImageTk
except ImportError:  # pragma: no cover
    Image = None
    ImageOps = None
    ImageTk = None

# ── Constants ─────────────────────────────────────────────────────────────

FOTO_DIR_REL = "socios_img"
FOTO_NAME_EXT = ".jpg"
CUAD = 320

_RE_NUM = re.compile(r"^\d+$")


# ── Path helpers ──────────────────────────────────────────────────────────

def app_root():
    """Raíz del proyecto (directorio que contiene app/). Devuelve un Path."""
    return Path(__file__).resolve().parent.parent


def foto_dir_abs():
    """Carpeta raíz absoluta donde viven las fotos."""
    return app_root() / FOTO_DIR_REL


def digito_carpeta(documento):
    """Último dígito del documento SOLO si es numérico; si no, None."""
    if documento is None:
        return None
    t = str(documento).strip()
    if not _RE_NUM.match(t):
        return None
    return t[-1]


def foto_rel_path(documento):
    """Path relativo POSIX socios_img/<digito>/<doc>.jpg, o "" si no numérico."""
    dig = digito_carpeta(documento)
    if dig is None:
        return ""
    name = f"{str(documento).strip()}{FOTO_NAME_EXT}"
    return f"{FOTO_DIR_REL}/{dig}/{name}"


def foto_abs_path(path_rel):
    """Convierte pathImage (relativo o legacy Windows) en un Path absoluto."""
    if path_rel is None or str(path_rel) == "":
        return None
    p = str(path_rel).strip()
    if re.match(r"^[A-Za-z]:", p) or os.path.isabs(p):
        return Path(p)
    return app_root() / p


def tiene_foto(documento):
    """True si existe físicamente el archivo de foto del documento."""
    rel = foto_rel_path(documento)
    if not rel:
        return False
    abs_path = foto_abs_path(rel)
    return bool(abs_path and abs_path.is_file())


def estandarizar_y_guardar(src_path, documento):
    """Estandariza una imagen a JPEG cuadrado 1:1 y la guarda.

    Devuelve el path relativo (para tbSocios.pathImage) o None si falló.
    """
    dig = digito_carpeta(documento)
    if dig is None:
        return None
    if Image is None or ImageOps is None:
        return None
    try:
        with Image.open(src_path) as img:
            img = img.convert("RGB")
            img = ImageOps.fit(img, (CUAD, CUAD), Image.Resampling.LANCZOS)
            dest = foto_abs_path(foto_rel_path(documento))
            dest.parent.mkdir(parents=True, exist_ok=True)
            img.save(dest, "JPEG", quality=85, optimize=True)
        return foto_rel_path(documento)
    except Exception:
        return None


def cargar_para_tk(path_rel, lado=125):
    """Abre la foto como ImageTk.PhotoImage re-muestreada a lado x lado.

    Devuelve un PhotoImage o None si no existe / error.
    """
    if Image is None or ImageTk is None:
        return None
    abs_path = foto_abs_path(path_rel)
    if not abs_path or not abs_path.is_file():
        return None
    try:
        with Image.open(abs_path) as img:
            img = img.convert("RGB")
            img = img.resize((lado, lado), Image.Resampling.LANCZOS)
            return ImageTk.PhotoImage(img)
    except Exception:
        return None
