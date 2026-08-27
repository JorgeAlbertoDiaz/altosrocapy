"""Registrar Gastos — alta de gastos generales (tbGastosGenerales).

Los gastos se ven en el reporte de Caja (columna Debe), pero no había forma de
cargarlos. Esta ventana permite registrarlos.

Estética: WinForms / VB.NET clásica. El ID se autogenera (MAX + 1).
"""

import datetime
import tkinter as tk
from tkinter import ttk, messagebox

try:
    from tkcalendar import DateEntry
except ImportError:
    DateEntry = None

try:
    from app import db
except ImportError:
    import db

# ── Constants ─────────────────────────────────────────────────────────────

W, H = 600, 520
BG = "#F0F0F0"
FG = "#000000"
FG_DISABLED = "#777777"
FG_LABEL = "#000000"
ENTRY_BG = "#FFFFFF"
ENTRY_READONLY_BG = "#E8E8E8"
BTN_BLUE = "#3B6FA0"
BTN_BLUE_ACTIVE = "#2D5A85"
SEL_BG = "#0078D7"
FN = ("Helvetica", 9)
FN_B = ("Helvetica", 9, "bold")


# ── Helpers ───────────────────────────────────────────────────────────────

def _next_id_gasto():
    conn = db.get_connection()
    try:
        r = conn.execute(
            "SELECT MAX(CAST(idGastos AS INTEGER)) FROM tbGastosGenerales "
            "WHERE idGastos GLOB '[0-9]*'").fetchone()
        return str((r[0] or 0) + 1)
    finally:
        conn.close()


def _load_tipos_gastos():
    conn = db.get_connection()
    try:
        rows = conn.execute(
            "SELECT idTipoGasto, Descripcion FROM tbTiposGastos "
            "WHERE (Eliminado IS NULL OR Eliminado != '1') "
            "  AND idTipoGasto GLOB '[0-9]*' "
            "ORDER BY CAST(idTipoGasto AS INTEGER)").fetchall()
        return [(str(r[0]), r[1]) for r in rows]
    finally:
        conn.close()


def _load_tipos_pago():
    conn = db.get_connection()
    try:
        rows = conn.execute(
            "SELECT Id, Descripcion FROM tb_TipoPago "
            "WHERE Id GLOB '[0-9]*' ORDER BY CAST(Id AS INTEGER)").fetchall()
        return [(str(r[0]), r[1]) for r in rows]
    finally:
        conn.close()


def _registrar_gasto(id_tipo, detalle, importe, fecha, usuario, id_tipo_pago):
    conn = db.get_connection()
    try:
        new_id = _next_id_gasto()
        conn.execute(
            "INSERT INTO tbGastosGenerales "
            "(idGastos, idTipoGastos, Detalle, Importe, Fecha, Eliminado, "
            " Usuario, idTipoPago) "
            "VALUES (?, ?, ?, ?, ?, '0', ?, ?)",
            (new_id, id_tipo, detalle, f"{importe:.2f}", fecha, usuario,
             id_tipo_pago))
        conn.commit()
        return new_id
    finally:
        conn.close()


def _gastos_hoy(fecha_d, fecha_h):
    conn = db.get_connection()
    try:
        rows = conn.execute(
            "SELECT g.idGastos, t.Descripcion AS tipo, g.Detalle, g.Importe, "
            "  g.Fecha, g.Usuario "
            "FROM tbGastosGenerales g "
            "LEFT JOIN tbTiposGastos t ON t.idTipoGasto = g.idTipoGastos "
            "WHERE (g.Eliminado IS NULL OR g.Eliminado != '1') "
            "  AND g.Fecha >= ? AND g.Fecha <= ? "
            "ORDER BY g.Fecha DESC LIMIT 100",
            (fecha_d, fecha_h)).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def _fmt(raw):
    if not raw:
        return ""
    try:
        return datetime.datetime.strptime(str(raw)[:19],
                                          "%Y-%m-%d %H:%M:%S").strftime(
                                              "%d/%m/%Y %H:%M")
    except (ValueError, TypeError):
        return str(raw)


# ── Main Window ───────────────────────────────────────────────────────────

