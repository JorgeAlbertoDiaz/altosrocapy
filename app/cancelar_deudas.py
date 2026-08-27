"""Cancelar Deudas — cancelar/cobrar deudas pendientes de un socio.

Módulo independiente de las cuotas. Solo administra saldos pendientes.
NO modifica vencimiento, cobros, pagos de cuotas ni planes.
"""

import datetime
import tkinter as tk
from tkinter import ttk, messagebox

try:
    from app import db
except ImportError:
    import db

# ── Constants ─────────────────────────────────────────────────────────────

W, H = 880, 270
PAD = 10
BG = "#F0F0F0"
FG = "#000000"
FG_LABEL = "#000000"
FG_DARK = "#333333"
ENTRY_BG = "#FFFFFF"
BTN_BLUE = "#3B6FA0"
BTN_BLUE_ACTIVE = "#2D5A85"
SEL_BG = "#0078D7"
FN = ("Helvetica", 9)
FN_B = ("Helvetica", 9, "bold")


# ── Helpers ───────────────────────────────────────────────────────────────

def _fmt(raw):
    if not raw:
        return ""
    try:
        dt = datetime.datetime.strptime(raw[:19], "%Y-%m-%d %H:%M:%S")
        return dt.strftime("%d/%m/%Y %H:%M")
    except (ValueError, TypeError):
        return raw


def _load_socio(id_socio):
    conn = db.get_connection()
    try:
        row = conn.execute(
            "SELECT idSocio, Apellidos, Nombres, Documento FROM tbSocios "
            "WHERE idSocio = ?",
            (id_socio,),
        ).fetchone()
        return dict(row) if row else None
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


def _cancel_deuda(id_deuda):
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

