"""Anular Cobros — eliminación de pagos de cuotas.

Ventana de selección y anulación de pagos existentes.
"""

import datetime
import tkinter as tk
from tkinter import ttk, messagebox

try:
    from app import db
except ImportError:
    import db

# ── Constants ─────────────────────────────────────────────────────────────

W, H = 730, 490
PAD = 8

BG = "#F0F0F0"
FG = "#000000"
FG_LABEL = "#333333"
FG_HEADER = "#003366"
FG_BLUE = "#003399"
BTN_BLUE = "#3B6FA0"
BTN_BLUE_ACTIVE = "#2D5A85"
SEL_BG = "#0078D7"


# ── Helpers ───────────────────────────────────────────────────────────────

def _parse_date(raw):
    if not raw:
        return None
    try:
        return datetime.datetime.strptime(raw[:10], "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def _fmt(raw):
    d = _parse_date(raw)
    return d.strftime("%d/%m/%Y") if d else ""


def _safe_float(val, default=0.0):
    try:
        return float(val or 0)
    except (ValueError, TypeError):
        return default


# ── Data access ───────────────────────────────────────────────────────────

def _search_socios(query):
    q = query.strip()
    if not q:
        return []
    conn = db.get_connection()
    try:
        like = f"%{q}%"
        rows = conn.execute(
            "SELECT idSocio, Apellidos, Nombres, Documento "
            "FROM tbSocios "
            "WHERE Documento != '---------' AND ("
            "  Documento LIKE ? OR Apellidos LIKE ? OR Nombres LIKE ? "
            "  OR (Apellidos || ' ' || Nombres LIKE ?)"
            ") ORDER BY Apellidos, Nombres LIMIT 50",
            (like, like, like, like),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def _load_pagos(id_socio):
    conn = db.get_connection()
    try:
        socio = conn.execute(
            "SELECT Apellidos, Nombres, Documento FROM tbSocios WHERE idSocio = ?",
            (id_socio,),
        ).fetchone()
        if socio is None:
            return None, []

        pagos = conn.execute(
            "SELECT idPago, Importe, FechaVencimineto, FechadePago, Observaciones "
            "FROM tbPagos "
            "WHERE idSocio = ? AND (Eliminado IS NULL OR Eliminado != '1') "
            "ORDER BY FechadePago DESC",
            (id_socio,),
        ).fetchall()
        result = []
        for p in pagos:
            result.append({
                "idPago": str(p["idPago"]),
                "Importe": p["Importe"],
                "FechaVencimineto": p["FechaVencimineto"],
                "FechadePago": p["FechadePago"],
                "Observaciones": p["Observaciones"],
            })
        return dict(socio), result
    finally:
        conn.close()


def _delete_pago(id_pago):
    conn = db.get_connection()
    try:
        conn.execute("DELETE FROM tbPagos WHERE idPago = ?", (int(id_pago),))
        conn.commit()
    finally:
        conn.close()


# ── Main Window ───────────────────────────────────────────────────────────

class AnularCobrosWindow(tk.Toplevel):
    def __init__(self, parent=None, socio_id=None, on_deleted=None):
        super().__init__(parent)
        self.title("ANULAR COBROS")
        self.geometry(f"{W}x{H}")
        self.minsize(600, 400)
        self.configure(bg=BG)
        self.bind("<Escape>", lambda _: self._on_close())

        self.current_socio_id = socio_id
        self.socio_info = None
        self.on_deleted = on_deleted

        self._build()

        if socio_id:
            self._load_socio_by_id(socio_id)

        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _on_close(self):
        parent = self.master
        self.destroy()
        if parent and parent.winfo_exists():
            parent.after(50, lambda: (parent.lift(), parent.focus_force()))

    # ── Build ─────────────────────────────────────────────────────────────

    def _build(self):
        frm_search = tk.Frame(self, bg=BG, height=36)
        frm_search.pack(fill="x", padx=PAD, pady=(8, 4))
        frm_search.pack_propagate(False)

        self.search_var = tk.StringVar()
        self.entry_search = tk.Entry(
            frm_search, textvariable=self.search_var,
            bg="#FFF", fg=FG,
            font=("Helvetica", 11),
            relief="solid", bd=1,
        )
        self.entry_search.place(x=0, y=2, width=620, height=30)
        self.entry_search.bind("<Return>", lambda _: self._do_search())

        tk.Button(
            frm_search, text="Buscar", bg="#888", fg="#FFF",
            font=("Helvetica", 9, "bold"), relief="flat",
            activebackground="#666", cursor="hand2",
            command=self._do_search,
        ).place(x=628, y=2, width=70, height=30)

        frm_info = tk.Frame(self, bg="#D8D8D8", relief="flat", bd=0)
        frm_info.pack(fill="x", padx=PAD, pady=(4, 2))

        self.lbl_nombre = tk.Label(
            frm_info, text="", bg="#D8D8D8",
            font=("Helvetica", 14, "bold"), fg=FG_BLUE,
        )
        self.lbl_nombre.pack(anchor="w", padx=10, pady=(8, 0))

        self.lbl_dni = tk.Label(
            frm_info, text="", bg="#D8D8D8",
            font=("Helvetica", 11, "bold"), fg=FG_BLUE,
        )
        self.lbl_dni.pack(anchor="w", padx=10, pady=(0, 8))

        self.lbl_title = tk.Label(
            self, text="", bg=BG,
            font=("Helvetica", 9, "bold"), fg=FG, anchor="w",
        )
        self.lbl_title.pack(fill="x", padx=PAD + 4, pady=(6, 2))

        frm_grid = tk.Frame(self, bg=BG)
        frm_grid.pack(fill="both", expand=True, padx=PAD, pady=(0, 4))

        cols = ("idPago", "importe", "vencimiento", "fecha_pago", "obs")
        self.tree = ttk.Treeview(
            frm_grid, columns=cols, show="headings", selectmode="browse",
        )
        self.tree.heading("idPago", text="ID Pago")
        self.tree.heading("importe", text="Importe")
        self.tree.heading("vencimiento", text="Vencimiento")
        self.tree.heading("fecha_pago", text="Fecha de Pago")
        self.tree.heading("obs", text="Observaciones")

        self.tree.column("idPago", width=80, minwidth=60, anchor="center")
        self.tree.column("importe", width=100, minwidth=70, anchor="e")
        self.tree.column("vencimiento", width=120, minwidth=90, anchor="center")
        self.tree.column("fecha_pago", width=120, minwidth=90, anchor="center")
        self.tree.column("obs", width=200, minwidth=80, anchor="w")

        style = ttk.Style(self)
        style.configure("AN.Treeview", rowheight=22, font=("Helvetica", 9),
                        background="#FFF", fieldbackground="#FFF")
        style.configure("AN.Treeview.Heading", font=("Helvetica", 8, "bold"))
        style.map("AN.Treeview",
                  background=[("selected", SEL_BG)],
                  foreground=[("selected", "#FFF")])
        self.tree.configure(style="AN.Treeview")

        vsb = ttk.Scrollbar(frm_grid, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

        self.tree.bind("<Double-Button-1>", lambda _: self._on_anular())

        bar = tk.Frame(self, bg=BG, height=38)
        bar.pack(fill="x", padx=PAD, pady=(0, PAD))

        self.btn_anular = tk.Button(
            bar, text="Anular", bg=BTN_BLUE, fg="#FFF",
            font=("Helvetica", 9, "bold"), relief="flat",
            activebackground=BTN_BLUE_ACTIVE, activeforeground="#FFF",
            cursor="hand2", command=self._on_anular, state="disabled",
        )
        self.btn_anular.pack(side="right", padx=(6, 0))

        tk.Button(
            bar, text="Volver", width=10, command=self._on_close,
        ).pack(side="right", padx=(6, 0))

    # ── Search ────────────────────────────────────────────────────────────

    def _do_search(self):
        query = self.search_var.get().strip()
        if not query:
            return
        results = _search_socios(query)
        if not results:
            messagebox.showinfo("Búsqueda", "No se encontraron socios.", parent=self)
            return
        if len(results) == 1:
            self._load_socio_by_id(results[0]["idSocio"])
            return
        self._show_picker(results)

    def _show_picker(self, results):
        picker = tk.Toplevel(self)
        picker.title("Seleccionar Socio")
        picker.geometry("460x350")
        picker.configure(bg=BG)
        picker.transient(self)
        picker.grab_set()
        picker.bind("<Escape>", lambda _: picker.destroy())

        tk.Label(picker, text="Seleccione un socio:", bg=BG,
                 font=("Helvetica", 10, "bold"), fg=FG).pack(padx=10, pady=(10, 5), anchor="w")

        cols = ("id", "apellido", "nombre", "doc")
        tree = ttk.Treeview(picker, columns=cols, show="headings", selectmode="browse")
        tree.heading("id", text="ID")
        tree.heading("apellido", text="Apellido")
        tree.heading("nombre", text="Nombre")
        tree.heading("doc", text="Documento")
        tree.column("id", width=40, anchor="center")
        tree.column("apellido", width=140)
        tree.column("nombre", width=140)
        tree.column("doc", width=90, anchor="center")
        for r in results:
            tree.insert("", "end", values=(
                r["idSocio"], r["Apellidos"] or "", r["Nombres"] or "",
                r["Documento"] or ""))
        tree.pack(fill="both", expand=True, padx=10, pady=5)

        def _select():
            sel = tree.selection()
            if not sel:
                return
            vals = tree.item(sel[0], "values")
            picker.destroy()
            self._load_socio_by_id(str(vals[0]))
            self.after(50, lambda: (self.lift(), self.focus_force()))

        tk.Button(picker, text="Seleccionar", bg=BTN_BLUE, fg="#FFF",
                  font=("Helvetica", 9, "bold"), relief="flat",
                  command=_select).pack(pady=8)
        tree.bind("<Double-Button-1>", lambda _: _select())

    # ── Load socio ────────────────────────────────────────────────────────

    def _load_socio_by_id(self, id_socio):
        socio, pagos = _load_pagos(id_socio)
        if socio is None:
            messagebox.showinfo("Error", "Socio no encontrado.", parent=self)
            return

        self.current_socio_id = id_socio
        self.socio_info = socio

        nombre = f"{(socio.get('Apellidos') or '').upper()}, {(socio.get('Nombres') or '').upper()}"
        self.lbl_nombre.configure(text=nombre)
        self.lbl_dni.configure(text=f"DNI: {socio.get('Documento', '')}")
        self.lbl_title.configure(
            text="ULTIMOS PAGOS REALIZADOS POR EL SOCIO:")

        self.tree.delete(*self.tree.get_children())
        for p in pagos:
            self.tree.insert("", "end", values=(
                p["idPago"],
                f"${_safe_float(p['Importe']):,.0f}",
                _fmt(p.get("FechaVencimineto")),
                _fmt(p.get("FechadePago")),
                p.get("Observaciones") or "",
            ))

        self.btn_anular.configure(state="normal" if pagos else "disabled")

    # ── Anular ────────────────────────────────────────────────────────────

    def _on_anular(self):
        sel = self.tree.selection()
        if not sel:
            return

        vals = self.tree.item(sel[0], "values")
        id_pago = str(vals[0]).strip()
        fcobro = vals[3]
        importe = vals[1]

        if not id_pago or id_pago == "None":
            messagebox.showerror("Error", "No se pudo identificar el pago.", parent=self)
            return

        confirm = tk.Toplevel(self)
        confirm.title("Confirmar Anulación")
        confirm.geometry("320x140")
        confirm.configure(bg=BG)
        confirm.resizable(False, False)
        confirm.transient(self)
        confirm.grab_set()
        confirm.bind("<Escape>", lambda _: confirm.destroy())

        tk.Label(
            confirm,
            text=f"¿Seguro de eliminar el Pago ID: {id_pago}?",
            bg=BG, font=("Helvetica", 10), fg=FG,
        ).place(relx=0.5, y=25, anchor="center")

        tk.Label(
            confirm,
            text=f"Fecha: {fcobro}  Importe: {importe}\nEsta acción eliminará\npermanentemente el cobro.",
            bg=BG, font=("Helvetica", 9, "bold"), fg="#CC0000",
            justify="center",
        ).place(relx=0.5, y=65, anchor="center")

        def _confirm_delete():
            _delete_pago(id_pago)
            confirm.destroy()
            self._refresh()
            if self.on_deleted:
                self.on_deleted()
            self.after(50, lambda: (self.lift(), self.focus_force()))

        def _cancel():
            confirm.destroy()
            self.after(50, lambda: (self.lift(), self.focus_force()))

        tk.Button(
            confirm, text="Aceptar", bg="#888", fg="#FFF",
            font=("Helvetica", 9, "bold"), relief="flat",
            activebackground="#666",
            command=_confirm_delete,
        ).place(x=70, y=105, width=80, height=28)

        tk.Button(
            confirm, text="Cancelar", bg="#888", fg="#FFF",
            font=("Helvetica", 9, "bold"), relief="flat",
            activebackground="#666",
            command=_cancel,
        ).place(x=170, y=105, width=80, height=28)

    def _refresh(self):
        if self.current_socio_id:
            self._load_socio_by_id(self.current_socio_id)


def open_window(parent=None, socio_id=None, on_deleted=None):
    return AnularCobrosWindow(parent, socio_id=socio_id, on_deleted=on_deleted)


if __name__ == "__main__":
    root = tk.Tk()
    root.withdraw()
    open_window(root)
    root.mainloop()
