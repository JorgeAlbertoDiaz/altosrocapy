"""Login window for AltosRoca (pure Tkinter)."""

import os
import sys
import tkinter as tk
import tkinter.font as tkfont

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

LOGO_PATH = os.path.join(os.path.dirname(__file__), "..", "temps", "logo.png")


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


def on_access(username: tk.Entry, password: tk.Entry) -> None:
    user = username.get().strip()
    pwd = password.get().strip()
    if not user or not pwd:
        print("Usuario y contraseña son obligatorios")
        return
    print(f"Login intentado con usuario: {user}")
    # Stub: authentication flow goes here.


def build_login(window: tk.Tk) -> None:
    window.title("AltosRoca — Login")
    window.resizable(False, False)
    window.configure(bg=BG_RIGHT)
    window.overrideredirect(False)

    left_width = int(WINDOW_WIDTH * 0.27)

    left_panel = tk.Frame(window, bg=BG_LEFT)
    left_panel.place(x=0, y=0, width=left_width, height=WINDOW_HEIGHT)

    logo = None
    if os.path.isfile(LOGO_PATH):
        try:
            logo = tk.PhotoImage(file=LOGO_PATH)
            logo_label = tk.Label(left_panel, image=logo, bg=BG_LEFT, bd=0)
            logo_label.place(relx=0.5, rely=0.5, anchor="center")
        except tk.TclError:
            logo = None
    if logo is None:
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
        command=lambda: on_access(user_container.winfo_children()[0], pwd_entry),
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


def main() -> None:
    window = tk.Tk()
    center_window(window)
    build_login(window)
    window.mainloop()


if __name__ == "__main__":
    main()
