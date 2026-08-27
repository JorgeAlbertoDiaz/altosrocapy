"""Historial de Cobros — consulta de ingresos (cobros) del gimnasio.

Similar a "Ingresos / Caja" pero EXCLUSIVAMENTE de ingreso (sin gastos):
  - Cobros de cuotas (tbPagos)
  - Cobros de deudas (tb_RegistroDeudas canceladas)
  - Ingresos manuales (tbIngresosGenerales)

Estética: WinForms / VB.NET clásica. Lista cronológica (más antiguo arriba).
Las consultas con filtros muestran un indicador de procesamiento para que el
usuario sepa que el sistema está trabajando.
"""

import datetime
import threading
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

try:
    from tkcalendar import DateEntry
except ImportError:
    DateEntry = None

try:
    from app import db
    from app import caja as _caja
except ImportError:
    import db
    import caja as _caja

# ── Constants ─────────────────────────────────────────────────────────────

W, H = 900, 520
BG = "#F0F0F0"
FG = "#000000"
BTN_BLUE = "#3B6FA0"
BTN_BLUE_ACTIVE = "#2D5A85"
SEL_BG = "#0078D7"
FN = ("Helvetica", 9)
FN_B = ("Helvetica", 9, "bold")

MESES = _caja.MESES


# ── Main Window ───────────────────────────────────────────────────────────

