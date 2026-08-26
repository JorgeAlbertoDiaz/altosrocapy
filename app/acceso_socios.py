"""Acceso Socios: persistent reception window (pure Tkinter)."""

import datetime
import os
import sqlite3
import tkinter as tk
import tkinter.font as tkfont

try:
    from app import db
    from app.resources import get_logo_path, apply_app_icon
except ImportError:
    import db
    from resources import get_logo_path, apply_app_icon

WINDOW_WIDTH = 800
WINDOW_HEIGHT = 600

COLOR_MAIN_BG = "#08142C"
COLOR_MAIN_BG_BOTTOM = "#0C1D3A"
COLOR_HEADER_BG = "#304A66"
COLOR_HEADER_FG = "#D9D9D9"
COLOR_INPUT_BG = "#FFFFFF"
COLOR_PANEL_BG = "#E7E8EB"
COLOR_TEXT_DARK = "#000000"
COLOR_PRIOR_MSG = "#4169E1"
COLOR_ENABLED = "#008000"
COLOR_DISABLED = "#FF0000"
COLOR_BUTTON_BG = "#314863"
COLOR_PHOTO_BG = "#000000"
COLOR_PHOTO_FG = "#FFFFFF"

LOGO_PATH = get_logo_path()

_singleton = {"window": None, "logo": None}


def _has_digits(value: str) -> bool:
    return any(c.isdigit() for c in value)


def _parse_date(raw):
    if not raw:
        return None
    return datetime.datetime.strptime(raw[:10], "%Y-%m-%d").date()


def query_socio(dni: str):
    """Look up a socio by Documento (fallback idSocio). Returns dict or None."""
    conn = db.get_connection()
    try:
        row = conn.execute(
            "SELECT idSocio, Apellidos, Nombres, Documento, Estado, id_Plan "
            "FROM tbSocios WHERE Documento = ?",
            (dni,),
        ).fetchone()
        if row is None and dni.isdigit():
            row = conn.execute(
                "SELECT idSocio, Apellidos, Nombres, Documento, Estado, id_Plan "
                "FROM tbSocios WHERE idSocio = ?",
                (dni,),
            ).fetchone()
        if row is None or not _has_digits(row["Documento"] or ""):
            return None
        socio = dict(row)

        plan = conn.execute(
            "SELECT Nomenclatura FROM tbPlan WHERE idPlan = ?",
            (socio["id_Plan"],),
        ).fetchone()
        socio["plan"] = plan["Nomenclatura"] if plan else "-"

        venc = conn.execute(
            "SELECT MAX(FechaVencimineto) AS v FROM tbPagos "
            "WHERE idSocio = ? AND FechaVencimineto IS NOT NULL",
            (socio["idSocio"],),
        ).fetchone()
        fecha_vto = _parse_date(venc["v"] if venc else None)
        hoy = datetime.date.today()
        socio["vencimiento"] = (
            fecha_vto.strftime("%d-%m-%Y") if fecha_vto else "-"
        )
        socio["habilitado"] = bool(fecha_vto and fecha_vto >= hoy)
        socio["estado"] = "HABILITADO" if socio["habilitado"] else "INHABILITADO"

        acceso = conn.execute(
            "SELECT FechaAcceso FROM tbSociosAcceso "
            "WHERE idSocio = ? AND FechaAcceso LIKE ? || '%' "
            "ORDER BY FechaAcceso DESC LIMIT 1",
            (socio["idSocio"], hoy.strftime("%Y-%m-%d")),
        ).fetchone()
        socio["ingreso_previo"] = (
            acceso["FechaAcceso"][11:19] if acceso else None
        )
        return socio
    except sqlite3.Error:
        return None
    finally:
        conn.close()


def _interpolate_color(start: str, end: str, t: float) -> str:
    r1, g1, b1 = (int(start[i:i + 2], 16) for i in (1, 3, 5))
    r2, g2, b2 = (int(end[i:i + 2], 16) for i in (1, 3, 5))
    return "#{:02x}{:02x}{:02x}".format(
        round(r1 + (r2 - r1) * t),
        round(g1 + (g2 - g1) * t),
        round(b1 + (b2 - b1) * t),
    )


def _draw_silhouette(canvas: tk.Canvas, w: int, h: int) -> None:
    """Draw a white head+shoulders silhouette on a black canvas."""
    canvas.create_oval(
        w // 2 - 25, 15, w // 2 + 25, 65,
        fill=COLOR_PHOTO_FG, outline=COLOR_PHOTO_FG,
    )
    canvas.create_arc(
        w // 2 - 55, 50, w // 2 + 55, 140,
        start=0, extent=180,
        style="pieslice",
        fill=COLOR_PHOTO_FG, outline=COLOR_PHOTO_FG,
    )


