"""ABM Genérico — alta, modificación y baja de tablas de control.

Ventana CRUD parametrizable usada por "Alta de Datos" para administrar tablas
que no tienen otro flujo de mantenimiento (planes, formas de pago, tipos de
gasto/ingreso, etc.).

Sin modernizar: estética WinForms / VB.NET clásica. Soft-delete cuando la tabla
tiene columna 'Eliminado', borrado físico en caso contrario. El ID se genera
automáticamente (MAX + 1), igual que el resto de la aplicación.
"""

import tkinter as tk
from tkinter import ttk, messagebox

try:
    from app import db
except ImportError:
    import db

# ── Constants ─────────────────────────────────────────────────────────────

BG = "#F0F0F0"
FG = "#000000"
FG_LABEL = "#000000"
ENTRY_BG = "#FFFFFF"
BTN_BLUE = "#3B6FA0"
BTN_BLUE_ACTIVE = "#2D5A85"
BTN_RED = "#C0392B"
BTN_RED_ACTIVE = "#A93226"
BTN_GRAY = "#888888"
BTN_GRAY_ACTIVE = "#666666"
SEL_BG = "#0078D7"
FN = ("Helvetica", 9)
FN_B = ("Helvetica", 9, "bold")


# ── Config ────────────────────────────────────────────────────────────────

# Cada entrada: (titulo, tabla, col_id, [columnas editables], ancho_grid)
ABM_CONFIGS = {
    "Planes": {
        "tabla": "tbPlan", "col_id": "idPlan",
        "col_eliminado": "Eliminado", "titulo_sing": "plan",
        "cols": [
            ("Nomenclatura", "Nomenclatura", 120),
            ("Descripción", "Descripcion", 220),
            ("Precio Vigente", "PrecioVigente", 110),
            ("Cant. Clases", "CantidadClases", 90),
        ],
    },
    "Formas de Pago": {
        "tabla": "tb_TipoPago", "col_id": "Id",
        "col_eliminado": None, "titulo_sing": "forma de pago",
        "cols": [
            ("Descripción", "Descripcion", 260),
        ],
    },
    "Tipos de Gasto": {
        "tabla": "tbTiposGastos", "col_id": "idTipoGasto",
        "col_eliminado": "Eliminado", "titulo_sing": "tipo de gasto",
        "cols": [
            ("Descripción", "Descripcion", 300),
        ],
    },
    "Tipos de Ingreso": {
        "tabla": "tbTiposIngresos", "col_id": "idTipoIngresos",
        "col_eliminado": "Eliminado", "titulo_sing": "tipo de ingreso",
        "cols": [
            ("Descripción", "Descripcion", 300),
        ],
    },
}


# ── Helpers / Data ────────────────────────────────────────────────────────

def _rows(cfg, solo_activos=True):
    """Load rows as list of dicts. Excludes the placeholder garbage row."""
    conn = db.get_connection()
    try:
        tabla, col_id = cfg["tabla"], cfg["col_id"]
        col_elim = cfg.get("col_eliminado")
        col_names = [col_id] + [c[1] for c in cfg["cols"]]
        qcols = ", ".join(f"[{c}]" for c in col_names)
        where = []
        if col_elim:
            where.append(f"([{col_elim}] IS NULL OR [{col_elim}] != '1')")
        # Exclude the legacy placeholder row where id is non-numeric dashes
        where.append(f"([{col_id}] GLOB '[0-9]*')")
        sql = f"SELECT {qcols} FROM [{tabla}]"
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += f" ORDER BY CAST([{col_id}] AS INTEGER)"
        rows = conn.execute(sql).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def _next_id(cfg):
    conn = db.get_connection()
    try:
        tabla, col_id = cfg["tabla"], cfg["col_id"]
        row = conn.execute(
            f"SELECT MAX(CAST([{col_id}] AS INTEGER)) FROM [{tabla}] "
            f"WHERE [{col_id}] GLOB '[0-9]*'").fetchone()
        return str((row[0] or 0) + 1)
    finally:
        conn.close()


def _insert(cfg, vals):
    conn = db.get_connection()
    try:
        tabla = cfg["tabla"]
        col_id = cfg["col_id"]
        cols = [col_id] + [c[1] for c in cfg["cols"]]
        qcols = ", ".join(f"[{c}]" for c in cols)
        marks = ", ".join("?" for _ in cols)
        conn.execute(f"INSERT INTO [{tabla}] ({qcols}) VALUES ({marks})", vals)
        conn.commit()
    finally:
        conn.close()


