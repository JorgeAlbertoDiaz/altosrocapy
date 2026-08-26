"""Consultar Estados Socios: panel administrativo de vencimientos/saldos/planes."""

import datetime
import tkinter as tk
from tkinter import ttk, messagebox

try:
    from app import db
except ImportError:
    import db

# ── Spanish day/month names (no locale dependency) ────────────────────────
_DAYS_ES = {
    0: "lunes", 1: "martes", 2: "miércoles", 3: "jueves",
    4: "viernes", 5: "sábado", 6: "domingo",
}
_MONTHS_ES = {
    1: "enero", 2: "febrero", 3: "marzo", 4: "abril",
    5: "mayo", 6: "junio", 7: "julio", 8: "agosto",
    9: "septiembre", 10: "octubre", 11: "noviembre", 12: "diciembre",
}
_MONTH_NUM = {v: k for k, v in _MONTHS_ES.items()}

WINDOW_WIDTH = 950
WINDOW_HEIGHT = 620

BG = "#E8E8E8"
FG = "#000000"
FG_GREEN = "#008000"
FG_RED = "#FF0000"
FG_ORANGE = "#FF6600"
FG_DARKRED = "#8B0000"
FG_GRAY = "#999999"
SELECTION_BG = "#0078D7"

PAD = 10  # horizontal padding

NAME_MAX_CHARS = 16
DEFAULT_PLAN_DESC = "MUSC APAR"


# ── Helpers ───────────────────────────────────────────────────────────────

