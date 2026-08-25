"""Main window (dashboard MDI) for AltosRoca (pure Tkinter)."""

import os
import sys
import tkinter as tk
import tkinter.font as tkfont

try:
    from app import login
except ImportError:  # dev / frozen fallback
    import login

WINDOW_WIDTH = 1366
WINDOW_HEIGHT = 768

COLOR_TOPBAR_BG = "#EEEEEE"
COLOR_SIDEBAR_BG = "#1A2430"
COLOR_AREA_TOP = "#010D2A"
COLOR_AREA_BOTTOM = "#061538"
COLOR_MENU_FG = "#FFFFFF"
COLOR_MENU_HOVER = "#C9A45B"

MODULES = [
    "Acceso Socios",
    "Registrar Socios",
    "Consultar Estados Socios",
    "Consultar Socios",
    "Registrar Cobros",
    "Consultar Caja",
    "Historial de Cobros",
    "Registrar Deudas",
    "Admin Pantalla",
]

LOGO_PATH = os.path.join(os.path.dirname(__file__), "..", "temps", "logo.png")


def center_window(window: tk.Wm) -> None:
    window.update_idletasks()
    x = (window.winfo_screenwidth() - WINDOW_WIDTH) // 2
    y = (window.winfo_screenheight() - WINDOW_HEIGHT) // 2
    window.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}+{x}+{y}")


def interpolate_color(start: str, end: str, t: float) -> str:
    r1, g1, b1 = (int(start[i:i + 2], 16) for i in (1, 3, 5))
    r2, g2, b2 = (int(end[i:i + 2], 16) for i in (1, 3, 5))
    return "#{:02x}{:02x}{:02x}".format(
        round(r1 + (r2 - r1) * t),
        round(g1 + (g2 - g1) * t),
        round(b1 + (b2 - b1) * t),
    )


def build_topbar(window: tk.Tk, usuario: str) -> None:
    bar = tk.Frame(window, bg=COLOR_TOPBAR_BG, height=30)
    bar.pack(side="top", fill="x")
    bar.pack_propagate(False)

    for name in ("Admin", "Alta de Datos", "Gráficos Estadísticos", "Ayuda"):
        btn = tk.Menubutton(bar, text=name, bg=COLOR_TOPBAR_BG, fg="#000000")
        menu = tk.Menu(btn, tearoff=0)
        menu.add_command(label="(próximamente)", state="disabled")
        btn.configure(menu=menu)
        btn.pack(side="left", padx=10)

    logout = tk.Label(
        bar,
        text=f"Cerrar Sesión {usuario}",
        bg=COLOR_TOPBAR_BG,
        fg="#000000",
        font=("Helvetica", 10, "bold"),
        cursor="hand2",
    )
    logout.pack(side="right", padx=10)

    def on_logout(_event=None):
        window.destroy()
        login.main()

    logout.bind("<Button-1>", on_logout)


def build_sidebar(window: tk.Tk, font_family: str) -> tk.Frame:
    sidebar = tk.Frame(window, bg=COLOR_SIDEBAR_BG, width=290)
    sidebar.pack(side="left", fill="y")
    sidebar.pack_propagate(False)

    menu_box = tk.Frame(sidebar, bg=COLOR_SIDEBAR_BG)
    menu_box.place(x=0, y=60, width=290, height=WINDOW_HEIGHT - 60)
    for name in MODULES:
        item = tk.Label(
            menu_box,
            text=name,
            bg=COLOR_SIDEBAR_BG,
            fg=COLOR_MENU_FG,
            font=(font_family, 11),
            anchor="w",
            cursor="hand2",
        )
        item.pack(fill="x", padx=16, pady=8)
        item.bind("<Enter>", lambda e, w=item: w.configure(fg=COLOR_MENU_HOVER))
        item.bind("<Leave>", lambda e, w=item: w.configure(fg=COLOR_MENU_FG))
        item.bind("<Button-1>", lambda e, n=name: open_module(window, n, font_family))
    return sidebar


def open_module(window: tk.Tk, name: str, font_family: str) -> None:
    top = tk.Toplevel(window)
    top.title(name)
    top.geometry("900x600")
    top.configure(bg="#F0F0F0")
    top.bind("<Escape>", lambda _e: top.destroy())
    tk.Label(
        top,
        text="[Módulo en construcción]",
        bg="#F0F0F0",
        fg="#333333",
        font=(font_family, 14),
    ).place(relx=0.5, rely=0.5, anchor="center")


def build_main_area(window: tk.Tk, font_family: str) -> None:
    area = tk.Frame(window, bg=COLOR_AREA_TOP)
    area.pack(side="left", fill="both", expand=True)

    # Soft vertical gradient simulated with stacked thin frames.
    steps = 40
    band_h = WINDOW_HEIGHT // steps
    for i in range(steps):
        color = interpolate_color(COLOR_AREA_TOP, COLOR_AREA_BOTTOM, i / (steps - 1))
        band = tk.Frame(area, bg=color, height=band_h)
        band.place(x=0, y=i * band_h, relwidth=1.0, height=band_h + 1)

    logo = None
    if os.path.isfile(LOGO_PATH):
        try:
            logo = tk.PhotoImage(file=LOGO_PATH)
            logo_label = tk.Label(area, image=logo, bd=0)
            logo_label.place(relx=1.0, x=-40, rely=0.5, anchor="e")
        except tk.TclError:
            logo = None
    if logo is None:
        tk.Label(
            area,
            text="ALTOS ROCA",
            bg=COLOR_AREA_TOP,
            fg="#5A6C8C",
            font=(font_family, 32, "bold"),
        ).place(relx=1.0, x=-40, rely=0.5, anchor="e")


def build_principal(window: tk.Tk, usuario: str) -> None:
    available_fonts = {f.lower() for f in tkfont.families()}
    font_family = "Segoe UI" if "segoe ui" in available_fonts else "Helvetica"

    window.title(f"SG GYM - Sistema de Gestion de Gimnasios: ALTOS ROCA GYM - Usuario: {usuario}")
    window.resizable(False, False)
    center_window(window)

    build_topbar(window, usuario)
    build_sidebar(window, font_family)
    build_main_area(window, font_family)


def main(usuario: str) -> None:
    window = tk.Tk()
    build_principal(window, usuario)
    window.protocol("WM_DELETE_WINDOW", window.destroy)
    window.mainloop()
    # Ensure the process (and the PyInstaller onefile parent) dies cleanly.
    sys.exit(0)


if __name__ == "__main__":
    main("MARCO")