class HistorialCobrosWindow(tk.Toplevel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.title("Historial de Cobros")
        self.geometry(f"{W}x{H}")
        self.resizable(False, False)
        self.configure(bg=BG)
        self.bind("<Escape>", lambda _: self.destroy())

        self._movs = []
        self._saldo_acum = []
        self._build()
        self._toggle_mode()

    def _build(self):
        frm = tk.Frame(self, bg=BG)
        frm.place(x=15, y=15, width=870, height=85)

        # --- Caja Diaria (radio, by default) ---
        self.diaria_var = tk.StringVar(value="diaria")
        tk.Radiobutton(frm, text="Caja Diaria", variable=self.diaria_var,
                       value="diaria", bg=BG, font=FN, fg=FG,
                       command=self._toggle_mode).place(x=0, y=0)
        self.dt_fecha = None
        if DateEntry is not None:
            self.dt_fecha = DateEntry(frm, width=22, background="#3B6FA0",
                                      foreground="white", borderwidth=1,
                                      date_pattern="dd/mm/yyyy", font=FN)
            self.dt_fecha.place(x=0, y=25, width=230, height=25)
        else:
            self.entry_fecha = tk.Entry(frm, bg="#FFFFFF", fg=FG, font=FN,
                                        relief="solid", bd=1)
            self.entry_fecha.place(x=0, y=25, width=230, height=25)

        # --- Filtrar por Período Mensual (radio) ---
        tk.Radiobutton(frm, text="Filtrar por Período Mensual",
                       variable=self.diaria_var, value="mensual",
                       bg=BG, font=FN, fg=FG,
                       command=self._toggle_mode).place(x=250, y=0)

        self.anio_var = tk.StringVar(value=str(datetime.date.today().year))
        self.spin_anio = tk.Spinbox(frm, from_=2000, to=2100,
                                    textvariable=self.anio_var, width=5,
                                    font=FN, command=self._on_change, increment=1)
        self.spin_anio.place(x=250, y=25, width=70, height=25)
        self.anio_var.trace_add("write", lambda *_: self._on_change())

        self.mes_var = tk.StringVar(value=MESES[datetime.date.today().month - 1])
        self.cb_mes = ttk.Combobox(frm, values=MESES, textvariable=self.mes_var,
                                   state="readonly", font=FN, width=12)
        self.cb_mes.place(x=330, y=25, width=110, height=25)
        self.cb_mes.bind("<<ComboboxSelected>>", lambda _: self._on_change())

        # --- Filtro Usuario ---
        tk.Label(frm, text="Usuario", bg=BG, fg=FG, font=FN).place(x=470, y=0)
        self.usuario_var = tk.StringVar(value="Todos")
        usuarios = ["Todos"] + self._lista_usuarios()
        self.cb_usu = ttk.Combobox(frm, values=usuarios,
                                   textvariable=self.usuario_var,
                                   state="readonly", font=FN, width=12)
        self.cb_usu.place(x=470, y=25, width=100, height=25)
        self.cb_usu.bind("<<ComboboxSelected>>", lambda _: self._on_change())

        # --- Actualizar datos ---
        tk.Button(frm, text="Actualizar datos", bg=BTN_BLUE, fg="#FFF",
                  font=FN_B, relief="flat", activebackground=BTN_BLUE_ACTIVE,
                  cursor="hand2", command=self._refresh).place(x=620, y=32,
                                                               width=110,
                                                               height=25)

        # === MAIN GRID ===
        frm_grid = tk.Frame(self, bg="#E8E8E8")
        frm_grid.place(x=15, y=110, width=870, height=315)

        cols = ("id", "detalle", "haber", "saldo")
        self.tree = ttk.Treeview(frm_grid, columns=cols, show="headings",
                                 selectmode="browse")
        self.tree.heading("id", text="ID")
        self.tree.heading("detalle", text="Detalle")
        self.tree.heading("haber", text="Ingreso")
        self.tree.heading("saldo", text="Saldo")
        self.tree.column("id", width=50, anchor="center", stretch=False)
        self.tree.column("detalle", width=520, stretch=True)
        self.tree.column("haber", width=120, anchor="e", stretch=False)
        self.tree.column("saldo", width=140, anchor="e", stretch=False)

        style = ttk.Style(self)
        style.configure("HC.Treeview", rowheight=22, font=FN,
                        background="#FFF", fieldbackground="#FFF")
        style.configure("HC.Treeview.Heading", font=FN_B)
        style.map("HC.Treeview",
                  background=[("selected", SEL_BG)],
                  foreground=[("selected", "#FFF")])
        self.tree.configure(style="HC.Treeview")

        vsb = ttk.Scrollbar(frm_grid, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(frm_grid, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self.tree.place(x=0, y=0, relwidth=0.985, relheight=0.96)
        vsb.place(relx=0.985, y=0, relheight=0.96)
        hsb.place(x=0, rely=0.96, relwidth=0.985)

        self.lbl_proc = tk.Label(
            frm_grid, text="⏳ Procesando reporte...", bg="#FFFBCC",
            fg="#7A5B00", font=("Helvetica", 14, "bold"), relief="solid", bd=1,
        )
        self.lbl_proc.place_forget()

        # === BOTTOM PANEL ===
        frm_bot = tk.Frame(self, bg=BG)
        frm_bot.place(x=15, y=440, width=870, height=60)

        tk.Label(frm_bot, text="TOTAL COBRADO:", bg=BG, fg=FG,
                 font=FN_B).place(x=0, y=15)
        self.lbl_total = tk.Label(frm_bot, text="", bg=BG, fg="#003399",
                                  font=("Helvetica", 13, "bold"))
        self.lbl_total.place(x=120, y=13)

        tk.Button(frm_bot, text="Exportar a Excel", bg=BTN_BLUE, fg="#FFF",
                  font=FN_B, relief="flat", activebackground=BTN_BLUE_ACTIVE,
                  cursor="hand2", command=self._exportar_excel).place(
            x=640, y=8, width=125, height=25)

        tk.Button(frm_bot, text="Salir", bg="#999", fg="#FFF", font=FN_B,
                  relief="flat", activebackground="#777", cursor="hand2",
                  command=self.destroy).place(x=795, y=8, width=75, height=25)

    # ── Filters ───────────────────────────────────────────────────────────

    def _lista_usuarios(self):
        conn = db.get_connection()
        try:
            s = set()
            for r in conn.execute(
                "SELECT UsuarioCobrador FROM tbPagos WHERE UsuarioCobrador IS NOT NULL"):
                if str(r[0]).strip() != "-------":
                    s.add(str(r[0]).strip())
            for r in conn.execute(
                "SELECT UsuarioCobrador FROM tbIngresosGenerales "
                "WHERE UsuarioCobrador IS NOT NULL"):
                if str(r[0]).strip() != "-------":
                    s.add(str(r[0]).strip())
            return sorted(s)
        finally:
            conn.close()

    def _toggle_mode(self):
        if self.diaria_var.get() == "diaria":
            if self.dt_fecha is not None:
                self.dt_fecha.configure(state="normal")
            else:
                self.entry_fecha.configure(state="normal")
            self.spin_anio.configure(state="disabled")
            self.cb_mes.configure(state="disabled")
        else:
            if self.dt_fecha is not None:
                self.dt_fecha.configure(state="disabled")
            else:
                self.entry_fecha.configure(state="disabled")
            self.spin_anio.configure(state="normal")
            self.cb_mes.configure(state="readonly")
        self._refresh()

    def _on_change(self):
        self._refresh()

    def _rango(self):
        if self.diaria_var.get() == "diaria":
            if self.dt_fecha is not None:
                d = self.dt_fecha.get_date()
            else:
                parts = self.entry_fecha.get().split("/")
                d = datetime.date(int(parts[2]), int(parts[1]), int(parts[0]))
            return (f"{d:%Y-%m-%d} 00:00:00", f"{d:%Y-%m-%d} 23:59:59")
        else:
            import calendar
            anio = int(self.anio_var.get())
            mes = MESES.index(self.mes_var.get()) + 1
            last = calendar.monthrange(anio, mes)[1]
            return (f"{anio:04d}-{mes:02d}-01 00:00:00",
                    f"{anio:04d}-{mes:02d}-{last:02d} 23:59:59")

    # ── Refresh (async, only income movements) ───────────────────────────

    def _refresh(self):
        fecha_d, fecha_h = self._rango()
        usuario = self.usuario_var.get()
        usuario = None if usuario == "Todos" else usuario

        self.lbl_proc.place(relx=0.5, rely=0.5, anchor="center")
        self.tree.configure(cursor="watch")
        self.update_idletasks()

        def _worker():
            try:
                movs = _caja._collect_movements(
                    fecha_d, fecha_h, usuario, None,
                    True, False)  # solo ingresos, sin gastos
            except Exception as e:
                self.after(0, lambda: self._apply_worker_error(e))
                return
            self.after(0, lambda: self._apply_movements(movs))

        threading.Thread(target=_worker, daemon=True).start()

    def _apply_movements(self, movs):
        self._movs = movs
        self.tree.delete(*self.tree.get_children())

        saldo = 0.0
        self._saldo_acum = []
        for m in self._movs:
            saldo += m["haber"] - m["debe"]
            self._saldo_acum.append(saldo)
            self.tree.insert("", "end", values=(
                m["id"], m["detalle"],
                f"{m['haber']:,.0f}" if m["haber"] else "",
                f"{saldo:,.0f}",
            ))

        self.lbl_total.configure(text=f"${saldo:,.0f}")
        self.lbl_proc.place_forget()
        self.tree.configure(cursor="")

    def _apply_worker_error(self, e):
        self.lbl_proc.place_forget()
        self.tree.configure(cursor="")
        messagebox.showerror("Error", f"Error al procesar el reporte: {e}",
                             parent=self)

    # ── Export ────────────────────────────────────────────────────────────

    def _exportar_excel(self):
        if not self._movs:
            messagebox.showinfo("Exportar", "No hay datos para exportar.",
                                parent=self)
            return
        path = filedialog.asksaveasfilename(
            parent=self, defaultextension=".xlsx",
            filetypes=[("Excel", "*.xlsx")],
            initialfile=f"historial_cobros.xlsx", title="Exportar a Excel")
        if not path:
            return
        try:
            _caja._export_excel(self._saldo_acum, self._movs, path)
            messagebox.showinfo("Exportar", f"Exportado a:\n{path}", parent=self)
        except Exception as e:
            messagebox.showerror("Error", f"Error al exportar: {e}", parent=self)


def open_window(parent=None):
    return HistorialCobrosWindow(parent)


if __name__ == "__main__":
    root = tk.Tk()
    root.withdraw()
    open_window(root)
    root.mainloop()
