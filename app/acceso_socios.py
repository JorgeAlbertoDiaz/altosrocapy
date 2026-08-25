"""Acceso Socios: persistent reception window (pure Tkinter)."""

import datetime
import os
import sqlite3
import tkinter as tk

try:
    from app import db
except ImportError:  # dev / frozen fallback
    import db

WINDOW_WIDTH = 780
WINDOW_HEIGHT = 620

COLOR_HEADER_BG = "#2D4864"
COLOR_HEADER_FG = "#D7D7D7"
COLOR_PANEL_BG = "#E7E8EB"
COLOR_TEXT_DARK = "#222222"
COLOR_PRIOR_MSG = "#456FE5"
COLOR_ENABLED = "#008000"
COLOR_DISABLED = "#FF0000"
COLOR_BUTTON_BG = "#314863"

LOGO_PATH = os.path.join(os.path.dirname(__file__), "..", "temps", "logo.png")

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


class AccesoSociosWindow(tk.Toplevel):
    def __init__(self, parent=None):
        super().__init__(parent) if parent else super().__init__()
        self.title("Acceso Socios")
        self.resizable(False, False)
        self.protocol("WM_DELETE_WINDOW", self.withdraw)

        self.state = "waiting"
        self.current_socio = None
        self._logo_ref = None

        available_fonts = {f.lower() for f in tkfont_families(self)}
        light_family = (
            "Segoe UI Light" if "segoe ui light" in available_fonts else "Helvetica"
        )

        header = tk.Frame(self, bg=COLOR_HEADER_BG, height=75)
        header.pack(side="top", fill="x")
        header.pack_propagate(False)

        logo = None
        if os.path.isfile(LOGO_PATH):
            try:
                logo = tk.PhotoImage(file=LOGO_PATH)
            except tk.TclError:
                logo = None
        if logo is not None:
            self._logo_ref = logo
            tk.Label(header, image=logo, bg=COLOR_HEADER_BG).pack(
                side="left", padx=12
            )
        else:
            tk.Label(
                header,
                text="ALTOS ROCA",
                bg=COLOR_HEADER_BG,
                fg="#FFFFFF",
                font=("Helvetica", 14, "bold"),
            ).pack(side="left", padx=12)

        tk.Label(
            header,
            text="ACCESO SOCIOS",
            bg=COLOR_HEADER_BG,
            fg=COLOR_HEADER_FG,
            font=(light_family, 40),
        ).place(relx=0.5, rely=0.5, anchor="center")

        input_wrap = tk.Frame(self, bg="#FFFFFF", bd=0)
        input_wrap.pack(pady=(15, 10))
        input_inner = tk.Frame(input_wrap, bg=COLOR_PANEL_BG,
                               width=690, height=60)
        input_inner.pack_propagate(False)
        input_inner.pack()

        vcmd = (self.register(lambda p: p == "" or p.isdigit()), "%P")
        self.entry = tk.Entry(
            input_inner,
            bg=COLOR_PANEL_BG,
            fg=COLOR_TEXT_DARK,
            font=("Helvetica", 22),
            justify="center",
            validate="key",
            validatecommand=vcmd,
            relief="flat",
        )
        self.entry.pack(fill="both", expand=True, padx=2, pady=2)
        self.entry.bind("<Return>", self._on_enter)

        panel_wrap = tk.Frame(self, bg="#FFFFFF")
        panel_wrap.pack(pady=5)
        panel = tk.Frame(panel_wrap, bg=COLOR_PANEL_BG, width=690, height=280)
        panel.pack_propagate(False)
        panel.pack()

        self.lbl_nombre = tk.Label(
            panel, text="", bg=COLOR_PANEL_BG, fg=COLOR_TEXT_DARK,
            font=("Helvetica", 18, "bold"), anchor="w",
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
            font=("Helvetica", 26, "bold"),
        )
        self.lbl_nombre.place(x=20, y=25, width=500)
        self.lbl_plan.place(x=20, y=70)
        self.lbl_vencimiento.place(x=20, y=95)
        self.lbl_previo.place(x=20, y=130)
        self.lbl_estado.place(x=20, y=200)

        photo_frame = tk.Frame(panel, bg="#BFC4CC", width=140, height=130)
        photo_frame.place(relx=1.0, x=-15, y=15, anchor="ne")
        tk.Label(
            photo_frame, text="SIN FOTO", bg="#BFC4CC", fg="#666666",
            font=("Helvetica", 11),
        ).place(relx=0.5, rely=0.5, anchor="center")

        btn = tk.Button(
            self,
            text="VER SOCIO",
            bg=COLOR_BUTTON_BG,
            fg="#FFFFFF",
            activebackground="#3F5A7C",
            activeforeground="#FFFFFF",
            font=("Helvetica", 12, "bold"),
            relief="flat",
            cursor="hand2",
            command=self._open_consultar_socios,
        )
        btn.pack(pady=(12, 0), ipadx=24, ipady=6)

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
                text=f"Ya registró ingreso al día de hoy {socio['ingreso_previo']}"
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


def tkfont_families(widget):
    import tkinter.font as tkfont
    return tkfont.families(widget)


if __name__ == "__main__":  # manual smoke run
    root = tk.Tk()
    root.withdraw()
    open_window(root)
    root.mainloop()