class RegistrarGastosWindow(tk.Toplevel):
    def __init__(self, parent=None, usuario=""):
        super().__init__(parent)
        self.title("Registrar Gastos")
        self.geometry(f"{W}x{H}")
        self.resizable(False, False)
        self.configure(bg=BG)
        self.bind("<Escape>", lambda _: self.destroy())

        self._tipos_gasto = _load_tipos_gastos()
        self._tipos_pago = _load_tipos_pago()
        self.usuario_logueado = usuario or "Admin"
        self._build()
        self._refresh_hoy()
        self.entry_detalle.focus_set()

    def _build(self):
        # === FORM GROUPBOX ===
        frm = tk.LabelFrame(
            self, text=" Datos del Gasto ", bg=BG, font=FN_B, fg="#333333",
            relief="groove", bd=2, labelanchor="nw")
        frm.place(x=15, y=15, width=W - 30, height=240)

        # Tipo de Gasto
        tk.Label(frm, text="Tipo de Gasto:", bg=BG, font=FN,
                 fg=FG_LABEL).place(x=20, y=25)
        self.tipo_var = tk.StringVar()
        self.combo_tipo = ttk.Combobox(
            frm, textvariable=self.tipo_var, state="readonly", width=30,
            font=FN)
        if self._tipos_gasto:
            self.combo_tipo["values"] = [t[1] for t in self._tipos_gasto]
            self.combo_tipo.current(0)
        self.combo_tipo.place(x=130, y=20, width=250, height=24)

        # Fecha
        tk.Label(frm, text="Fecha:", bg=BG, font=FN, fg=FG_LABEL).place(x=410, y=25)
        if DateEntry is not None:
            self.dt_fecha = DateEntry(frm, width=12, background="#3B6FA0",
                                      foreground="white", borderwidth=1,
                                      date_pattern="dd/mm/yyyy", font=FN)
            self.dt_fecha.place(x=410, y=18, width=140, height=24)
        else:
            self.dt_fecha = None
            self.fecha_var = tk.StringVar(
                value=datetime.date.today().strftime("%d/%m/%Y"))
            self.entry_fecha = tk.Entry(
                frm, textvariable=self.fecha_var, bg=ENTRY_BG, fg=FG, font=FN,
                relief="solid", bd=1)
            self.entry_fecha.place(x=410, y=18, width=140, height=24)

        # Importe
        tk.Label(frm, text="Importe:", bg=BG, font=FN, fg=FG_LABEL).place(x=20, y=65)
        self.importe_var = tk.StringVar()
        self.entry_importe = tk.Entry(
            frm, textvariable=self.importe_var, bg=ENTRY_BG, fg=FG, font=FN,
            relief="solid", bd=1)
        self.entry_importe.place(x=130, y=60, width=150, height=24)

        # Forma de Pago
        tk.Label(frm, text="Forma de Pago:", bg=BG, font=FN,
                 fg=FG_LABEL).place(x=20, y=105)
        self.pago_var = tk.StringVar()
        self.combo_pago = ttk.Combobox(
            frm, textvariable=self.pago_var, state="readonly", width=20,
            font=FN)
        if self._tipos_pago:
            self.combo_pago["values"] = [p[1] for p in self._tipos_pago]
            self.combo_pago.current(0)  # Efectivo
        self.combo_pago.place(x=130, y=100, width=150, height=24)

        # Usuario (no editable: siempre es el usuario logueado)
        tk.Label(frm, text="Usuario:", bg=BG, font=FN, fg=FG_LABEL).place(x=20, y=145)
        self.usuario_var = tk.StringVar(value=self.usuario_logueado)
        self.entry_usuario = tk.Entry(
            frm, textvariable=self.usuario_var, state="readonly",
            readonlybackground=ENTRY_READONLY_BG, fg=FG_DISABLED, font=FN,
            relief="solid", bd=1, cursor="arrow")
        self.entry_usuario.place(x=130, y=140, width=150, height=24)

        # Detalle (wide)
        tk.Label(frm, text="Detalle:", bg=BG, font=FN, fg=FG_LABEL).place(x=20, y=185)
        self.detalle_var = tk.StringVar()
        self.entry_detalle = tk.Entry(
            frm, textvariable=self.detalle_var, bg=ENTRY_BG, fg=FG, font=FN,
            relief="solid", bd=1)
        self.entry_detalle.place(x=130, y=180, width=430, height=24)

        # === BOTONES ===
        self.btn_guardar = tk.Button(
            self, text="REGISTRAR GASTO", bg=BTN_BLUE, fg="#FFF", font=FN_B,
            relief="flat", activebackground=BTN_BLUE_ACTIVE, cursor="hand2",
            command=self._on_guardar)
        self.btn_guardar.place(x=15, y=270, width=170, height=32)

        tk.Button(self, text="Salir", bg="#999", fg="#FFF", font=FN_B,
                  relief="flat", activebackground="#777", cursor="hand2",
                  command=self.destroy).place(x=W - 100, y=270, width=85,
                                              height=32)

        # === GRID: gastos del día ===
        frm_grid = tk.LabelFrame(
            self, text=" Gastos registrados (hoy) ", bg=BG, font=FN_B,
            fg="#333333", relief="groove", bd=2, labelanchor="nw")
        frm_grid.place(x=15, y=315, width=W - 30, height=185)

        cols = ("id", "tipo", "detalle", "importe", "fecha", "usuario")
        self.tree = ttk.Treeview(frm_grid, columns=cols, show="headings",
                                 selectmode="browse")
        self.tree.heading("id", text="ID")
        self.tree.heading("tipo", text="Tipo")
        self.tree.heading("detalle", text="Detalle")
        self.tree.heading("importe", text="Importe")
        self.tree.heading("fecha", text="Fecha")
        self.tree.heading("usuario", text="Usuario")
        self.tree.column("id", width=50, anchor="center", stretch=False)
        self.tree.column("tipo", width=110, stretch=False)
        self.tree.column("detalle", width=190, stretch=True)
        self.tree.column("importe", width=80, anchor="e", stretch=False)
        self.tree.column("fecha", width=120, stretch=False)
        self.tree.column("usuario", width=70, center=False, stretch=False)

        style = ttk.Style(self)
        style.configure("GR.Treeview", rowheight=22, font=FN,
                        background="#FFF", fieldbackground="#FFF")
        style.configure("GR.Treeview.Heading", font=FN_B)
        style.map("GR.Treeview",
                  background=[("selected", SEL_BG)],
                  foreground=[("selected", "#FFF")])
        self.tree.configure(style="GR.Treeview")

        vsb = ttk.Scrollbar(frm_grid, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.place(x=0, y=0, relwidth=0.97, relheight=1.0)
        vsb.place(relx=0.975, y=0, relheight=1.0)

    # ── Today's gastos grid ───────────────────────────────────────────────

    def _rango_hoy(self):
        d = datetime.date.today()
        return (f"{d:%Y-%m-%d} 00:00:00", f"{d:%Y-%m-%d} 23:59:59")

    def _refresh_hoy(self):
        fd, fh = self._rango_hoy()
        rows = _gastos_hoy(fd, fh)
        self.tree.delete(*self.tree.get_children())
        for r in rows:
            self.tree.insert("", "end", values=(
                r["idGastos"], r["tipo"] or "", r["Detalle"] or "",
                f"{float(r['Importe'] or 0):,.0f}",
                _fmt(r["Fecha"]), r["Usuario"] or ""))

    # ── Guardar ───────────────────────────────────────────────────────────

    def _on_guardar(self):
        detalle = self.detalle_var.get().strip()
        importe = self.importe_var.get().strip()
        if not detalle:
            messagebox.showwarning("Guardar", "El detalle es obligatorio.",
                                   parent=self)
            self.entry_detalle.focus_set()
            return
        try:
            importe_f = float(importe)
        except (ValueError, TypeError):
            messagebox.showwarning("Guardar", "Importe inválido.", parent=self)
            self.entry_importe.focus_set()
            return
        if importe_f <= 0:
            messagebox.showwarning("Guardar", "El importe debe ser mayor a 0.",
                                   parent=self)
            self.entry_importe.focus_set()
            return

        tipo_idx = self.combo_tipo.current()
        if tipo_idx < 0:
            messagebox.showwarning("Guardar", "Seleccione el tipo de gasto.",
                                   parent=self)
            return
        id_tipo = self._tipos_gasto[tipo_idx][0]

        pago_idx = self.combo_pago.current()
        id_pago = self._tipos_pago[pago_idx][0] if pago_idx >= 0 else "1"

        if DateEntry is not None:
            fecha = self.dt_fecha.get_date().strftime("%Y-%m-%d %H:%M:%S.000")
        else:
            try:
                parts = self.fecha_var.get().split("/")
                fecha = datetime.datetime(
                    int(parts[2]), int(parts[1]), int(parts[0])
                ).strftime("%Y-%m-%d %H:%M:%S.000")
            except (ValueError, IndexError):
                messagebox.showwarning("Guardar", "Fecha inválida.", parent=self)
                return

        try:
            new_id = _registrar_gasto(
                id_tipo, detalle, importe_f, fecha,
                self.usuario_var.get().strip() or "Admin", id_pago)
        except Exception as e:
            messagebox.showerror("Error", f"Error al registrar gasto: {e}",
                                 parent=self)
            return

        messagebox.showinfo(
            "Éxito", f"Gasto registrado.\n\nID: {new_id}\nImporte: ${importe_f:,.2f}",
            parent=self)
        self.importe_var.set("")
        self.detalle_var.set("")
        self._refresh_hoy()


def open_window(parent=None, usuario=""):
    return RegistrarGastosWindow(parent, usuario=usuario)


if __name__ == "__main__":
    root = tk.Tk()
    root.withdraw()
    open_window(root, "Admin")
    root.mainloop()