def _parse_date(raw):
    if not raw:
        return None
    try:
        return datetime.datetime.strptime(raw[:10], "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def _fmt_ddmmyyyy(raw):
    d = _parse_date(raw)
    return d.strftime("%d/%m/%Y") if d else ""


def _today_es():
    t = datetime.date.today()
    return f"{_DAYS_ES[t.weekday()]}, {t.day} de {_MONTHS_ES[t.month]} de {t.year}"


def _parse_date_es(text):
    """Parse 'miércoles, 26 de agosto de 2026' — no locale."""
    try:
        after = text.split(", ", 1)[1] if ", " in text else text
        parts = after.split()
        return datetime.date(int(parts[4]), _MONTH_NUM[parts[2]], int(parts[0]))
    except (ValueError, KeyError, IndexError):
        return None


def _truncate(apellidos, nombres):
    ap = (apellidos or "").strip()
    no = (nombres or "").strip()
    full = f"{ap}, {no}"
    if len(full) <= NAME_MAX_CHARS:
        return full
    avail = NAME_MAX_CHARS - len(ap) - 2
    return f"{ap}, {no[:avail]}" if avail > 0 else ap[:NAME_MAX_CHARS]


def _latest_payments(conn):
    rows = conn.execute(
        """
        SELECT p.idSocio, p.FechaVencimineto, p.FechadePago, p.Importe, p.Saldo
        FROM tbPagos p
        JOIN (SELECT idSocio, MAX(FechadePago) AS m
              FROM tbPagos WHERE Eliminado IS NULL OR Eliminado != '1'
              GROUP BY idSocio) x
        ON p.idSocio = x.idSocio AND p.FechadePago = x.m
        """
    ).fetchall()
    return {r["idSocio"]: dict(r) for r in rows}


def _plan_map(conn):
    return {r["idPlan"]: r["Descripcion"]
            for r in conn.execute("SELECT idPlan, Descripcion FROM tbPlan")}


def _plan_list(conn):
    return [r["Descripcion"] for r in conn.execute(
        "SELECT Descripcion FROM tbPlan WHERE idPlan != '------' ORDER BY Descripcion")]


def _plan_id(conn, desc):
    r = conn.execute("SELECT idPlan FROM tbPlan WHERE Descripcion=?", (desc,)).fetchone()
    return r["idPlan"] if r else None


def _unpaid_debtors(conn):
    """Set of idSocio with at least one unpaid/not-deleted debt (ONE query)."""
    rows = conn.execute(
        "SELECT DISTINCT idSocio FROM tb_RegistroDeudas "
        "WHERE (Cancelada IS NULL OR Cancelada!='1') "
        "AND (Eliminado IS NULL OR Eliminado!='1')"
    ).fetchall()
    return {r["idSocio"] for r in rows}


# ── Core query ────────────────────────────────────────────────────────────

def populate_grid(tree, status_label, filter_mode, plan_desc=None, date=None):
    tree.delete(*tree.get_children())
    conn = db.get_connection()
    try:
        hoy = datetime.date.today()

        sql = """
            SELECT s.idSocio, s.Apellidos, s.Nombres, s.Documento,
                   s.NroInscripcion, s.Estado, s.id_Plan, s.FechaBaja
            FROM tbSocios s
            WHERE s.Documento != '---------' AND (
                s.Documento LIKE '%0%' OR s.Documento LIKE '%1%'
                OR s.Documento LIKE '%2%' OR s.Documento LIKE '%3%'
                OR s.Documento LIKE '%4%' OR s.Documento LIKE '%5%'
                OR s.Documento LIKE '%6%' OR s.Documento LIKE '%7%'
                OR s.Documento LIKE '%8%' OR s.Documento LIKE '%9%')
        """
        params = []

        if filter_mode in ("ACTIVOS_POR_PLAN", "INACTIVOS_POR_PLAN") and plan_desc:
            pid = _plan_id(conn, plan_desc)
            if pid:
                sql += " AND s.id_Plan=?"
                params.append(pid)

        socios = conn.execute(sql, params).fetchall()
        pagos = _latest_payments(conn)
        planes = _plan_map(conn)
        deudores = _unpaid_debtors(conn)
        count = 0

        for s in socios:
            sid = s["idSocio"]
            pago = pagos.get(sid)
            if pago is None:
                continue

            # Business rules:
            #   cuota vigente  -> latest FechaVencimineto >= today
            #   ACTIVOS        -> cuota vigente y sin deudas
            #   ACTIVOS C/SALDO-> cuota vigente y con deudas
            #   INACTIVOS      -> cuota vencida (sin importar deudas)
            vd = _parse_date(pago.get("FechaVencimineto"))
            vigente = vd is not None and vd >= hoy
            tiene_deuda = sid in deudores
            activo = vigente and not tiene_deuda
            con_saldo = vigente and tiene_deuda

            # Filter
            if filter_mode in ("ACTIVOS", "ACTIVOS_POR_PLAN") and not activo:
                continue
            if filter_mode == "ACTIVOS_C_SALDO" and not con_saldo:
                continue
            if filter_mode in ("INACTIVOS", "INACTIVOS_POR_PLAN") and vigente:
                continue
            if filter_mode == "POR_DIA" and date:
                pd = _parse_date(pago.get("FechadePago"))
                if pd != _parse_date(date):
                    continue

            nombre = _truncate(s["Apellidos"], s["Nombres"])
            venc = _fmt_ddmmyyyy(pago.get("FechaVencimineto"))
            fpago = _fmt_ddmmyyyy(pago.get("FechadePago"))
            imp = str(pago.get("Importe") or "0")
            sal = str(pago.get("Saldo") or "0")
            plan = planes.get(s["id_Plan"], "")
            icon = "\u2705" if (activo or con_saldo) else ""
            tag = "orange" if con_saldo else ("green" if activo else "")

            tree.insert("", "end", values=(
                sid, nombre, s["Documento"], s["NroInscripcion"],
                venc, fpago, imp, sal, plan, icon,
            ), tags=(tag,) if tag else ())
            count += 1

        status_label.configure(text=f"Socios: {count}")
        return count
    finally:
        conn.close()


# ── Window ────────────────────────────────────────────────────────────────

class ConsultarEstadosSociosWindow(tk.Toplevel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.title("Consultar Estados de Socios")
        self.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        self.minsize(950, 620)
        self.configure(bg=BG)
        self.bind("<Escape>", lambda _: self.destroy())

        self.filter_var = tk.StringVar(value="ACTIVOS")
        self.plan_var = tk.StringVar(value=DEFAULT_PLAN_DESC)
        self.search_var = tk.StringVar()

        self._build()
        self._sync_states()
        self._refresh()

    # ── Build ─────────────────────────────────────────────────────────────

    def _build(self):
        # === SEARCH BAR (fixed height) ===
        frm_search = tk.Frame(self, bg=BG, height=36)
        frm_search.pack(fill="x", padx=PAD, pady=(8, 4))
        frm_search.pack_propagate(False)

        self.entry_search = tk.Entry(
            frm_search, textvariable=self.search_var,
            bg="#FFF", fg=FG, font=("Helvetica", 10),
            relief="solid", bd=1,
            highlightthickness=1, highlightbackground="#999",
        )
        self.entry_search.pack(fill="both", expand=True, ipady=3)
        self.entry_search.bind("<Return>", lambda _: self._refresh())

        # === FILTERS (fixed height) ===
        frm_filters = tk.LabelFrame(
            self, text=" Filtros ", bg=BG,
            font=("Helvetica", 9, "bold"), relief="groove", bd=1,
            labelanchor="nw", height=82,
        )
        frm_filters.pack(fill="x", padx=PAD, pady=(0, 4))
        frm_filters.pack_propagate(False)

        # Row 0: main radios + date
        self.r_act = tk.Radiobutton(
            frm_filters, text="ACTIVOS", variable=self.filter_var,
            value="ACTIVOS", bg=BG, fg=FG_GREEN,
            font=("Helvetica", 9, "bold"), selectcolor=BG,
            activebackground=BG, activeforeground=FG_GREEN,
            command=self._on_filter)
        self.r_act.place(x=10, y=4)

        self.r_inact = tk.Radiobutton(
            frm_filters, text="INACTIVOS", variable=self.filter_var,
            value="INACTIVOS", bg=BG, fg=FG_RED,
            font=("Helvetica", 9, "bold"), selectcolor=BG,
            activebackground=BG, activeforeground=FG_RED,
            command=self._on_filter)
        self.r_inact.place(x=130, y=4)

        self.r_csaldo = tk.Radiobutton(
            frm_filters, text="ACTIVOS C/SALDO", variable=self.filter_var,
            value="ACTIVOS_C_SALDO", bg=BG, fg=FG_ORANGE,
            font=("Helvetica", 9, "bold"), selectcolor=BG,
            activebackground=BG, activeforeground=FG_ORANGE,
            command=self._on_filter)
        self.r_csaldo.place(x=290, y=4)

        self.r_pordia = tk.Radiobutton(
            frm_filters, text="POR DÍA", variable=self.filter_var,
            value="POR_DIA", bg=BG, fg=FG,
            font=("Helvetica", 9, "bold"), selectcolor=BG,
            activebackground=BG, command=self._on_filter)
        self.r_pordia.place(x=470, y=4)

        self.entry_date = tk.Entry(
            frm_filters, bg="#FFF", fg=FG, font=("Helvetica", 9),
            relief="solid", bd=1, state="disabled")
        self.entry_date.place(x=560, y=4, width=310, height=22)
        # Pre-fill while normal, then disable
        self.entry_date.configure(state="normal")
        self.entry_date.delete(0, "end")
        self.entry_date.insert(0, _today_es())
        self.entry_date.configure(state="disabled", fg=FG_GRAY)

        # Row 1: plan radios + combo
        self.r_aplan = tk.Radiobutton(
            frm_filters, text="ACTIVOS POR PLAN", variable=self.filter_var,
            value="ACTIVOS_POR_PLAN", bg=BG, fg=FG_GREEN,
            font=("Helvetica", 9, "bold"), selectcolor=BG,
            activebackground=BG, activeforeground=FG_GREEN,
            command=self._on_filter)
        self.r_aplan.place(x=10, y=40)

        self.combo_plan = ttk.Combobox(
            frm_filters, textvariable=self.plan_var,
            width=18, state="disabled")
        self.combo_plan.place(x=195, y=42)
        self.combo_plan.bind("<<ComboboxSelected>>", lambda _: self._on_filter())

        self.r_iplan = tk.Radiobutton(
            frm_filters, text="INACTIVOS POR PLAN", variable=self.filter_var,
            value="INACTIVOS_POR_PLAN", bg=BG, fg=FG_RED,
            font=("Helvetica", 9, "bold"), selectcolor=BG,
            activebackground=BG, activeforeground=FG_RED,
            command=self._on_filter)
        self.r_iplan.place(x=400, y=40)

        self._load_plans()

        # === TREEVIEW (EXPANDS) ===
        frm_tree = tk.Frame(self, bg=BG)
        frm_tree.pack(fill="both", expand=True, padx=PAD, pady=(0, 0))

        cols = ("idSocio", "Nombre Completo", "Documento", "Nro",
                "Vencimiento", "FechaPago", "Importe", "Saldo", "Plan", "Estado")
        widths = [50, 180, 100, 50, 90, 90, 70, 60, 130, 50]

        style = ttk.Style(self)
        style.configure("G.Treeview", background="#FFF", foreground=FG,
                        rowheight=22, fieldbackground="#FFF",
                        font=("Helvetica", 9, "bold"))
        style.configure("G.Treeview.Heading", background=BG,
                        font=("Helvetica", 8, "bold"))
        style.map("G.Treeview",
                  background=[("selected", SELECTION_BG)],
                  foreground=[("selected", "#FFF")])

        self.tree = ttk.Treeview(
            frm_tree, columns=cols, show="headings",
            style="G.Treeview", selectmode="browse")

        for c, w in zip(cols, widths):
            # NOTE: ttk headings do not accept a "font" option; the heading
            # font comes from the "G.Treeview.Heading" style above.
            self.tree.heading(c, text=c)
            a = "center" if c in ("idSocio", "Nro", "Importe", "Saldo", "Estado") else "w"
            self.tree.column(c, width=w, minwidth=30, anchor=a)

        self.tree.tag_configure("green", foreground=FG_GREEN)
        self.tree.tag_configure("orange", foreground=FG_ORANGE)

        vsb = ttk.Scrollbar(frm_tree, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(frm_tree, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        frm_tree.grid_rowconfigure(0, weight=1)
        frm_tree.grid_columnconfigure(0, weight=1)

        # === BOTTOM BAR (fixed height) ===
        bar = tk.Frame(self, bg=BG, height=40)
        bar.pack(fill="x", padx=PAD, pady=(0, 5))
        bar.pack_propagate(False)

        tk.Button(bar, text="Exportar a Excel", width=14,
                  command=lambda: messagebox.showinfo("Exportar", "Próximamente")
                  ).place(x=10, y=6)
        tk.Button(bar, text="Exportar a PDF", width=14,
                  command=lambda: messagebox.showinfo("Exportar", "Próximamente")
                  ).place(x=160, y=6)

        self.lbl_count = tk.Label(bar, text="Socios: 0", bg=BG,
                                  font=("Helvetica", 10, "bold"), fg=FG)
        self.lbl_count.place(x=650, y=8)

        tk.Button(bar, text="Salir", width=10,
                  command=self.destroy).place(x=860, y=6)

    def _load_plans(self):
        conn = db.get_connection()
        try:
            plans = _plan_list(conn)
        finally:
            conn.close()
        self.combo_plan["values"] = plans
        if DEFAULT_PLAN_DESC in plans:
            self.plan_var.set(DEFAULT_PLAN_DESC)
        elif plans:
            self.plan_var.set(plans[0])

    # ── Filter state + refresh ────────────────────────────────────────────

    def _on_filter(self):
        self._sync_states()
        self._refresh()

    def _sync_states(self):
        mode = self.filter_var.get()
        plan_active = mode in ("ACTIVOS_POR_PLAN", "INACTIVOS_POR_PLAN")
        date_active = mode == "POR_DIA"

        self.combo_plan.configure(state="readonly" if plan_active else "disabled")

        if date_active:
            self.entry_date.configure(state="normal", fg=FG)
        else:
            self.entry_date.configure(state="disabled", fg=FG_GRAY)

    def _refresh(self):
        mode = self.filter_var.get()
        plan = self.plan_var.get() if mode in ("ACTIVOS_POR_PLAN", "INACTIVOS_POR_PLAN") else None
        date = None
        if mode == "POR_DIA":
            parsed = _parse_date_es(self.entry_date.get())
            if parsed:
                date = parsed.strftime("%Y-%m-%d")

        search = self.search_var.get().strip()

        count = populate_grid(self.tree, self.lbl_count, mode, plan_desc=plan, date=date)

        # Apply search filter (DNI or name) on top of the SQL filter
        if search:
            visible = []
            for item in self.tree.get_children():
                vals = self.tree.item(item, "values")
                # vals: id, nombre, documento, nro, venc, fpago, imp, sal, plan, estado
                if (search in str(vals[1]).lower() or   # nombre
                    search in str(vals[2]) or            # documento (DNI)
                    search in str(vals[0])):             # idSocio
                    visible.append(item)
            hidden = set(self.tree.get_children()) - set(visible)
            for item in hidden:
                self.tree.delete(item)
            self.lbl_count.configure(text=f"Socios: {len(visible)}")


def open_window(parent=None):
    return ConsultarEstadosSociosWindow(parent)


if __name__ == "__main__":
    root = tk.Tk()
    root.withdraw()
    open_window(root)
    root.mainloop()
