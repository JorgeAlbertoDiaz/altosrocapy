"""Main window (dashboard MDI) for AltosRoca (pure Tkinter)."""

import os
import sys
import tkinter as tk
import tkinter.font as tkfont

try:
    from app import login
    from app import acceso_socios
    from app import consultar_estados_socios
    from app import consultar_socios
    from app import registrar_cobros
    from app import anular_cobros
    from app import registrar_socio
    from app import registrar_deudas
    from app import caja
    from app import historial_cobros
    from app import abm_generico
    from app import admin_cuentas
    from app import registrar_gastos
    from app.resources import load_logo, apply_app_icon
except ImportError:  # dev / frozen fallback
    import login
    import acceso_socios
    import consultar_estados_socios
    import consultar_socios
    import registrar_cobros
    import anular_cobros
    import registrar_socio
    import registrar_deudas
    import caja
    import historial_cobros
    import abm_generico
    import admin_cuentas
    import registrar_gastos
    from resources import load_logo, apply_app_icon

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
    "Registrar Gastos",
    "Admin Pantalla",
]

# Set by on_logout; consumed in main() after the mainloop ends.
_logout_requested = False
_current_user = "Admin"


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


def build_topbar(window: tk.Tk, usuario: str, font_family: str) -> None:
    bar = tk.Frame(window, bg=COLOR_TOPBAR_BG, height=30)
    bar.pack(side="top", fill="x")
    bar.pack_propagate(False)

    def _cmd(name):
        return lambda: open_module(window, name, font_family)

    # --- Admin ---
    m_admin = tk.Menubutton(bar, text="Admin", bg=COLOR_TOPBAR_BG,
                            fg="#000000")
    menu_admin = tk.Menu(m_admin, tearoff=0)
    menu_admin.add_command(label="Admin Pantalla (cuentas de usuario)",
                           command=_cmd("Admin Pantalla"))
    m_admin.configure(menu=menu_admin)
    m_admin.pack(side="left", padx=10)

    # --- Alta de Datos ---
    m_alta = tk.Menubutton(bar, text="Alta de Datos", bg=COLOR_TOPBAR_BG,
                           fg="#000000")
    menu_alta = tk.Menu(m_alta, tearoff=0)
    menu_alta.add_command(label="Registrar Gastos", command=_cmd("Registrar Gastos"))
    menu_alta.add_separator()
    menu_alta.add_command(label="Planes", command=_cmd("ABM Planes"))
    menu_alta.add_command(label="Formas de Pago",
                          command=_cmd("ABM Formas de Pago"))
    menu_alta.add_command(label="Tipos de Gasto",
                          command=_cmd("ABM Tipos de Gasto"))
    menu_alta.add_command(label="Tipos de Ingreso",
                          command=_cmd("ABM Tipos de Ingreso"))
    m_alta.configure(menu=menu_alta)
    m_alta.pack(side="left", padx=10)

    # --- Gráficos Estadísticos (próximamente) ---
    for name in ("Gráficos Estadísticos", "Ayuda"):
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
        # Do not chain windows from inside the callback: just mark logout
        # and close. main() shows the login window once the mainloop ends.
        global _logout_requested
        _logout_requested = True
        window.destroy()

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
    if name == "Acceso Socios":
        acceso_socios.open_window(window)
        return
    if name == "Consultar Estados Socios":
        consultar_estados_socios.open_window(window)
        return
    if name == "Consultar Socios":
        consultar_socios.open_window(window)
        return
    if name == "Registrar Cobros":
        registrar_cobros.open_window(window, usuario=_current_user)
        return
    if name == "Anular Cobros":
        anular_cobros.open_window(window)
        return
    if name == "Registrar Socios":
        registrar_socio.open_window(window)
        return
    if name == "Registrar Deudas":
        registrar_deudas.open_window(window, usuario=_current_user)
        return
    if name in ("Consultar Caja", "Caja", "Ingresos"):
        caja.open_window(window)
        return
    if name in ("Historial de Cobros", "Historial Cobros"):
        historial_cobros.open_window(window)
        return
    if name == "Admin Pantalla":
        admin_cuentas.open_window(window)
        return
    if name in ("Registrar Gastos", "Registrar Gastos"):
        registrar_gastos.open_window(window, usuario=_current_user)
        return
    if name.startswith("ABM "):
        abm_generico.open_window(window, titulo=name[4:])
        return
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

    # The logo is transparent: give its label the gradient color at the
    # vertical position where it sits, so the PNG alpha blends seamlessly.
    steps = 40
    band_h = WINDOW_HEIGHT // steps
    mid = int((WINDOW_HEIGHT * 0.5) / band_h)
    logo_bg = interpolate_color(COLOR_AREA_TOP, COLOR_AREA_BOTTOM, mid / (steps - 1))

    logo = load_logo(max_w=420, max_h=400)
    if logo is not None:
        logo_label = tk.Label(area, image=logo, bg=logo_bg, bd=0)
        logo_label.place(relx=1.0, x=-40, rely=0.5, anchor="e")
        area.logo = logo
    else:
        tk.Label(
            area,
            text="ALTOS ROCA",
            bg=COLOR_AREA_TOP,
            fg="#5A6C8C",
            font=(font_family, 32, "bold"),
        ).place(relx=1.0, x=-40, rely=0.5, anchor="e")


def build_principal(window: tk.Tk, usuario: str) -> None:
    global _current_user
    _current_user = usuario
    available_fonts = {f.lower() for f in tkfont.families()}
    font_family = "Segoe UI" if "segoe ui" in available_fonts else "Helvetica"

    window.title(f"SG GYM - Sistema de Gestion de Gimnasios: ALTOS ROCA GYM - Usuario: {usuario}")
    window.resizable(False, False)
    center_window(window)

    build_topbar(window, usuario, font_family)
    build_sidebar(window, font_family)
    build_main_area(window, font_family)
    apply_app_icon(window)

    acceso_socios.open_window(window)


def main(usuario: str) -> None:
    global _logout_requested
    _logout_requested = False
    window = tk.Tk()
    build_principal(window, usuario)
    window.protocol("WM_DELETE_WINDOW", window.destroy)
    window.mainloop()
    if _logout_requested:
        # Principal is gone -> login must be visible (mandatory rule).
        _logout_requested = False
        login.main()
    else:
        # Ensure the process (and the PyInstaller onefile parent) dies cleanly.
        sys.exit(0)


if __name__ == "__main__":
    main("MARCO")