def _update(cfg, id_val, vals):
    conn = db.get_connection()
    try:
        tabla = cfg["tabla"]
        col_id = cfg["col_id"]
        sets = ", ".join(f"[{c[1]}]=?" for c in cfg["cols"])
        conn.execute(f"UPDATE [{tabla}] SET {sets} WHERE [{col_id}]=?",
                     vals + [str(id_val)])
        conn.commit()
    finally:
        conn.close()


def _soft_delete(cfg, id_val):
    conn = db.get_connection()
    try:
        col_elim = cfg["col_eliminado"]
        conn.execute(
            f"UPDATE [{cfg['tabla']}] SET [{col_elim}] = '1' "
            f"WHERE [{cfg['col_id']}] = ?", (str(id_val),))
        conn.commit()
    finally:
        conn.close()


def _hard_delete(cfg, id_val):
    conn = db.get_connection()
    try:
        conn.execute(
            f"DELETE FROM [{cfg['tabla']}] WHERE [{cfg['col_id']}] = ?",
            (str(id_val),))
        conn.commit()
    finally:
        conn.close()


# ── Main Window ───────────────────────────────────────────────────────────

class ABMWindow(tk.Toplevel):
    def __init__(self, parent=None, titulo=None):
        super().__init__(parent)
        if titulo is None:
            titulo = "ABM"
        self.cfg = ABM_CONFIGS.get(titulo)
        if self.cfg is None:
            self.destroy()
            raise ValueError(f"Config ABM no encontrada: {titulo}")

        self.title(titulo)
        n_cols = len(self.cfg["cols"])
        self.W = max(620, 30 + sum(w for _, _, w in self.cfg["cols"]) + 90)
        self.H = 470
        self.geometry(f"{self.W}x{self.H}")
        self.resizable(False, False)
        self.configure(bg=BG)
        self.bind("<Escape>", lambda _: self.destroy())

        self.current_id = None  # id of the row being edited (None = nuevo)
        self._build()
        self._refresh_grid()
        self._form_state_new()

    def _build(self):
        # === GRID ===
        frm_grid = tk.Frame(self, bg="#E8E8E8")
        frm_grid.place(x=15, y=15, width=self.W - 30, height=250)

        cols = ("id",) + tuple(c[1] for c in self.cfg["cols"])
        headings = ("ID",) + tuple(c[0] for c in self.cfg["cols"])
        self.tree = ttk.Treeview(frm_grid, columns=cols, show="headings",
                                 selectmode="browse")
        for cid, h in zip(cols, headings):
            self.tree.heading(cid, text=h)
        self.tree.column("id", width=50, anchor="center", stretch=False)
        for i, (label, cname, w) in enumerate(self.cfg["cols"]):
            self.tree.column(cname, width=w, stretch=True)

        style = ttk.Style(self)
        style.configure("ABM.Treeview", rowheight=22, font=FN,
                        background="#FFF", fieldbackground="#FFF")
        style.configure("ABM.Treeview.Heading", font=FN_B)
        style.map("ABM.Treeview",
                  background=[("selected", SEL_BG)],
                  foreground=[("selected", "#FFF")])
        self.tree.configure(style="ABM.Treeview")

        vsb = ttk.Scrollbar(frm_grid, orient="vertical",
                            command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.place(x=0, y=0, relwidth=0.985, relheight=1.0)
        vsb.place(relx=0.985, y=0, relheight=1.0)
        self.tree.bind("<<TreeviewSelect>>", self._on_select)

        # === FORM GROUPBOX ===
        self.frm_form = tk.LabelFrame(
            self, text=" Datos ", bg=BG, font=FN_B, fg="#333333",
            relief="groove", bd=2, labelanchor="nw")
        self.frm_form.place(x=15, y=275, width=self.W - 30, height=130)

        self.entries = {}
        # Layout entries: up to 2 per row
        x_row_max = 2
        for i, (label, cname, w) in enumerate(self.cfg["cols"]):
            row, col = divmod(i, x_row_max)
            x = 20 + col * ((self.W - 60) // 2)
            y = 22 + row * 48
            tk.Label(self.frm_form, text=f"{label}:", bg=BG, font=FN,
                     fg=FG_LABEL).place(x=x, y=y)
            e = tk.Entry(self.frm_form, bg=ENTRY_BG, fg=FG, font=FN,
                         relief="solid", bd=1)
            e.place(x=x + 110, y=y - 3, width=w + 60, height=24)
            self.entries[cname] = e

        # === BOTTONS ===
        self.btn_nuevo = tk.Button(
            self, text="Nuevo", bg=BTN_GRAY, fg="#FFF", font=FN_B,
            relief="flat", activebackground=BTN_GRAY_ACTIVE, cursor="hand2",
            command=self._form_state_new)
        self.btn_nuevo.place(x=15, y=420, width=80, height=30)

        self.btn_guardar = tk.Button(
            self, text="Guardar", bg=BTN_BLUE, fg="#FFF", font=FN_B,
            relief="flat", activebackground=BTN_BLUE_ACTIVE, cursor="hand2",
            command=self._on_guardar)
        self.btn_guardar.place(x=105, y=420, width=90, height=30)

        self.btn_eliminar = tk.Button(
            self, text="Eliminar", bg=BTN_RED, fg="#FFF", font=FN_B,
            relief="flat", activebackground=BTN_RED_ACTIVE, cursor="hand2",
            command=self._on_eliminar, state="disabled")
        self.btn_eliminar.place(x=205, y=420, width=90, height=30)

        self.btn_cancelar = tk.Button(
            self, text="Cancelar", bg=BTN_GRAY, fg="#FFF", font=FN_B,
            relief="flat", activebackground=BTN_GRAY_ACTIVE, cursor="hand2",
            command=self._form_state_new)
        self.btn_cancelar.place(x=self.W - 105, y=420, width=90, height=30)

    # ── Grid ──────────────────────────────────────────────────────────────

    def _refresh_grid(self):
        self.tree.delete(*self.tree.get_children())
        for r in _rows(self.cfg):
            self.tree.insert("", "end", values=(
                r[self.cfg["col_id"]],
                *[r[c[1]] or "" for c in self.cfg["cols"]],
            ))

    def _on_select(self, _event):
        sel = self.tree.selection()
        if not sel:
            return
        vals = self.tree.item(sel[0], "values")
        self.current_id = str(vals[0])
        for i, (_, cname, _) in enumerate(self.cfg["cols"]):
            self.entries[cname].delete(0, "end")
            self.entries[cname].insert(0, vals[i + 1] if vals[i + 1] else "")
        self.btn_eliminar.configure(state="normal")

    # ── Form state ────────────────────────────────────────────────────────

    def _clear_form(self):
        for e in self.entries.values():
            e.delete(0, "end")
        self.current_id = None
        self.btn_eliminar.configure(state="disabled")

    def _form_state_new(self):
        self._clear_form()
        self.tree.selection_remove(self.tree.selection())

    # ── Actions ───────────────────────────────────────────────────────────

    def _on_guardar(self):
        vals = []
        for _, cname, _ in self.cfg["cols"]:
            raw = self.entries[cname].get().strip()
            vals.append(raw)

        # Validación: al menos el primer campo (descripción/nombre) obligatorio
        if not vals[0]:
            messagebox.showwarning(
                "Guardar",
                f"Complete la {self.cfg['cols'][0][0].lower()}.",
                parent=self)
            return

        titulo_sing = self.cfg["titulo_sing"]
        if self.current_id is None:
            # NUEVO
            new_id = _next_id(self.cfg)
            _insert(self.cfg, [new_id] + vals)
            messagebox.showinfo("Guardar",
                                f"{titulo_sing.capitalize()} creado (ID {new_id}).",
                                parent=self)
        else:
            # MODIFICAR
            _update(self.cfg, self.current_id, vals)
            messagebox.showinfo("Guardar",
                                f"{titulo_sing.capitalize()} modificado.",
                                parent=self)

        self._refresh_grid()
        self._form_state_new()

    def _on_eliminar(self):
        if self.current_id is None:
            return
        titulo_sing = self.cfg["titulo_sing"]
        if not messagebox.askyesno(
                "Confirmar",
                f"¿Desea eliminar el {titulo_sing} ID {self.current_id}?",
                parent=self):
            return
        if self.cfg.get("col_eliminado"):
            _soft_delete(self.cfg, self.current_id)
        else:
            _hard_delete(self.cfg, self.current_id)
        self._refresh_grid()
        self._form_state_new()
        messagebox.showinfo("Eliminar", f"{titulo_sing.capitalize()} eliminado.",
                            parent=self)


def open_window(parent=None, titulo=None):
    return ABMWindow(parent, titulo=titulo)


if __name__ == "__main__":
    root = tk.Tk()
    root.withdraw()
    open_window(root, "Planes")
    root.mainloop()