class CancelarDeudasWindow(tk.Toplevel):
    def __init__(self, parent=None, socio_id=None):
        super().__init__(parent)
        self.title("Cancelar Deudas")
        self.geometry(f"{W}x{H}")
        self.resizable(False, False)
        self.configure(bg=BG)
        self.bind("<Escape>", lambda _: self.destroy())

        self.socio_id = socio_id
        self._build()

        if socio_id:
            self._load_socio(socio_id)

    def _build(self):
        # === ENCABEZADO ===
        self.lbl_encabezado = tk.Label(
            self, text="", bg=BG, fg=FG_DARK,
            font=("Helvetica", 16, "bold"),
        )
        self.lbl_encabezado.place(x=10, y=6)

        # === LEFT: DEBT GRID (600x180) ===
        frm_grid = tk.Frame(self, bg=BG)
        frm_grid.place(x=10, y=40, width=600, height=180)

        cols = ("id", "socio", "doc", "importe", "fecha", "detalle")
        self.tree = ttk.Treeview(frm_grid, columns=cols, show="headings",
                                 selectmode="browse")
        self.tree.heading("id", text="ID")
        self.tree.heading("socio", text="Socio")
        self.tree.heading("doc", text="Documento")
        self.tree.heading("importe", text="Importe Adeudado")
        self.tree.heading("fecha", text="Fecha Deuda")
        self.tree.heading("detalle", text="Detalle")
        self.tree.column("id", width=50, anchor="center")
        self.tree.column("socio", width=160)
        self.tree.column("doc", width=90, anchor="center")
        self.tree.column("importe", width=100, anchor="e")
        self.tree.column("fecha", width=100)
        self.tree.column("detalle", width=90)

        style = ttk.Style(self)
        style.configure("C.Treeview", rowheight=22, font=FN,
                        background="#FFF", fieldbackground="#FFF")
        style.configure("C.Treeview.Heading", font=FN_B)
        style.map("C.Treeview",
                  background=[("selected", SEL_BG)],
                  foreground=[("selected", "#FFF")])
        self.tree.configure(style="C.Treeview")

        vsb = ttk.Scrollbar(frm_grid, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.place(x=0, y=0, relwidth=0.97, relheight=1.0)
        vsb.place(relx=0.975, y=0, relheight=1.0)

        self.tree.bind("<<TreeviewSelect>>", self._on_select)

        # === RIGHT: CANCELACION PARCIAL PANEL ===
        frm_right = tk.LabelFrame(
            self, text=" CANCELACION PARCIAL ", bg=BG,
            font=FN_B, fg="#333", relief="groove", bd=2, labelanchor="nw",
        )
        frm_right.place(x=620, y=40, width=250, height=180)

        tk.Label(frm_right, text="Importe a saldar:", bg=BG, font=FN,
                 fg=FG_LABEL).place(x=10, y=18)
        self.lbl_importe = tk.Label(frm_right, text="", bg=BG, font=FN_B, fg=FG)
        self.lbl_importe.place(x=10, y=40)

        tk.Label(frm_right, text="Detalle:", bg=BG, font=FN, fg=FG_LABEL).place(x=10, y=66)
        self.lbl_detalle = tk.Label(frm_right, text="", bg=BG, font=FN, fg=FG,
                                     anchor="w")
        self.lbl_detalle.place(x=10, y=88)

        tk.Label(frm_right, text="Fecha:", bg=BG, font=FN, fg=FG_LABEL).place(x=10, y=112)
        self.lbl_fecha = tk.Label(frm_right, text="", bg=BG, font=FN, fg=FG)
        self.lbl_fecha.place(x=10, y=134)

        # === BOTTOM BAR ===
        self.btn_parcial = tk.Button(
            self, text="CANCELAR DEUDA PARCIAL", bg=BTN_BLUE, fg="#FFF",
            font=FN_B, relief="flat",
            activebackground=BTN_BLUE_ACTIVE, activeforeground="#FFF",
            cursor="hand2", command=self._on_cancel_parcial, state="disabled",
        )
        self.btn_parcial.place(x=620, y=228, width=250, height=30)

        self.btn_total = tk.Button(
            self, text="CANCELAR TOTAL", bg=BTN_BLUE, fg="#FFF",
            font=FN_B, relief="flat",
            activebackground=BTN_BLUE_ACTIVE, activeforeground="#FFF",
            cursor="hand2", command=self._on_cancel_total, state="disabled",
        )
        self.btn_total.place(x=10, y=228, width=160, height=30)

        tk.Button(
            self, text="Salir", bg="#999", fg="#FFF", font=FN_B,
            relief="flat", activebackground="#777", cursor="hand2",
            command=self.destroy,
        ).place(x=180, y=228, width=80, height=30)

        # === TOTAL ADEUDADO ===
        self.lbl_total = tk.Label(self, text="", bg=BG, fg=FG,
                                   font=("Helvetica", 13, "bold"))
        self.lbl_total.place(x=420, y=232)

    # ── Load socio ────────────────────────────────────────────────────────

    def _load_socio(self, id_socio):
        socio = _load_socio(id_socio)
        if socio is None:
            messagebox.showinfo("Error", "Socio no encontrado.", parent=self)
            self.destroy()
            return
        self.socio_id = id_socio

        nombre = f"{(socio['Apellidos'] or '').upper()} {(socio['Nombres'] or '').upper()}"
        self.lbl_encabezado.configure(text=nombre)

        self._refresh()

    def _refresh(self):
        if not self.socio_id:
            return
        socio = _load_socio(self.socio_id)
        deudas = _load_deudas(self.socio_id)
        total = _total_deuda(self.socio_id)

        nombre = f"{(socio['Apellidos'] or '').upper()} {(socio['Nombres'] or '').upper()}"
        doc = socio["Documento"]

        # Update grid
        self.tree.delete(*self.tree.get_children())
        for d in deudas:
            importe = float(d["ImporteDeuda"] or 0)
            self.tree.insert("", "end", values=(
                d["idDeuda"], nombre, doc,
                f"${importe:.0f}", _fmt(d["Fecha"]), d["Detalle"] or "",
            ))

        # Clear right panel selection
        self.lbl_importe.configure(text="")
        self.lbl_detalle.configure(text="")
        self.lbl_fecha.configure(text="")

        # Total
        self.lbl_total.configure(
            text=f"Total adeudado: ${total:.0f}")

        has_deudas = len(deudas) > 0
        self.btn_total.configure(state="normal" if has_deudas else "disabled")
        self.btn_parcial.configure(state="disabled")

    # ── Selection ─────────────────────────────────────────────────────────

    def _on_select(self, _event):
        sel = self.tree.selection()
        if not sel:
            self.btn_parcial.configure(state="disabled")
            return
        vals = self.tree.item(sel[0], "values")
        self.lbl_importe.configure(text=vals[3])
        self.lbl_detalle.configure(text=vals[5])
        # Find full fecha with seconds
        for d in _load_deudas(self.socio_id):
            if str(d["idDeuda"]) == str(vals[0]):
                self.lbl_fecha.configure(text=d["Fecha"])
                break
        self.btn_parcial.configure(state="normal")

    # ── Cancel partial ────────────────────────────────────────────────────

    def _on_cancel_parcial(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Cancelar", "Seleccione una deuda.", parent=self)
            return
        vals = self.tree.item(sel[0], "values")
        id_deuda = str(vals[0])
        importe = vals[3]

        if not messagebox.askyesno(
            "Confirmar",
            f"¿Desea cancelar la deuda ID {id_deuda} por {importe}?",
            parent=self,
        ):
            return

        try:
            _cancel_deuda(id_deuda)
        except Exception as e:
            messagebox.showerror("Error", f"Error al cancelar: {e}", parent=self)
            return

        self._refresh()
        messagebox.showinfo("Éxito", f"Deuda ID {id_deuda} cancelada.", parent=self)

    # ── Cancel total ──────────────────────────────────────────────────────

    def _on_cancel_total(self):
        total = _total_deuda(self.socio_id)
        if not messagebox.askyesno(
            "Confirmar",
            f"¿Desea cancelar todas las deudas del socio?\n\n"
            f"Importe total: ${total:.0f}",
            parent=self,
        ):
            return

        try:
            _cancel_all(self.socio_id)
        except Exception as e:
            messagebox.showerror("Error", f"Error al cancelar: {e}", parent=self)
            return

        self._refresh()
        messagebox.showinfo("Éxito", "Todas las deudas fueron canceladas.", parent=self)


def open_window(parent=None, socio_id=None):
    return CancelarDeudasWindow(parent, socio_id=socio_id)


if __name__ == "__main__":
    root = tk.Tk()
    root.withdraw()
    open_window(root)
    root.mainloop()
