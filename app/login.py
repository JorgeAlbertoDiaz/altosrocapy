"""Login window for AltosRoca (pure Tkinter)."""

import os
import sys
import tkinter as tk
import tkinter.font as tkfont
import tkinter.messagebox as messagebox

try:
    from app.db import validate_credentials
    from app.resources import load_logo, apply_app_icon, force_taskbar_button
except ImportError:  # dev / frozen fallback
    from db import validate_credentials
    from resources import load_logo, apply_app_icon, force_taskbar_button

try:
    from app import principal
except ImportError:  # dev / frozen fallback
    import principal

WINDOW_WIDTH = 730
WINDOW_HEIGHT = 330

BG_LEFT = "#E9E9E9"
BG_RIGHT = "#232428"
COLOR_TITLE = "#8D7B63"
COLOR_UNDERLINE = "#707070"
COLOR_ENTRY_TEXT = "#F0F0F0"
COLOR_BUTTON_BG = "#404040"
COLOR_BUTTON_ACTIVE = "#4A4A4A"
COLOR_BUTTON_FG = "#E8D7C2"
COLOR_WINDOW_BUTTONS = "#555555"

TITLE_BAR_HEIGHT = 28


def center_window(window: tk.Tk) -> None:
    window.update_idletasks()
    x = (window.winfo_screenwidth() - WINDOW_WIDTH) // 2
    y = (window.winfo_screenheight() - WINDOW_HEIGHT) // 2
    window.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}+{x}+{y}")


def make_underlined_entry(parent: tk.Widget, width_px: int) -> tk.Frame:
    """Entry with flat relief and a material-style bottom border line."""
    container = tk.Frame(parent, bg=BG_RIGHT)
    entry = tk.Entry(
        container,
        relief="flat",
        bd=0,
        bg=BG_RIGHT,
        fg=COLOR_ENTRY_TEXT,
        insertbackground=COLOR_ENTRY_TEXT,
        font=("Helvetica", 12),
    )
    entry.place(x=0, y=0, width=width_px, height=27)
    underline = tk.Frame(container, bg=COLOR_UNDERLINE)
    underline.place(x=0, y=27, width=width_px, height=1)
    container.configure(width=width_px, height=28)
    container.pack_propagate(False)
    return container


def on_access(window: tk.Tk, username: tk.Entry, password: tk.Entry) -> None:
    user = username.get().strip()
    pwd = password.get().strip()
    if not user or not pwd:
        messagebox.showwarning("AltosRoca", "Usuario y contraseña son obligatorios")
        return
    try:
        ok = validate_credentials(user, pwd)
    except FileNotFoundError as exc:
        messagebox.showerror("AltosRoca", str(exc))
        return
    if ok:
        window.destroy()
        principal.main(user)
    else:
        messagebox.showerror("AltosRoca", "Usuario o contraseña incorrectos")


def make_window_draggable(window: tk.Tk) -> None:
    """Allow moving the borderless window by dragging its top strip."""
    offset = {"x": 0, "y": 0}

    def on_press(event):
        offset["x"] = event.x
        offset["y"] = event.y

    def on_drag(event):
        window.geometry(
            f"+{event.x_root - offset['x']}+{event.y_root - offset['y']}"
        )

    strip = tk.Frame(window, bg=BG_RIGHT, height=TITLE_BAR_HEIGHT)
    strip.place(x=0, y=0, relwidth=1.0, height=TITLE_BAR_HEIGHT)
    strip.bind("<ButtonPress-1>", on_press)
    strip.bind("<B1-Motion>", on_drag)


