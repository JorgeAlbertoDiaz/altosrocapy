"""Admin Pantalla — gestión de cuentas de usuario (tabla Login).

ABM de usuarios con recupero de contraseña:
  - Alta, modificación y baja de usuarios.
  - Ver/recuperar contraseña del usuario seleccionado (texto plano, replicando
    el sistema legacy — ver decisión de seguridad en memoria).
  - Nivel de acceso desde la tabla NivelAcceso (Administrador/Empleado).

Estética: WinForms / VB.NET clásica.
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

W, H = 640, 500


# ── Helpers / Data ────────────────────────────────────────────────────────

def _next_user_id():
    conn = db.get_connection()
    try:
        r = conn.execute(
            "SELECT MAX(CAST(UserID AS INTEGER)) FROM Login "
            "WHERE UserID GLOB '[0-9]*'").fetchone()
        return str((r[0] or 0) + 1)
    finally:
        conn.close()


def _niveles():
    conn = db.get_connection()
    try:
        rows = conn.execute(
            "SELECT idNivel, Nivel FROM NivelAcceso "
            "WHERE idNivel GLOB '[0-9]*' ORDER BY CAST(idNivel AS INTEGER)"
        ).fetchall()
        return [(str(r[0]), r[1]) for r in rows]
    finally:
        conn.close()


def _usuarios():
    conn = db.get_connection()
    try:
        rows = conn.execute(
            "SELECT UserID, UserName, Password, NivelAcceso "
            "FROM Login WHERE UserID GLOB '[0-9]*' "
            "ORDER BY CAST(UserID AS INTEGER)").fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def _insert_user(user, pwd, nivel):
    conn = db.get_connection()
    try:
        uid = _next_user_id()
        conn.execute(
            "INSERT INTO Login (UserID, UserName, Password, NivelAcceso) "
            "VALUES (?, ?, ?, ?)", (uid, user, pwd, nivel))
        conn.commit()
        return uid
    finally:
        conn.close()


def _update_user(uid, user, pwd, nivel):
    conn = db.get_connection()
    try:
        conn.execute(
            "UPDATE Login SET UserName=?, Password=?, NivelAcceso=? "
            "WHERE UserID=?", (user, pwd, nivel, str(uid)))
        conn.commit()
    finally:
        conn.close()


def _delete_user(uid):
    conn = db.get_connection()
    try:
        conn.execute("DELETE FROM Login WHERE UserID=?", (str(uid),))
        conn.commit()
    finally:
        conn.close()


def _find_user(uid):
    conn = db.get_connection()
    try:
        r = conn.execute(
            "SELECT UserID, UserName, Password, NivelAcceso "
            "FROM Login WHERE UserID=?", (str(uid),)).fetchone()
        return dict(r) if r else None
    finally:
        conn.close()


# ── Main Window ───────────────────────────────────────────────────────────

class AdminCuentasWindow(tk.Toplevel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.title("Admin Pantalla - Administración de Usuarios")
        self.geometry(f"{W}x{H}")
        self.resizable(False, False)
        self.configure(bg=BG)
        self.bind("<Escape>", lambda _: self.destroy())

        self._niveles = _niveles()
        self.current_id = None
        self._build()
        self._refresh_grid()
        self._form_state_new()

    def _build(self):
        # === GRID ===
        frm_grid = tk.Frame(self, bg="#E8E8E8")
        frm_grid.place(x=15, y=15, width=W - 30, height=230)

        cols = ("id", "user", "nivel")
        self.tree = ttk.Treeview(frm_grid, columns=cols, show="headings",
                                 selectmode="browse")
        self.tree.heading("id", text="ID")
        self.tree.heading("user", text="Usuario")
        self.tree.heading("nivel", text="Nivel de Acceso")
        self.tree.column("id", width=60, anchor="center", stretch=False)
        self.tree.column("user", width=220, stretch=True)
        self.tree.column("nivel", width=200, anchor="center", stretch=True)

        style = ttk.Style(self)
        style.configure("ADM.Treeview", rowheight=22, font=FN,
                        background="#FFF", fieldbackground="#FFF")
        style.configure("ADM.Treeview.Heading", font=FN_B)
        style.map("ADM.Treeview",
                  background=[("selected", SEL_BG)],
                  foreground=[("selected", "#FFF")])
        self.tree.configure(style="ADM.Treeview")

        vsb = ttk.Scrollbar(frm_grid, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.place(x=0, y=0, relwidth=0.985, relheight=1.0)
        vsb.place(relx=0.985, y=0, relheight=1.0)
        self.tree.bind("<<TreeviewSelect>>", self._on_select)

        # === FORM ===
        self.frm_form = tk.LabelFrame(
            self, text=" Datos del Usuario ", bg=BG, font=FN_B, fg="#333333",
            relief="groove", bd=2, labelanchor="nw")
        self.frm_form.place(x=15, y=255, width=W - 30, height=150)

        tk.Label(self.frm_form, text="Usuario:", bg=BG, font=FN,
                 fg=FG_LABEL).place(x=20, y=25)
        self.entry_user = tk.Entry(self.frm_form, bg=ENTRY_BG, fg=FG, font=FN,
                                   relief="solid", bd=1)
        self.entry_user.place(x=110, y=20, width=220, height=24)

        tk.Label(self.frm_form, text="Contraseña:", bg=BG, font=FN,
                 fg=FG_LABEL).place(x=20, y=60)
        self.entry_pwd = tk.Entry(self.frm_form, bg=ENTRY_BG, fg=FG, font=FN,
                                  relief="solid", bd=1, show="*")
        self.entry_pwd.place(x=110, y=55, width=220, height=24)

        tk.Label(self.frm_form, text="Nivel de Acceso:", bg=BG, font=FN,
                 fg=FG_LABEL).place(x=365, y=25)
        self.nivel_var = tk.StringVar()
        self.combo_nivel = ttk.Combobox(
            self.frm_form, textvariable=self.nivel_var, state="readonly",
            width=22, font=FN)
        self.combo_nivel["values"] = [n[1] for n in self._niveles]
        self.combo_nivel.place(x=470, y=20, width=150, height=24)

        # Recuperar contraseña button (in panel)
        self.btn_recuperar = tk.Button(
            self.frm_form, text="Recuperar Contraseña", bg=BTN_BLUE, fg="#FFF",
            font=FN_B, relief="flat", activebackground=BTN_BLUE_ACTIVE,
            cursor="hand2", command=self._on_recuperar, state="disabled")
        self.btn_recuperar.place(x=110, y=95, width=170, height=28)

        # === BOTONES ===
        self.btn_nuevo = tk.Button(
            self, text="Nuevo", bg=BTN_GRAY, fg="#FFF", font=FN_B,
            relief="flat", activebackground=BTN_GRAY_ACTIVE, cursor="hand2",
            command=self._form_state_new)
        self.btn_nuevo.place(x=15, y=425, width=80, height=30)

        self.btn_guardar = tk.Button(
            self, text="Guardar", bg=BTN_BLUE, fg="#FFF", font=FN_B,
            relief="flat", activebackground=BTN_BLUE_ACTIVE, cursor="hand2",
            command=self._on_guardar)
        self.btn_guardar.place(x=105, y=425, width=90, height=30)

        self.btn_eliminar = tk.Button(
            self, text="Eliminar", bg=BTN_RED, fg="#FFF", font=FN_B,
            relief="flat", activebackground=BTN_RED_ACTIVE, cursor="hand2",
            command=self._on_eliminar, state="disabled")
        self.btn_eliminar.place(x=205, y=425, width=90, height=30)

        self.btn_cancelar = tk.Button(
            self, text="Cancelar", bg=BTN_GRAY, fg="#FFF", font=FN_B,
            relief="flat", activebackground=BTN_GRAY_ACTIVE, cursor="hand2",
            command=self._form_state_new)
        self.btn_cancelar.place(x=W - 105, y=425, width=90, height=30)

    # ── Grid ──────────────────────────────────────────────────────────────

    def _refresh_grid(self):
        self.tree.delete(*self.tree.get_children())
        for u in _usuarios():
            self.tree.insert("", "end", values=(
                u["UserID"], u["UserName"], u["NivelAcceso"]))

    def _on_select(self, _event):
        sel = self.tree.selection()
        if not sel:
            return
        vals = self.tree.item(sel[0], "values")
        self.current_id = str(vals[0])
        self.entry_user.delete(0, "end")
        self.entry_user.insert(0, vals[1])
        # No fill password by default (hidden); nivel by matching value
        self.entry_pwd.delete(0, "end")
        nidx = next((i for i, (_, n) in enumerate(self._niveles)
                     if str(n) == str(vals[2]) or str(self._niveles[i][0]) == str(vals[2])), -1)
        if nidx >= 0:
            self.combo_nivel.current(nidx)
        else:
            self.nivel_var.set("")
        self.btn_eliminar.configure(state="normal")
        self.btn_recuperar.configure(state="normal")

    # ── Form state ────────────────────────────────────────────────────────

    def _clear_form(self):
        self.entry_user.delete(0, "end")
        self.entry_pwd.delete(0, "end")
        if self._niveles:
            self.combo_nivel.current(0)
        self.current_id = None
        self.btn_eliminar.configure(state="disabled")
        self.btn_recuperar.configure(state="disabled")

    def _form_state_new(self):
        self._clear_form()
        self.tree.selection_remove(self.tree.selection())

    # ── Actions ───────────────────────────────────────────────────────────

    def _nivel_id(self):
        idx = self.combo_nivel.current()
        if idx >= 0:
            return self._niveles[idx][0]
        return ""

    def _on_guardar(self):
        user = self.entry_user.get().strip()
        pwd = self.entry_pwd.get().strip()
        if not user:
            messagebox.showwarning("Guardar", "El nombre de usuario es obligatorio.",
                                   parent=self)
            return
        if not pwd:
            messagebox.showwarning("Guardar", "La contraseña es obligatoria.",
                                   parent=self)
            return

        if self.current_id is None:
            uid = _insert_user(user, pwd, self._nivel_id())
            messagebox.showinfo("Guardar",
                                f"Usuario creado (ID {uid}) con contraseña: {pwd}",
                                parent=self)
        else:
            _update_user(self.current_id, user, pwd, self._nivel_id())
            messagebox.showinfo("Guardar", "Usuario modificado.", parent=self)

        self._refresh_grid()
        self._form_state_new()

    def _on_eliminar(self):
        if self.current_id is None:
            return
        if not messagebox.askyesno(
                "Confirmar",
                f"¿Desea eliminar el usuario ID {self.current_id}?",
                parent=self):
            return
        _delete_user(self.current_id)
        self._refresh_grid()
        self._form_state_new()
        messagebox.showinfo("Eliminar", "Usuario eliminado.", parent=self)

    def _on_recuperar(self):
        if self.current_id is None:
            return
        u = _find_user(self.current_id)
        if u is None:
            messagebox.showinfo("Recuperar", "Usuario no encontrado.", parent=self)
            return
        messagebox.showinfo(
            "Recuperar Contraseña",
            f"Usuario: {u['UserName']}\n\n"
            f"Contraseña actual: {u['Password']}\n"
            f"Nivel de acceso: {u['NivelAcceso']}",
            parent=self)


def open_window(parent=None):
    return AdminCuentasWindow(parent)


if __name__ == "__main__":
    root = tk.Tk()
    root.withdraw()
    open_window(root)
    root.mainloop()
