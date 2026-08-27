"""Gestionar Gastos — ABM de gastos generales con filtro por rango de fechas.

Ventana dedicada a la gestión (edición y baja física) de los gastos cargados
en tbGastosGenerales. Se elige un rango de fechas (default: hoy completo) y se
listan los gastos en un grid; al seleccionar uno se permite modificarlo o
borrarlo físicamente.

Estética: WinForms / VB.NET clásica. La baja es FÍSICA (DELETE) porque el
sistema legacy no mantenía "papelera" para gastos; no hay columna Eliminado en
el flujo de gestión de gastos.

Se reutilizan los helpers de datos de registrar_gastos (_load_tipos_gastos,
_load_tipos_pago, _fmt) para no duplicar lógica. La consulta por rango propia
incluye el JOIN con tbTiposGastos y el idTipoPago para poder editar.
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
    from app.registrar_gastos import _fmt, _load_tipos_gastos, _load_tipos_pago
except ImportError:
    import db
    from registrar_gastos import _fmt, _load_tipos_gastos, _load_tipos_pago

# ── Constants ─────────────────────────────────────────────────────────────

W, H = 780, 600
BG = "#F0F0F0"
FG = "#000000"
FG_LABEL = "#000000"
FG_DISABLED = "#777777"
ENTRY_BG = "#FFFFFF"
ENTRY_READONLY_BG = "#E8E8E8"
BTN_BLUE = "#3B6FA0"
BTN_BLUE_ACTIVE = "#2D5A85"
BTN_RED = "#C0392B"
BTN_RED_ACTIVE = "#A93226"
BTN_GRAY = "#888888"
BTN_GRAY_ACTIVE = "#666666"
BTN_GREEN = "#2E8B57"
BTN_GREEN_ACTIVE = "#246B43"
SEL_BG = "#0078D7"
FN = ("Helvetica", 9)
FN_B = ("Helvetica", 9, "bold")


# ── Data helpers ──────────────────────────────────────────────────────────

def _gastos_rango(fecha_d, fecha_h):
    conn = db.get_connection()
    try:
        rows = conn.execute(
            "SELECT g.idGastos, g.idTipoGastos, t.Descripcion AS tipo, "
            "  g.Detalle, g.Importe, g.Fecha, g.Usuario, g.idTipoPago "
            "FROM tbGastosGenerales g "
            "LEFT JOIN tbTiposGastos t ON t.idTipoGasto = g.idTipoGastos "
            "WHERE (g.Eliminado IS NULL OR g.Eliminado != '1') "
            "  AND g.Fecha >= ? AND g.Fecha <= ? "
            "ORDER BY g.Fecha DESC",
            (fecha_d, fecha_h)).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def _update_gasto(id_gasto, id_tipo, detalle, importe, fecha, id_tipo_pago):
    conn = db.get_connection()
    try:
        conn.execute(
            "UPDATE tbGastosGenerales "
            "SET idTipoGastos=?, Detalle=?, Importe=?, Fecha=?, idTipoPago=? "
            "WHERE idGastos=?",
            (str(id_tipo), detalle, f"{float(importe):.2f}", fecha,
             str(id_tipo_pago), str(id_gasto)))
        conn.commit()
    finally:
        conn.close()


def _delete_gasto(id_gasto):
    conn = db.get_connection()
    try:
        conn.execute("DELETE FROM tbGastosGenerales WHERE idGastos=?",
                     (str(id_gasto),))
        conn.commit()
    finally:
        conn.close()


# ── Main Window ───────────────────────────────────────────────────────────

class GestionarGastosWindow(tk.Toplevel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.title("Gestionar Gastos")
        self.geometry(f"{W}x{H}")
        self.resizable(False, False)
        self.configure(bg=BG)
        self.bind("<Escape>", lambda _: self.destroy())

        self._tipos_gasto = _load_tipos_gastos()
        self._tipos_pago = _load_tipos_pago()
        self.current_id = None
        self._build()
        self._set_rango_hoy()
        self._refresh_grid()
        self._new_edit()

    # ── Build ─────────────────────────────────────────────────────────────

    def _build(self):
        # === FILTRO DE RANGO DE FECHAS ===
        frm_filtro = tk.LabelFrame(
            self, text=" Rango de Fechas ", bg=BG, font=FN_B, fg="#333333",
            relief="groove", bd=2, labelanchor="nw")
        frm_filtro.place(x=15, y=12, width=W - 30, height=72)

        tk.Label(frm_filtro, text="Desde:", bg=BG, font=FN,
                 fg=FG_LABEL).place(x=20, y=30)
        if DateEntry is not None:
            self.dt_desde = DateEntry(frm_filtro, width=12,
                                      background=BTN_BLUE, foreground="white",
                                      borderwidth=1, date_pattern="dd/mm/yyyy",
                                      font=FN)
            self.dt_desde.place(x=70, y=24, width=120, height=24)
        else:
            self.desde_var = tk.StringVar(
                value=datetime.date.today().strftime("%d/%m/%Y"))
            self.dt_desde = None
            self.entry_desde = tk.Entry(
                frm_filtro, textvariable=self.desde_var, bg=ENTRY_BG, fg=FG,
                font=FN, relief="solid", bd=1)
            self.entry_desde.place(x=70, y=24, width=120, height=24)

        tk.Label(frm_filtro, text="Hasta:", bg=BG, font=FN,
                 fg=FG_LABEL).place(x=210, y=30)
        if DateEntry is not None:
            self.dt_hasta = DateEntry(frm_filtro, width=12,
                                      background=BTN_BLUE, foreground="white",
                                      borderwidth=1, date_pattern="dd/mm/yyyy",
                                      font=FN)
            self.dt_hasta.place(x=260, y=24, width=120, height=24)
        else:
            self.hasta_var = tk.StringVar(
                value=datetime.date.today().strftime("%d/%m/%Y"))
            self.dt_hasta = None
            self.entry_hasta = tk.Entry(
                frm_filtro, textvariable=self.hasta_var, bg=ENTRY_BG, fg=FG,
                font=FN, relief="solid", bd=1)
            self.entry_hasta.place(x=260, y=24, width=120, height=24)

        self.btn_buscar = tk.Button(
            frm_filtro, text="Buscar", bg=BTN_BLUE, fg="#FFF", font=FN_B,
            relief="flat", activebackground=BTN_BLUE_ACTIVE, cursor="hand2",
            command=self._on_buscar)
        self.btn_buscar.place(x=420, y=24, width=90, height=26)

        # === GRID ===
        frm_grid = tk.Frame(self, bg="#E8E8E8")
        frm_grid.place(x=15, y=95, width=W - 30, height=260)

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
        self.tree.column("detalle", width=260, stretch=True)
        self.tree.column("importe", width=90, anchor="e", stretch=False)
        self.tree.column("fecha", width=130, stretch=False)
        self.tree.column("usuario", width=80, anchor="center", stretch=False)

        style = ttk.Style(self)
        style.configure("GG.Treeview", rowheight=22, font=FN,
                        background="#FFF", fieldbackground="#FFF")
        style.configure("GG.Treeview.Heading", font=FN_B)
        style.map("GG.Treeview",
                  background=[("selected", SEL_BG)],
                  foreground=[("selected", "#FFF")])
        self.tree.configure(style="GG.Treeview")

        vsb = ttk.Scrollbar(frm_grid, orient="vertical",
                            command=self.tree.yview)
        vsb2 = ttk.Scrollbar(frm_grid, orient="horizontal",
                             command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set,
                            xscrollcommand=vsb2.set)
        self.tree.place(x=0, y=0, relwidth=0.97, relheight=1.0)
        vsb.place(relx=0.975, y=0, relheight=1.0)
        vsb2.place(relx=0, rely=1.0, relwidth=0.97, relheight=10)
        self.tree.bind("<<TreeviewSelect>>", self._on_select)

        # === FORM DE EDICIÓN ===
        frm_edit = tk.LabelFrame(
            self, text=" Edición del Gasto Seleccionado ", bg=BG, font=FN_B,
            fg="#333333", relief="groove", bd=2, labelanchor="nw")
        frm_edit.place(x=15, y=365, width=W - 30, height=190)

        tk.Label(frm_edit, text="Tipo de Gasto:", bg=BG, font=FN,
                 fg=FG_LABEL).place(x=20, y=30)
        self.combo_tipo = ttk.Combobox(frm_edit, state="readonly", width=26,
                                       font=FN)
        self.combo_tipo["values"] = [t[1] for t in self._tipos_gasto]
        self.combo_tipo.place(x=130, y=24, width=230, height=24)

        tk.Label(frm_edit, text="Forma de Pago:", bg=BG, font=FN,
                 fg=FG_LABEL).place(x=400, y=30)
        self.combo_pago = ttk.Combobox(frm_edit, state="readonly", width=20,
                                       font=FN)
        self.combo_pago["values"] = [p[1] for p in self._tipos_pago]
        self.combo_pago.place(x=520, y=24, width=200, height=24)

        tk.Label(frm_edit, text="Detalle:", bg=BG, font=FN,
                 fg=FG_LABEL).place(x=20, y=70)
        self.entry_detalle = tk.Entry(frm_edit, bg=ENTRY_BG, fg=FG, font=FN,
                                      relief="solid", bd=1)
        self.entry_detalle.place(x=130, y=64, width=590, height=24)

        tk.Label(frm_edit, text="Importe:", bg=BG, font=FN,
                 fg=FG_LABEL).place(x=20, y=110)
        self.entry_importe = tk.Entry(frm_edit, bg=ENTRY_BG, fg=FG, font=FN,
                                      relief="solid", bd=1)
        self.entry_importe.place(x=130, y=104, width=150, height=24)

        tk.Label(frm_edit, text="Fecha:", bg=BG, font=FN,
                 fg=FG_LABEL).place(x=310, y=110)
        if DateEntry is not None:
            self.dt_fecha = DateEntry(frm_edit, width=12, background=BTN_BLUE,
                                      foreground="white", borderwidth=1,
                                      date_pattern="dd/mm/yyyy", font=FN)
            self.dt_fecha.place(x=380, y=104, width=140, height=24)
        else:
            self.dt_fecha = None
            self.fecha_var = tk.StringVar()
            self.entry_fecha = tk.Entry(
                frm_edit, textvariable=self.fecha_var, bg=ENTRY_BG, fg=FG,
                font=FN, relief="solid", bd=1)
            self.entry_fecha.place(x=380, y=104, width=140, height=24)

        self.btn_guardar = tk.Button(
            frm_edit, text="Guardar Cambios", bg=BTN_GREEN, fg="#FFF",
            font=FN_B, relief="flat", activebackground=BTN_GREEN_ACTIVE,
            cursor="hand2", command=self._on_guardar, state="disabled")
        self.btn_guardar.place(x=560, y=104, width=160, height=26)

        self.btn_eliminar = tk.Button(
            frm_edit, text="Eliminar", bg=BTN_RED, fg="#FFF", font=FN_B,
            relief="flat", activebackground=BTN_RED_ACTIVE, cursor="hand2",
            command=self._on_eliminar, state="disabled")
        self.btn_eliminar.place(x=560, y=140, width=160, height=26)

        self.btn_nuevo = tk.Button(
            frm_edit, text="Nuevo", bg=BTN_GRAY, fg="#FFF", font=FN_B,
            relief="flat", activebackground=BTN_GRAY_ACTIVE, cursor="hand2",
            command=self._new_edit)
        self.btn_nuevo.place(x=440, y=140, width=100, height=26)

    # ── Rangos / grid ─────────────────────────────────────────────────────

    def _set_rango_hoy(self):
        d = datetime.date.today()
        if DateEntry is not None:
            self.dt_desde.set_date(d)
            self.dt_hasta.set_date(d)
        else:
            self.desde_var.set(d.strftime("%d/%m/%Y"))
            self.hasta_var.set(d.strftime("%d/%m/%Y"))

    def _rango_actual(self):
        """Return (desde, hasta) as 'YYYY-MM-DD HH:MM:SS' strings."""
        if DateEntry is not None:
            d = self.dt_desde.get_date()
            h = self.dt_hasta.get_date()
            return (f"{d:%Y-%m-%d} 00:00:00", f"{h:%Y-%m-%d} 23:59:59")
        try:
            parts_d = self.desde_var.get().split("/")
            parts_h = self.hasta_var.get().split("/")
            d = datetime.datetime(int(parts_d[2]), int(parts_d[1]),
                                  int(parts_d[0]))
            h = datetime.datetime(int(parts_h[2]), int(parts_h[1]),
                                  int(parts_h[0]))
            return (d.strftime("%Y-%m-%d %H:%M:%S"),
                    h.strftime("%Y-%m-%d %H:%M:%S"))
        except (ValueError, IndexError):
            messagebox.showwarning("Buscar", "Fechas inválidas.", parent=self)
            return None

    def _refresh_grid(self):
        rango = self._rango_actual()
        if rango is None:
            return
        rows = _gastos_rango(*rango)
        self.tree.delete(*self.tree.get_children())
        for r in rows:
            self.tree.insert("", "end", values=(
                r["idGastos"], r["tipo"] or "", r["Detalle"] or "",
                f"{float(r['Importe'] or 0):.0f}",
                _fmt(r["Fecha"]), r["Usuario"] or ""))

    def _on_buscar(self):
        self._refresh_grid()
        self._new_edit()

    # ── Selection / state ─────────────────────────────────────────────────

    def _on_select(self, _event):
        sel = self.tree.selection()
        if not sel:
            return
        vals = self.tree.item(sel[0], "values")
        # vals: id, tipo, detalle, importe, fecha, usuario
        self.current_id = str(vals[0])

        ti = next((i for i, (_, t) in enumerate(self._tipos_gasto)
                   if t == vals[1]), -1)
        self.combo_tipo.current(ti if ti >= 0 else 0)

        pi = next((i for i, (_, p) in enumerate(self._tipos_pago)
                   if str(p) == str(self._tipo_pago_desc(vals))), -1)
        self.combo_pago.current(pi if pi >= 0 else 0)

        self.entry_detalle.delete(0, "end")
        self.entry_detalle.insert(0, vals[2] if vals[2] else "")
        self.entry_importe.delete(0, "end")
        self.entry_importe.insert(0, vals[3] if vals[3] else "")
        if DateEntry is not None:
            self.dt_fecha.set_date(datetime.datetime.strptime(
                str(self._fecha_sql(vals[4]))[:10], "%Y-%m-%d").date())
        else:
            self.fecha_var.set(str(self._fecha_sql(vals[4]))[:10])

        self.btn_guardar.configure(state="normal")
        self.btn_eliminar.configure(state="normal")

    def _new_edit(self):
        self.current_id = None
        self.tree.selection_remove(self.tree.selection())
        if self._tipos_gasto:
            self.combo_tipo.current(0)
        if self._tipos_pago:
            self.combo_pago.current(0)
        self.entry_detalle.delete(0, "end")
        self.entry_importe.delete(0, "end")
        self.btn_guardar.configure(state="disabled")
        self.btn_eliminar.configure(state="disabled")

    # Helpers para resolver ids a partir de las filas mostradas

    def _tipo_pago_desc(self, vals):
        # Determinamos el idTipoPago consultando la fila por idGastos
        gid = str(vals[0])
        conn = db.get_connection()
        try:
            r = conn.execute(
                "SELECT idTipoPago FROM tbGastosGenerales WHERE idGastos=?",
                (gid,)).fetchone()
            if r is None:
                return ""
            return next((p for i, (pid, p) in enumerate(self._tipos_pago)
                         if str(pid) == str(r[0])), "")
        finally:
            conn.close()

    def _fecha_sql(self, fecha_str):
        # 'dd/mm/aaaa hh:mm' -> 'aaaa-mm-dd' for DateEntry
        s = str(fecha_str)
        try:
            return datetime.datetime.strptime(s, "%d/%m/%Y %H:%M").strftime(
                "%Y-%m-%d")
        except (ValueError, TypeError):
            return str(s)[:10]

    # ── Actions: EDIT ─────────────────────────────────────────────────────

    def _on_guardar(self):
        if self.current_id is None:
            return
        detalle = self.entry_detalle.get().strip()
        importe = self.entry_importe.get().strip()
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
                messagebox.showwarning("Guardar", "Fecha inválida.",
                                       parent=self)
                return

        try:
            _update_gasto(self.current_id, id_tipo, detalle, importe_f, fecha,
                          id_pago)
        except Exception as e:
            messagebox.showerror("Error", f"Error al guardar gasto: {e}",
                                 parent=self)
            return

        messagebox.showinfo("Guardar", "Gasto modificado.", parent=self)
        self._refresh_grid()
        self._new_edit()

    def _on_eliminar(self):
        if self.current_id is None:
            return
        if not messagebox.askyesno(
                "Confirmar",
                f"¿Desea eliminar físicamente el gasto ID {self.current_id}?",
                parent=self):
            return
        _delete_gasto(self.current_id)
        self._refresh_grid()
        self._new_edit()
        messagebox.showinfo("Eliminar", "Gasto eliminado.", parent=self)


def open_window(parent=None):
    return GestionarGastosWindow(parent)


if __name__ == "__main__":
    root = tk.Tk()
    root.withdraw()
    open_window(root)
    root.mainloop()