class AccesoSociosWindow(tk.Toplevel):
    def __init__(self, parent=None):
        super().__init__(parent) if parent else super().__init__()
        self.title("Acceso Socios")
        self.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        self.resizable(False, False)
        self.configure(bg=COLOR_MAIN_BG)
        self.protocol("WM_DELETE_WINDOW", self.withdraw)
        apply_app_icon(self)

        self.state = "waiting"
        self.current_socio = None
        self._logo_ref = None

        available_fonts = {f.lower() for f in tkfont.families(self)}
        light_family = (
            "Segoe UI Light" if "segoe ui light" in available_fonts
            else "Helvetica"
        )

        gradient_steps = 30
        band_h = WINDOW_HEIGHT // gradient_steps
        for i in range(gradient_steps):
            color = _interpolate_color(
                COLOR_MAIN_BG, COLOR_MAIN_BG_BOTTOM, i / (gradient_steps - 1)
            )
            tk.Frame(self, bg=color, height=band_h).place(
                x=0, y=i * band_h, relwidth=1.0, height=band_h + 1
            )

        header = tk.Frame(self, bg=COLOR_HEADER_BG, height=75)
        header.place(x=0, y=0, relwidth=1.0, height=75)

        logo = None
        if os.path.isfile(LOGO_PATH):
            try:
                logo = tk.PhotoImage(file=LOGO_PATH)
            except tk.TclError:
                logo = None
        if logo is not None:
            self._logo_ref = logo
            tk.Label(header, image=logo, bg=COLOR_HEADER_BG).place(x=12, rely=0.5, anchor="w")

        tk.Label(
            header,
            text="ACCESO SOCIOS",
            bg=COLOR_HEADER_BG,
            fg=COLOR_HEADER_FG,
            font=(light_family, 44),
        ).place(relx=0.5, rely=0.5, anchor="center")

        input_frame = tk.Frame(self, bg=COLOR_INPUT_BG, width=690, height=60)
        input_frame.place(x=(WINDOW_WIDTH - 690) // 2, y=91)
        input_frame.pack_propagate(False)

        vcmd = (self.register(lambda p: p == "" or p.isdigit()), "%P")
        self.entry = tk.Entry(
            input_frame,
            bg=COLOR_INPUT_BG,
            fg=COLOR_TEXT_DARK,
            font=("Helvetica", 24),
            justify="center",
            validate="key",
            validatecommand=vcmd,
            relief="flat",
            bd=0,
            highlightthickness=0,
        )
        self.entry.place(relwidth=1.0, relheight=1.0, x=4, y=4, width=-8, height=-8)
        self.entry.bind("<Return>", self._on_enter)

        panel = tk.Frame(self, bg=COLOR_PANEL_BG, width=690, height=280)
        panel.place(x=(WINDOW_WIDTH - 690) // 2, y=167)
        panel.pack_propagate(False)

        self.lbl_nombre = tk.Label(
            panel, text="", bg=COLOR_PANEL_BG, fg=COLOR_TEXT_DARK,
            font=("Helvetica", 18), anchor="w",
        )
        self.lbl_plan = tk.Label(
            panel, text="", bg=COLOR_PANEL_BG, fg=COLOR_TEXT_DARK,
            font=("Helvetica", 13), anchor="w",
        )
        self.lbl_vencimiento = tk.Label(
            panel, text="", bg=COLOR_PANEL_BG, fg=COLOR_TEXT_DARK,
            font=("Helvetica", 13), anchor="w",
        )
        self.lbl_previo = tk.Label(
            panel, text="", bg=COLOR_PANEL_BG, fg=COLOR_PRIOR_MSG,
            font=("Helvetica", 12), anchor="w",
        )
        self.lbl_estado = tk.Label(
            panel, text="", bg=COLOR_PANEL_BG,
            font=("Helvetica", 24, "bold"),
        )

        self.lbl_nombre.place(x=15, y=15, width=500)
        self.lbl_plan.place(x=15, y=55)
        self.lbl_vencimiento.place(x=15, y=80)
        self.lbl_previo.place(x=15, y=110)
        self.lbl_estado.place(x=15, y=170)

        photo_frame = tk.Frame(
            panel, bg=COLOR_PHOTO_BG, width=140, height=130,
            highlightthickness=1, highlightbackground="#888888",
        )
        photo_frame.place(x=535, y=15)

        silhouette_canvas = tk.Canvas(
            photo_frame, bg=COLOR_PHOTO_BG, width=140, height=130,
            highlightthickness=0, bd=0,
        )
        silhouette_canvas.place(relwidth=1.0, relheight=1.0)
        _draw_silhouette(silhouette_canvas, 140, 130)

        btn = tk.Button(
            self,
            text="VER SOCIO",
            bg=COLOR_BUTTON_BG,
            fg="#FFFFFF",
            activebackground="#3F5A7C",
            activeforeground="#FFFFFF",
            font=("Helvetica", 12, "bold"),
            relief="solid",
            borderwidth=1,
            cursor="hand2",
            command=self._open_consultar_socios,
        )
        btn.place(x=(WINDOW_WIDTH - 130) // 2, y=482, width=130, height=36)

    # -- state machine ---------------------------------------------------

    def _on_enter(self, _event=None):
        if self.state == "waiting":
            texto = self.entry.get().strip()
            if texto and texto.isdigit():
                self._show_result(query_socio(texto))
        elif self.state == "showing":
            self._clear_panel()
        self.entry.focus_set()

    def _show_result(self, socio):
        self.current_socio = socio
        self.entry.delete(0, "end")
        if socio is None:
            self.lbl_nombre.configure(text="SOCIO NO ENCONTRADO")
            self.lbl_estado.configure(text="", fg=COLOR_TEXT_DARK)
            self.state = "showing"
            return
        nombre = f"{(socio['Apellidos'] or '').upper()}, {(socio['Nombres'] or '').upper()}"
        self.lbl_nombre.configure(text=nombre)
        self.lbl_plan.configure(text=f"Plan: {socio['plan']}")
        self.lbl_vencimiento.configure(text=f"Vencimiento: {socio['vencimiento']}")
        if socio.get("ingreso_previo"):
            self.lbl_previo.configure(
                text=f"Ya registra ingreso al dia de hoy, horas: {socio['ingreso_previo']}"
            )
        else:
            self.lbl_previo.configure(text="")
        color = COLOR_ENABLED if socio["habilitado"] else COLOR_DISABLED
        estado = "SOCIO HABILITADO" if socio["habilitado"] else "SOCIO INHABILITADO"
        self.lbl_estado.configure(text=estado, fg=color)
        self.state = "showing"

    def _clear_panel(self):
        self.current_socio = None
        self.lbl_nombre.configure(text="")
        self.lbl_plan.configure(text="")
        self.lbl_vencimiento.configure(text="")
        self.lbl_previo.configure(text="")
        self.lbl_estado.configure(text="")
        self.state = "waiting"

    def _open_consultar_socios(self):
        top = tk.Toplevel(self)
        top.title("Consultar Socios")
        top.geometry("900x600")
        top.configure(bg="#F0F0F0")
        top.bind("<Escape>", lambda _e: top.destroy())
        tk.Label(
            top, text="[Módulo en construcción]",
            bg="#F0F0F0", fg="#333333", font=("Helvetica", 14),
        ).place(relx=0.5, rely=0.48, anchor="center")
        socio = self.current_socio
        detalle = (
            f"Socio actual: #{socio['idSocio']} - "
            f"{(socio['Apellidos'] or '').upper()}, {(socio['Nombres'] or '').upper()}"
            if socio
            else "Socio actual: (ninguno)"
        )
        tk.Label(
            top, text=detalle,
            bg="#F0F0F0", fg="#555555", font=("Helvetica", 11),
        ).place(relx=0.5, rely=0.56, anchor="center")

    def focus_input(self):
        try:
            self.deiconify()
            self.lift()
            self.entry.focus_set()
        except tk.TclError:
            pass


def open_window(parent=None) -> AccesoSociosWindow:
    """Show the singleton window; reopen (deiconify) if hidden.

    If the previous instance died together with its Tk root (login ->
    principal transition), a fresh one is created on the new root.
    """
    win = _singleton["window"]
    if win is not None:
        try:
            alive = win.winfo_exists()
        except tk.TclError:
            alive = False
        if alive:
            win.focus_input()
            return win
        _singleton["window"] = None
    win = AccesoSociosWindow(parent)
    _singleton["window"] = win
    win.focus_input()
    return win


if __name__ == "__main__":
    root = tk.Tk()
    root.withdraw()
    open_window(root)
    root.mainloop()