def add_window_buttons(window: tk.Tk) -> None:
    """Custom minimize/close buttons in the top-right corner."""

    def minimize():
        window.iconify()

    bar = tk.Frame(window, bg=BG_RIGHT)
    bar.place(
        x=WINDOW_WIDTH - 84,
        y=4,
        width=80,
        height=22,
    )

    minimize_btn = tk.Label(
        bar,
        text="\u2013",
        bg=BG_RIGHT,
        fg=COLOR_WINDOW_BUTTONS,
        font=("Helvetica", 13),
        cursor="hand2",
    )
    minimize_btn.place(x=0, y=0, width=38, height=22)
    minimize_btn.bind("<Button-1>", lambda e: minimize())

    close_btn = tk.Label(
        bar,
        text="\u2715",
        bg=BG_RIGHT,
        fg=COLOR_WINDOW_BUTTONS,
        font=("Helvetica", 12),
        cursor="hand2",
    )
    close_btn.place(x=40, y=0, width=38, height=22)
    close_btn.bind("<Button-1>", lambda e: window.destroy())


def build_login(window: tk.Tk) -> None:
    window.title("AltosRoca — Login")
    window.resizable(False, False)
    window.configure(bg=BG_RIGHT)
    # Remove the native title bar; custom buttons are drawn instead.
    window.overrideredirect(True)

    left_width = int(WINDOW_WIDTH * 0.27)

    left_panel = tk.Frame(window, bg=BG_LEFT)
    left_panel.place(x=0, y=0, width=left_width, height=WINDOW_HEIGHT)

    logo = load_logo(max_w=left_width - 30, max_h=WINDOW_HEIGHT - 40)
    if logo is not None:
        logo_label = tk.Label(left_panel, image=logo, bg=BG_LEFT, bd=0)
        logo_label.place(relx=0.5, rely=0.5, anchor="center")
    else:
        # Logo not critical in this version; show name as fallback.
        tk.Label(
            left_panel,
            text="ALTOS ROCA",
            bg=BG_LEFT,
            fg="#555555",
            font=("Helvetica", 14),
        ).place(relx=0.5, rely=0.5, anchor="center")

    right_panel = tk.Frame(window, bg=BG_RIGHT)
    right_panel.place(x=left_width, y=0, width=WINDOW_WIDTH - left_width, height=WINDOW_HEIGHT)
    # Keep a reference so the image is not garbage collected.
    right_panel.logo = logo

    available_fonts = {f.lower() for f in tkfont.families()}
    title_font = "Helvetica Light" if "helvetica light" in available_fonts else "Helvetica"
    title = tk.Label(
        right_panel,
        text="LOGIN",
        bg=BG_RIGHT,
        fg=COLOR_TITLE,
        font=(title_font, 20),
    )
    title.place(relx=0.5, y=30, anchor="n")

    entry_width = 410
    user_container = make_underlined_entry(right_panel, entry_width)
    user_container.place(x=65, y=90)

    pwd_container = make_underlined_entry(right_panel, entry_width)
    pwd_container.place(x=65, y=90 + 28 + 35)
    pwd_entry = pwd_container.winfo_children()[0]
    pwd_entry.configure(show="*")

    button = tk.Button(
        right_panel,
        text="ACCEDER",
        command=lambda: on_access(window, user_container.winfo_children()[0], pwd_entry),
        relief="flat",
        bd=0,
        bg=COLOR_BUTTON_BG,
        activebackground=COLOR_BUTTON_ACTIVE,
        activeforeground=COLOR_BUTTON_FG,
        fg=COLOR_BUTTON_FG,
        font=("Helvetica", 11),
        cursor="hand2",
    )
    button.place(x=65, y=230, width=445, height=40)

    user_entry = user_container.winfo_children()[0]
    submit = lambda _event=None: on_access(window, user_entry, pwd_entry) or "break"
    window.bind("<Return>", submit)
    user_entry.bind("<Return>", submit)
    pwd_entry.bind("<Return>", submit)
    button.configure(command=lambda: on_access(window, user_entry, pwd_entry))
    user_entry.focus_set()

    make_window_draggable(window)
    add_window_buttons(window)
    apply_app_icon(window)
    force_taskbar_button(window)


def main() -> None:
    window = tk.Tk()
    center_window(window)
    build_login(window)
    window.protocol("WM_DELETE_WINDOW", window.destroy)
    window.mainloop()
    # Ensure the process (and the PyInstaller onefile parent) dies cleanly.
    sys.exit(0)


if __name__ == "__main__":
    main()
