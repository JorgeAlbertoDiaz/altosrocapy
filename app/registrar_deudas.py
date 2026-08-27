"""Registrar Deudas — registro de deudas pendientes de un socio.

NOTA: Las deudas son independientes de las cuotas. NO modifican vencimiento,
cobros, pagos ni planes. Representan consumos/productos/servicios pendientes
(agua, proteína, inscripción, diferencia de cuota, accesorios, etc.).
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

W, H = 700, 540
PAD = 10
BG = "#F0F0F0"
FG = "#000000"
FG_LABEL = "#000000"
FG_BLUE = "#003399"
ENTRY_BG = "#FFFFFF"
BTN_BLUE = "#3B6FA0"
BTN_BLUE_ACTIVE = "#2D5A85"
SEL_BG = "#0078D7"
FN = ("Helvetica", 9)
FN_B = ("Helvetica", 9, "bold")


# ── Helpers ───────────────────────────────────────────────────────────────

def _search_socios(query):
    q = query.strip()
    if not q:
        return []
    conn = db.get_connection()
    try:
        like = f"%{q}%"
        rows = conn.execute(
            "SELECT s.idSocio, s.Apellidos, s.Nombres, s.Documento, s.Domicilio, "
            "  COALESCE((SELECT SUM(CAST(d.ImporteDeuda AS REAL)) FROM "
            "      tb_RegistroDeudas d "
            "      WHERE d.idSocio = s.idSocio "
            "        AND (d.Cancelada IS NULL OR d.Cancelada != '1') "
            "        AND (d.Eliminado IS NULL OR d.Eliminado != '1')), 0) AS deuda "
            "FROM tbSocios s "
            "WHERE s.Documento != '---------' AND ("
            "  s.Documento LIKE ? OR s.Apellidos LIKE ? OR s.Nombres LIKE ? "
            "  OR (s.Apellidos || ' ' || s.Nombres LIKE ?)"
            ") ORDER BY s.Apellidos, s.Nombres LIMIT 50",
            (like, like, like, like),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def _load_deudas(id_socio):
    """Load active (non-cancelled, non-deleted) debts for a socio."""
    conn = db.get_connection()
    try:
        rows = conn.execute(
            "SELECT idDeuda, idSocio, Fecha, ImporteDeuda, Detalle "
            "FROM tb_RegistroDeudas "
            "WHERE idSocio = ? "
            "  AND (Cancelada IS NULL OR Cancelada != '1') "
            "  AND (Eliminado IS NULL OR Eliminado != '1') "
            "ORDER BY Fecha",
            (id_socio,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def _total_deuda(id_socio):
    deudas = _load_deudas(id_socio)
    try:
        return sum(float(d["ImporteDeuda"] or 0) for d in deudas)
    except (ValueError, TypeError):
        return 0.0


def _register_deuda(id_socio, fecha, importe, detalle, usuario=""):
    """Insert a new debt. Returns new idDeuda."""
    conn = db.get_connection()
    try:
        row = conn.execute(
            "SELECT MAX(CAST(idDeuda AS INTEGER)) FROM tb_RegistroDeudas"
        ).fetchone()
        new_id = str((row[0] or 0) + 1)

        conn.execute(
            "INSERT INTO tb_RegistroDeudas "
            "(idDeuda, idSocio, Fecha, ImporteDeuda, Detalle, "
            " Cancelada, Eliminado, UsuarioCobrador) "
            "VALUES (?, ?, ?, ?, ?, '0', '0', ?)",
            (new_id, id_socio, fecha, f"{importe:.2f}", detalle, usuario),
        )
        conn.commit()
        return new_id
    finally:
        conn.close()


def _cancel_deuda(id_deuda):
    """Mark a specific debt as cancelled."""
    conn = db.get_connection()
    try:
        ahora = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.000")
        conn.execute(
            "UPDATE tb_RegistroDeudas SET Cancelada = '1', FechaCancelacion = ? "
            "WHERE idDeuda = ?",
            (ahora, id_deuda),
        )
        conn.commit()
    finally:
        conn.close()


def _cancel_all(id_socio):
    """Mark all active debts of a socio as cancelled."""
    conn = db.get_connection()
    try:
        ahora = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.000")
        conn.execute(
            "UPDATE tb_RegistroDeudas SET Cancelada = '1', FechaCancelacion = ? "
            "WHERE idSocio = ? "
            "  AND (Cancelada IS NULL OR Cancelada != '1') "
            "  AND (Eliminado IS NULL OR Eliminado != '1')",
            (ahora, id_socio),
        )
        conn.commit()
    finally:
        conn.close()


# ── Main Window ───────────────────────────────────────────────────────────

class RegistrarDeudasWindow(tk.Toplevel):
    def __init__(self, parent=None, usuario=None):
        super().__init__(parent)
        self.title("Registrar Deudas")
        self.geometry(f"{W}x{H}")
        self.resizable(False, False)
        self.configure(bg=BG)
        self.bind("<Escape>", lambda _: self.destroy())

        self.usuario = usuario or ""
        self.current_socio = None
        self._build()

    def _build(self):
        # === SEARCH BAR ===
        self.search_var = tk.StringVar()
        self.entry_search = tk.Entry(
            self, textvariable=self.search_var,
            bg="#FFF", fg=FG, font=("Helvetica", 11),
            relief="solid", bd=1,
        )
        self.entry_search.place(x=10, y=10, width=600, height=30)
        self.entry_search.bind("<Return>", lambda _: self._do_search())

        tk.Button(
            self, text="Buscar", bg="#888", fg="#FFF",
            font=FN_B, relief="flat", activebackground="#666",
            cursor="hand2", command=self._do_search,
        ).place(x=618, y=10, width=72, height=30)

        # === SOCIO GRID (680x220) ===
        frm_grid = tk.Frame(self, bg=BG)
        frm_grid.place(x=10, y=48, width=680, height=220)

        cols = ("socio", "doc", "domicilio", "deuda")
        self.tree = ttk.Treeview(frm_grid, columns=cols, show="headings",
                                 selectmode="browse")
        self.tree.heading("socio", text="Socio")
        self.tree.heading("doc", text="Documento")
        self.tree.heading("domicilio", text="Domicilio")
        self.tree.heading("deuda", text="Deuda")
        self.tree.column("socio", width=240)
        self.tree.column("doc", width=100, anchor="center")
        self.tree.column("domicilio", width=220)
        self.tree.column("deuda", width=100, anchor="e")

        style = ttk.Style(self)
        style.configure("D.Treeview", rowheight=22, font=FN,
                        background="#FFF", fieldbackground="#FFF")
        style.configure("D.Treeview.Heading", font=FN_B)
        style.map("D.Treeview",
                  background=[("selected", SEL_BG)],
                  foreground=[("selected", "#FFF")])
        self.tree.configure(style="D.Treeview")

        vsb = ttk.Scrollbar(frm_grid, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.place(x=0, y=0, relwidth=0.98, relheight=1.0)
        vsb.place(relx=0.985, y=0, relheight=1.0)

        self.tree.bind("<<TreeviewSelect>>", self._on_select)

        # === SOCIO INFO PANEL ===
        self.frm_info = tk.Frame(self, bg="#D8D8D8")
        self.frm_info.place(x=10, y=276, width=680, height=60)

        self.lbl_nombre = tk.Label(
            self.frm_info, text="", bg="#D8D8D8", fg=FG_BLUE,
            font=("Helvetica", 14, "bold"),
        )
        self.lbl_nombre.place(x=10, y=6)

        self.lbl_dni = tk.Label(
            self.frm_info, text="", bg="#D8D8D8", fg=FG_BLUE,
            font=("Helvetica", 11, "bold"),
        )
        self.lbl_dni.place(x=10, y=34)

        # === DEBT FORM ===
        frm_form = tk.LabelFrame(
            self, text=" Datos de la Deuda ", bg=BG,
            font=FN_B, fg="#333", relief="groove", bd=2, labelanchor="nw",
        )
        frm_form.place(x=10, y=344, width=680, height=130)

        # Fecha
        tk.Label(frm_form, text="Fecha:", bg=BG, font=FN, fg=FG_LABEL).place(x=20, y=25)
        if DateEntry is not None:
            self.dt_fecha = DateEntry(
                frm_form, width=12, background="#3B6FA0", foreground="white",
                borderwidth=1, date_pattern="dd/mm/yyyy", font=FN,
            )
            self.dt_fecha.place(x=95, y=18, width=140, height=24)
        else:
            self.dt_fecha = None
            self.fecha_var = tk.StringVar(
                value=datetime.date.today().strftime("%d/%m/%Y"))
            self.entry_fecha = tk.Entry(
                frm_form, textvariable=self.fecha_var,
                bg=ENTRY_BG, fg=FG, font=FN, relief="solid", bd=1,
            )
            self.entry_fecha.place(x=95, y=18, width=140, height=24)

        # Importe Deuda
        tk.Label(frm_form, text="Importe Deuda:", bg=BG, font=FN,
                 fg=FG_LABEL).place(x=20, y=58)
        self.importe_var = tk.StringVar()
        self.entry_importe = tk.Entry(
            frm_form, textvariable=self.importe_var,
            bg=ENTRY_BG, fg=FG, font=FN, relief="solid", bd=1,
        )
        self.entry_importe.place(x=95, y=52, width=140, height=24)

        # Detalle
        tk.Label(frm_form, text="Detalle:", bg=BG, font=FN, fg=FG_LABEL).place(x=20, y=90)
        self.detalle_var = tk.StringVar()
        self.entry_detalle = tk.Entry(
            frm_form, textvariable=self.detalle_var,
            bg=ENTRY_BG, fg=FG, font=FN, relief="solid", bd=1,
        )
        self.entry_detalle.place(x=95, y=84, width=300, height=24)

        # === BOTTOM BUTTONS ===
        self.btn_registrar = tk.Button(
            self, text="REGISTRAR DEUDA", bg=BTN_BLUE, fg="#FFF",
            font=FN_B, relief="flat",
            activebackground=BTN_BLUE_ACTIVE, activeforeground="#FFF",
            cursor="hand2", command=self._on_register, state="disabled",
        )
        self.btn_registrar.place(x=10, y=490, width=160, height=32)

        self.btn_detalle = tk.Button(
            self, text="DETALLE DEUDA", bg=BTN_BLUE, fg="#FFF",
            font=FN_B, relief="flat",
            activebackground=BTN_BLUE_ACTIVE, activeforeground="#FFF",
            cursor="hand2", command=self._on_detalle, state="disabled",
        )
        self.btn_detalle.place(x=180, y=490, width=160, height=32)

        tk.Button(
            self, text="Salir", bg="#999", fg="#FFF", font=FN_B,
            relief="flat", activebackground="#777", cursor="hand2",
            command=self.destroy,
        ).place(x=600, y=490, width=90, height=32)

    # ── Search ────────────────────────────────────────────────────────────

    def _do_search(self):
        results = _search_socios(self.search_var.get())
        self.tree.delete(*self.tree.get_children())
        self._clear_selection()
        if not results:
            return
        for r in results:
            nombre = f"{(r['Apellidos'] or '').upper()} {(r['Nombres'] or '').upper()}"
            self.tree.insert("", "end", values=(
                nombre, r["Documento"] or "", r["Domicilio"] or "",
                f"{r['deuda'] or 0:.2f}",
            ))

    def _on_select(self, _event):
        sel = self.tree.selection()
        if not sel:
            return
        item = self.tree.item(sel[0], "values")
        doc = str(item[1])
        # Re-query the socio by doc to get idSocio
        results = _search_socios(doc)
        if not results:
            return
        socio = results[0]
        self.current_socio = {"idSocio": socio["idSocio"], "deuda": socio["deuda"]}
        nombre = f"{(socio['Apellidos'] or '').upper()} {(socio['Nombres'] or '').upper()}"
        self.lbl_nombre.configure(text=nombre)
        self.lbl_dni.configure(text=f"DNI: {socio['Documento']}")
        self.btn_registrar.configure(state="normal")
        self.btn_detalle.configure(state="normal")

    def _clear_selection(self):
        self.current_socio = None
        self.lbl_nombre.configure(text="")
        self.lbl_dni.configure(text="")
        self.btn_registrar.configure(state="disabled")
        self.btn_detalle.configure(state="disabled")
        self.importe_var.set("")
        self.detalle_var.set("")

    # ── Register debt ─────────────────────────────────────────────────────

    def _on_register(self):
        if not self.current_socio:
            messagebox.showwarning("Deuda", "Seleccione un socio.", parent=self)
            return
        importe = self.importe_var.get().strip()
        detalle = self.detalle_var.get().strip()

        try:
            importe_f = float(importe)
        except (ValueError, TypeError):
            messagebox.showwarning("Deuda", "Importe inválido.", parent=self)
            return

        if importe_f <= 0:
            messagebox.showwarning("Deuda", "El importe debe ser mayor a 0.", parent=self)
            return
        if not detalle:
            messagebox.showwarning("Deuda", "El detalle es obligatorio.", parent=self)
            return

        if DateEntry is not None:
            fecha = self.dt_fecha.get_date().strftime("%Y-%m-%d %H:%M:%S.000")
        else:
            try:
                parts = self.fecha_var.get().split("/")
                fecha = datetime.datetime(
                    int(parts[2]), int(parts[1]), int(parts[0])
                ).strftime("%Y-%m-%d %H:%M:%S.000")
            except (ValueError, IndexError):
                messagebox.showwarning("Deuda", "Fecha inválida.", parent=self)
                return

        try:
            new_id = _register_deuda(
                self.current_socio["idSocio"], fecha, importe_f, detalle,
                self.usuario)
        except Exception as e:
            messagebox.showerror("Error", f"Error al registrar deuda: {e}", parent=self)
            return

        messagebox.showinfo("Éxito", f"Deuda registrada. ID: {new_id}\n"
                              f"Importe: ${importe_f:.2f}\nDetalle: {detalle}",
                            parent=self)
        self.importe_var.set("")
        self.detalle_var.set("")
        self._refresh_grid()

    def _refresh_grid(self):
        """Refresh the deuda column in the grid."""
        if not self.current_socio:
            return
        new_total = _total_deuda(self.current_socio["idSocio"])
        self.current_socio["deuda"] = new_total
        self._do_search()

    # ── Open detalle (cancelar deudas) ────────────────────────────────────

    def _on_detalle(self):
        if not self.current_socio:
            return
        try:
            from app import cancelar_deudas
        except ImportError:
            import cancelar_deudas
        cancelar_deudas.open_window(self, socio_id=self.current_socio["idSocio"])


def open_window(parent=None, usuario=None):
    return RegistrarDeudasWindow(parent, usuario=usuario)


if __name__ == "__main__":
    root = tk.Tk()
    root.withdraw()
    open_window(root)
    root.mainloop()
