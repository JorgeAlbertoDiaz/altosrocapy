"""Admin Pantalla — gestión de cuentas de usuario (tabla Login).

ABM de usuarios con recupero de contraseña. Se elige un MODO con un radio:

  - "Crear Usuario": muestra SOLO el formulario de alta de un usuario nuevo
    (Usuario, Contraseña, Nivel de Acceso) + botón REGISTRAR.
  - "Editar / Borrar / Recuperar": muestra la tabla de usuarios y, al
    seleccionar uno, permite modificar, eliminar o recuperar su contraseña.

La contraseña se muestra en texto plano para replicar el sistema legacy
(decisión de seguridad documentada en memoria) — NO hashear.

El Nivel de Acceso se toma de la tabla NivelAcceso (Administrador/Empleado).

Estética: WinForms / VB.NET clásica. Los radios guían al usuario para que el
alta y la edición no se mezclen.
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
FG_DISABLED = "#777777"
ENTRY_BG = "#FFFFFF"
ENTRY_DISABLED_BG = "#E8E8E8"
BTN_BLUE = "#3B6FA0"
BTN_BLUE_ACTIVE = "#2D5A85"
BTN_RED = "#C0392B"
BTN_RED_ACTIVE = "#A93226"
BTN_GRAY = "#D9D9D9"
BTN_GRAY_ACTIVE = "#BFBFBF"
BTN_GRAY_FG = "#333333"
BTN_GREEN = "#2E8B57"
BTN_GREEN_ACTIVE = "#246B43"
SEL_BG = "#0078D7"
FN = ("Helvetica", 9)
FN_B = ("Helvetica", 9, "bold")

W, H = 720, 560


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
        self._modo = tk.StringVar(value="crear")
        self.current_id = None
        self._build()
        self._refresh_grid()
        self._set_mode("crear")

    # ── Build ─────────────────────────────────────────────────────────────

    def _build(self):
        # === RADIOS DE MODO ===
        frm_modo = tk.Frame(self, bg=BG)
        frm_modo.place(x=15, y=12, width=690, height=34)

        tk.Label(frm_modo, text="Seleccione la operación:", bg=BG, font=FN_B,
                 fg=FG_LABEL).pack(side="left", padx=(0, 20))

        rb_crear = tk.Radiobutton(
            frm_modo, text="Crear usuario nuevo", variable=self._modo,
            value="crear", command=lambda: self._set_mode("crear"),
            bg=BG, fg=FG, font=FN, selectcolor="#FFFFFF", activebackground=BG,
            anchor="w")
        rb_crear.pack(side="left", padx=(0, 25))

        rb_editar = tk.Radiobutton(
            frm_modo, text="Editar / Borrar / Recuperar contraseña",
            variable=self._modo, value="editar",
            command=lambda: self._set_mode("editar"),
            bg=BG, fg=FG, font=FN, selectcolor="#FFFFFF", activebackground=BG,
            anchor="w")
        rb_editar.pack(side="left")

        # === VISTA CREAR ===
        self.frm_crear = tk.Frame(self, bg=BG)
        self.frm_crear.place(x=0, y=50, width=W, height=H - 50)

        info = tk.LabelFrame(
            self.frm_crear, text=" Alta de Usuario Nuevo ", bg=BG, font=FN_B,
            fg="#333333", relief="groove", bd=2, labelanchor="nw")
        info.place(x=15, y=10, width=690, height=210)

        tk.Label(info, text="Usuario:", bg=BG, font=FN,
                 fg=FG_LABEL).place(x=30, y=40)
        self.cr_user = tk.Entry(info, bg=ENTRY_BG, fg=FG, font=FN,
                                relief="solid", bd=1)
        self.cr_user.place(x=160, y=34, width=300, height=26)

        tk.Label(info, text="Contraseña:", bg=BG, font=FN,
                 fg=FG_LABEL).place(x=30, y=85)
        self.cr_pwd = tk.Entry(info, bg=ENTRY_BG, fg=FG, font=FN,
                               relief="solid", bd=1, show="*")
        self.cr_pwd.place(x=160, y=79, width=300, height=26)

        tk.Label(info, text="Nivel de Acceso:", bg=BG, font=FN,
                 fg=FG_LABEL).place(x=30, y=130)
        self.cr_nivel = ttk.Combobox(info, state="readonly", width=24, font=FN)
        self.cr_nivel["values"] = [n[1] for n in self._niveles]
        if self._niveles:
            self.cr_nivel.current(0)
        self.cr_nivel.place(x=160, y=124, width=300, height=26)

        tk.Label(info, text=("El usuario quedará habilitado para ingresar al "
                             "sistema."),
                 bg=BG, fg=FG_DISABLED, font=("Helvetica", 8)).place(x=30,
                                                                     y=170)

        self.btn_crear = tk.Button(
            self.frm_crear, text="REGISTRAR USUARIO", bg=BTN_GREEN, fg="#FFF",
            font=FN_B, relief="flat", activebackground=BTN_GREEN_ACTIVE,
            cursor="hand2", command=self._on_crear)
        self.btn_crear.place(x=440, y=235, width=180, height=34)

        # === VISTA EDITAR ===
        self.frm_editar = tk.Frame(self, bg=BG)
        self.frm_editar.place(x=0, y=50, width=W, height=H - 50)

        # Grid de usuarios
        frm_grid = tk.Frame(self.frm_editar, bg="#E8E8E8")
        frm_grid.place(x=15, y=10, width=690, height=250)

        cols = ("id", "user", "nivel")
        self.tree = ttk.Treeview(frm_grid, columns=cols, show="headings",
                                 selectmode="browse")
        self.tree.heading("id", text="ID")
        self.tree.heading("user", text="Usuario")
        self.tree.heading("nivel", text="Nivel de Acceso")
        self.tree.column("id", width=70, anchor="center", stretch=False)
        self.tree.column("user", width=280, stretch=True)
        self.tree.column("nivel", width=260, anchor="center", stretch=True)

        style = ttk.Style(self)
        style.configure("ADM.Treeview", rowheight=22, font=FN,
                        background="#FFF", fieldbackground="#FFF")
        style.configure("ADM.Treeview.Heading", font=FN_B)
        style.map("ADM.Treeview",
                  background=[("selected", SEL_BG)],
                  foreground=[("selected", "#FFF")])
        self.tree.configure(style="ADM.Treeview")

        vsb = ttk.Scrollbar(frm_grid, orient="vertical",
                            command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.place(x=0, y=0, relwidth=0.97, relheight=1.0)
        vsb.place(relx=0.975, y=0, relheight=1.0)
        self.tree.bind("<<TreeviewSelect>>", self._on_select)

        # Form de edición
        frm_edit = tk.LabelFrame(
            self.frm_editar, text=" Edición del Usuario Seleccionado ", bg=BG,
            font=FN_B, fg="#333333", relief="groove", bd=2, labelanchor="nw")
        frm_edit.place(x=15, y=270, width=690, height=180)

        tk.Label(frm_edit, text="Usuario:", bg=BG, font=FN,
                 fg=FG_LABEL).place(x=30, y=32)
        self.ed_user = tk.Entry(frm_edit, bg=ENTRY_BG, fg=FG, font=FN,
                                relief="solid", bd=1)
        self.ed_user.place(x=160, y=26, width=220, height=26)

        tk.Label(frm_edit, text="Contraseña:", bg=BG, font=FN,
                 fg=FG_LABEL).place(x=30, y=72)
        self.ed_pwd = tk.Entry(frm_edit, bg=ENTRY_BG, fg=FG, font=FN,
                               relief="solid", bd=1, show="*")
        self.ed_pwd.place(x=160, y=66, width=220, height=26)

        tk.Label(frm_edit, text="Nivel de Acceso:", bg=BG, font=FN,
                 fg=FG_LABEL).place(x=30, y=112)
        self.ed_nivel = ttk.Combobox(frm_edit, state="readonly", width=18,
                                     font=FN)
        self.ed_nivel["values"] = [n[1] for n in self._niveles]
        self.ed_nivel.place(x=160, y=106, width=220, height=26)

        self.btn_recuperar = tk.Button(
            frm_edit, text="Recuperar Contraseña", bg=BTN_BLUE, fg="#FFF",
            font=FN_B, relief="flat", activebackground=BTN_BLUE_ACTIVE,
            cursor="hand2", command=self._on_recuperar)
        self.btn_guardar_edit = tk.Button(
            frm_edit, text="Guardar Cambios", bg=BTN_GREEN, fg="#FFF",
            font=FN_B, relief="flat", activebackground=BTN_GREEN_ACTIVE,
            cursor="hand2", command=self._on_guardar_edit)
        self.btn_eliminar = tk.Button(
            frm_edit, text="Eliminar Usuario", bg=BTN_RED, fg="#FFF",
            font=FN_B, relief="flat", activebackground=BTN_RED_ACTIVE,
            cursor="hand2", command=self._on_eliminar)
        # Ocultos al inicio: se muestran al seleccionar un usuario.
        self._act_btns = [
            (self.btn_recuperar, 420, 26, 180, 28),
            (self.btn_guardar_edit, 420, 66, 180, 28),
            (self.btn_eliminar, 420, 106, 180, 28),
        ]
        self._set_action_buttons(False)

        self.btn_nuevo = tk.Button(
            self.frm_editar, text="Nuevo", bg=BTN_GRAY, fg=BTN_GRAY_FG,
            font=FN_B, relief="flat", activebackground=BTN_GRAY_ACTIVE,
            cursor="hand2", command=self._new_edit)
        self.btn_nuevo.place(x=W - 110, y=465, width=90, height=30)

    # ── Mode switching ────────────────────────────────────────────────────

    def _set_mode(self, modo):
        self._modo.set(modo)
        if modo == "crear":
            self.frm_crear.place(x=0, y=50, width=W, height=H - 50)
            self.frm_editar.place_forget()
            self.cr_user.focus_set()
        else:
            self.frm_editar.place(x=0, y=50, width=W, height=H - 50)
            self.frm_crear.place_forget()
            self._refresh_grid()
            self._new_edit()

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
        self.ed_user.delete(0, "end")
        self.ed_user.insert(0, vals[1])
        self.ed_pwd.delete(0, "end")
        nidx = next(
            (i for i, (_, n) in enumerate(self._niveles)
             if str(n) == str(vals[2]) or str(self._niveles[i][0]) == str(vals[2])),
            -1)
        self.ed_nivel.current(nidx if nidx >= 0 else 0)
        self._set_action_buttons(True)

    def _set_action_buttons(self, visible):
        """Muestra/oculta Guardar/Eliminar/Recuperar según haya selección."""
        if visible:
            for btn, x, y, w, h in self._act_btns:
                btn.place(x=x, y=y, width=w, height=h)
        else:
            for btn, *_ in self._act_btns:
                btn.place_forget()

    # ── State helpers ─────────────────────────────────────────────────────

    def _new_edit(self):
        self.current_id = None
        self.tree.selection_remove(self.tree.selection())
        self.ed_user.delete(0, "end")
        self.ed_pwd.delete(0, "end")
        if self._niveles:
            self.ed_nivel.current(0)
        self._set_action_buttons(False)

    def _cr_nivel_id(self):
        idx = self.cr_nivel.current()
        return self._niveles[idx][0] if 0 <= idx < len(self._niveles) else ""

    def _ed_nivel_id(self):
        idx = self.ed_nivel.current()
        return self._niveles[idx][0] if 0 <= idx < len(self._niveles) else ""

    # ── Actions: CREATE ───────────────────────────────────────────────────

    def _on_crear(self):
        user = self.cr_user.get().strip()
        pwd = self.cr_pwd.get().strip()
        if not user:
            messagebox.showwarning("Registrar", "Ingrese el nombre de usuario.",
                                   parent=self)
            self.cr_user.focus_set()
            return
        if not pwd:
            messagebox.showwarning("Registrar", "Ingrese la contraseña.",
                                   parent=self)
            self.cr_pwd.focus_set()
            return
        uid = _insert_user(user, pwd, self._cr_nivel_id())
        messagebox.showinfo(
            "Registrar",
            f"Usuario '{user}' creado (ID {uid}) con contraseña: {pwd}",
            parent=self)
        self.cr_user.delete(0, "end")
        self.cr_pwd.delete(0, "end")
        if self._niveles:
            self.cr_nivel.current(0)
        self.cr_user.focus_set()
        self._refresh_grid()

    # ── Actions: EDIT ─────────────────────────────────────────────────────

    def _on_guardar_edit(self):
        if self.current_id is None:
            return
        user = self.ed_user.get().strip()
        pwd = self.ed_pwd.get().strip()
        if not user:
            messagebox.showwarning("Guardar", "El nombre de usuario es obligatorio.",
                                   parent=self)
            return
        if not pwd:
            messagebox.showwarning("Guardar", "La contraseña es obligatoria.",
                                   parent=self)
            return
        _update_user(self.current_id, user, pwd, self._ed_nivel_id())
        messagebox.showinfo("Guardar", "Usuario modificado.", parent=self)
        self._refresh_grid()
        self._new_edit()

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
        self._new_edit()
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
