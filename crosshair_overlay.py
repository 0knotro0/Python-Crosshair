#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Crosshair Overlay - originale
Overlay trasparente e sempre in primo piano per il mirino (crosshair) nei giochi.

Requisiti:
  - Python 3 (tkinter incluso di solito)
  - Click-through nativo: solo Windows (usa ctypes)

Avvio:
  python crosshair_overlay.py

Controlli:
  - Pannello "Controllo": attiva/nascondi overlay, tipo, colore, dimensione,
    spessore, gap centrale, opacità e click-through.
  - Tasto ESC sulla finestra dell'overlay per nasconderla.
  - I profili vengono salvati in %USERPROFILE%\crosshair_overlay_profiles.json
"""

import tkinter as tk
from tkinter import ttk, colorchooser, messagebox
import json
import os
import sys

# Colore usato per lo sfondo trasparente. Nero puro e' il piu' compatibile
# con la trasparenza finestra su Windows.
TRANSPARENT_BG = "#000000"
CONFIG_FILE = os.path.join(os.path.expanduser("~"), "crosshair_overlay_profiles.json")

CROSSHAIR_TYPES = [
    ("Punto", "dot"),
    ("Croce", "cross"),
    ("Cerchio", "circle"),
    ("Croce + Cerchio", "cross_circle"),
    ("T (mirino)", "t_shape"),
    ("Croce con gap centrale", "cross_gap"),
]

HAS_WIN32 = sys.platform == "win32"


def tk_color_to_colorref(hex_color):
    """Converte un colore tkinter #RRGGBB nel formato Windows COLORREF 0x00BBGGRR."""
    hex_color = hex_color.lstrip("#")
    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)
    return (b << 16) | (g << 8) | r


def get_hwnd(window):
    """Recupera l'HWND della finestra tkinter in modo robusto."""
    try:
        wid = window.winfo_id()
        if isinstance(wid, str):
            wid = wid.strip()
            if wid.lower().startswith("0x"):
                return int(wid, 16)
            return int(wid)
        return int(wid)
    except Exception:
        return None


class CrosshairOverlay:
    def __init__(self, root):
        self.root = root
        self.root.title("Crosshair Overlay - Controllo")
        self.root.geometry("370x660")
        self.root.resizable(False, False)

        # Stato
        self.enabled = tk.BooleanVar(value=True)
        self.click_through = tk.BooleanVar(value=True)
        self.ctype = tk.StringVar(value="cross")
        self.color = tk.StringVar(value="#00FF00")
        self.size = tk.IntVar(value=40)
        self.thickness = tk.IntVar(value=3)
        self.opacity = tk.DoubleVar(value=100)
        self.gap = tk.IntVar(value=6)

        # Label per mostrare valori interi puliti degli slider
        self.lbl_size = None
        self.lbl_thickness = None
        self.lbl_gap = None
        self.lbl_opacity = None

        self.overlay = None
        self.canvas = None
        self.hwnd = None

        self.build_ui()
        self.load_last_profile()
        self.apply_settings()

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    # ------------------------------------------------------------------ UI
    def build_ui(self):
        pad = {"padx": 12, "pady": 6}
        frame = ttk.Frame(self.root)
        frame.pack(fill="both", expand=True)

        ttk.Label(frame, text="Crosshair Overlay", font=("Segoe UI", 15, "bold")).pack(**pad)
        ttk.Label(
            frame,
            text="Overlay originale - trasparente, sempre in primo piano",
            font=("Segoe UI", 9),
        ).pack(**pad)

        ttk.Separator(frame, orient="horizontal").pack(fill="x", pady=8)

        ttk.Checkbutton(
            frame, text="Attiva overlay", variable=self.enabled, command=self.toggle_overlay
        ).pack(anchor="w", **pad)
        ttk.Checkbutton(
            frame,
            text="Click-through (i click passano al gioco)",
            variable=self.click_through,
            command=self.apply_settings,
        ).pack(anchor="w", **pad)

        ttk.Separator(frame, orient="horizontal").pack(fill="x", pady=8)

        ttk.Label(frame, text="Tipo di mirino:").pack(anchor="w", **pad)
        values = [v[1] for v in CROSSHAIR_TYPES]
        self.type_menu = ttk.OptionMenu(
            frame, self.ctype, self.ctype.get(), *values, command=lambda _: self.apply_settings()
        )
        self.type_menu.pack(fill="x", **pad)

        col_frame = ttk.Frame(frame)
        col_frame.pack(fill="x", **pad)
        ttk.Label(col_frame, text="Colore:").pack(side="left")
        self.color_btn = tk.Button(col_frame, bg=self.color.get(), width=6, command=self.pick_color)
        self.color_btn.pack(side="left", padx=6)
        ttk.Entry(col_frame, textvariable=self.color, width=10).pack(side="left")

        self._add_slider(frame, "Dimensione (px):", self.size, 8, 240, "lbl_size")
        self._add_slider(frame, "Spessore linee (px):", self.thickness, 1, 12, "lbl_thickness")
        self._add_slider(frame, "Gap centro (px):", self.gap, 0, 60, "lbl_gap")
        self._add_slider(frame, "Opacità (%):", self.opacity, 0, 100, "lbl_opacity")

        ttk.Separator(frame, orient="horizontal").pack(fill="x", pady=12)

        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill="x", **pad)
        ttk.Button(btn_frame, text="Centra overlay", command=self.center_overlay).pack(
            side="left", expand=True, fill="x", padx=3
        )
        ttk.Button(btn_frame, text="Scegli colore", command=self.pick_color).pack(
            side="left", expand=True, fill="x", padx=3
        )
        ttk.Button(btn_frame, text="Salva profilo", command=self.save_profile).pack(
            side="left", expand=True, fill="x", padx=3
        )

        btn_frame2 = ttk.Frame(frame)
        btn_frame2.pack(fill="x", **pad)
        ttk.Button(btn_frame2, text="Esci", command=self.on_close).pack(fill="x")

        self.status_var = tk.StringVar(value="Pronto")
        ttk.Label(frame, textvariable=self.status_var, foreground="gray").pack(**pad)

    def _add_slider(self, parent, label_text, var, frm, to, lbl_attr):
        ttk.Label(parent, text=label_text).pack(anchor="w", **{"padx": 12, "pady": (8, 0)})
        slider = ttk.Scale(
            parent, from_=frm, to=to, variable=var, orient="horizontal",
            command=lambda v: self._on_slider_changed(v, lbl_attr),
        )
        slider.pack(fill="x", padx=12)
        lbl = ttk.Label(parent, text=str(int(var.get())))
        lbl.pack(anchor="e", padx=12, pady=(0, 4))
        setattr(self, lbl_attr, lbl)

    def _on_slider_changed(self, value, lbl_attr):
        try:
            val = int(float(value))
            lbl = getattr(self, lbl_attr, None)
            if lbl is not None:
                lbl.config(text=str(val))
        except Exception:
            pass
        self.apply_settings()

    # --------------------------------------------------------------- overlay
    def get_overlay(self):
        if self.overlay is None or not self.overlay.winfo_exists():
            self.create_overlay()
        return self.overlay

    def create_overlay(self):
        self.overlay = tk.Toplevel(self.root)
        self.overlay.overrideredirect(True)          # niente bordi / barra titolo
        self.overlay.attributes("-topmost", True)    # sempre in primo piano
        self.overlay.attributes("-transparentcolor", TRANSPARENT_BG)
        self.overlay.config(bg=TRANSPARENT_BG)
        self.overlay.geometry("320x320+200+200")

        self.canvas = tk.Canvas(
            self.overlay, width=320, height=320, bg=TRANSPARENT_BG, highlightthickness=0
        )
        self.canvas.pack()

        # Forza la creazione della finestra nativa prima di leggere hwnd
        try:
            self.overlay.update_idletasks()
            self.overlay.update()
        except Exception:
            pass

        if HAS_WIN32:
            self.hwnd = get_hwnd(self.overlay)

        self.overlay.bind("<Escape>", lambda e: self.hide_overlay())

        # Mostra l'overlay subito se "Attiva overlay" è spuntato
        if self.enabled.get():
            self.overlay.deiconify()
            self.overlay.lift()
        else:
            self.overlay.withdraw()

        self.apply_settings()

    def toggle_overlay(self):
        try:
            if self.enabled.get():
                ov = self.get_overlay()
                ov.deiconify()
                ov.lift()
                self.apply_settings()
                self.status_var.set("Overlay attivo")
            else:
                self.hide_overlay()
                self.status_var.set("Overlay nascosto")
        except Exception as e:
            self.status_var.set(f"Errore attivazione overlay: {e}")

    def hide_overlay(self):
        if self.overlay and self.overlay.winfo_exists():
            try:
                self.overlay.withdraw()
            except Exception:
                pass

    def apply_settings(self):
        try:
            if not self.overlay or not self.overlay.winfo_exists():
                return
            try:
                self.overlay.attributes("-alpha", max(0.05, self.opacity.get() / 100.0))
            except Exception:
                pass
            self.draw_crosshair()
            self.apply_click_through()
        except Exception as e:
            self.status_var.set(f"Errore impostazioni: {e}")

    def apply_click_through(self):
        if not HAS_WIN32 or not self.hwnd:
            return
        try:
            import ctypes
            user32 = ctypes.windll.user32
            GWL_EXSTYLE = -20
            WS_EX_LAYERED = 0x00080000
            WS_EX_TRANSPARENT = 0x00000020
            LWA_COLORKEY = 0x00000001

            styles = user32.GetWindowLongW(self.hwnd, GWL_EXSTYLE)
            if self.click_through.get():
                styles |= WS_EX_LAYERED | WS_EX_TRANSPARENT
            else:
                styles &= ~WS_EX_TRANSPARENT
                styles |= WS_EX_LAYERED

            user32.SetWindowLongW(self.hwnd, GWL_EXSTYLE, styles)

            # Colorkey: rende trasparente il colore di sfondo (nero puro)
            # Convertito correttamente in formato Windows COLORREF (BGR)
            colorkey = tk_color_to_colorref(TRANSPARENT_BG)
            user32.SetLayeredWindowAttributes(
                self.hwnd, colorkey, 0, LWA_COLORKEY
            )
        except Exception as e:
            print("click-through non disponibile:", e)

    def draw_crosshair(self):
        if not self.overlay or not self.overlay.winfo_exists() or not self.canvas:
            return
        try:
            self.canvas.delete("all")
        except Exception:
            return

        try:
            w = self.canvas.winfo_width() or 320
            h = self.canvas.winfo_height() or 320
        except Exception:
            w, h = 320, 320
        cx, cy = w // 2, h // 2

        try:
            size = max(4, int(self.size.get()))
            thick = max(1, int(self.thickness.get()))
            gap = max(0, int(self.gap.get()))
        except Exception:
            size, thick, gap = 40, 3, 6
        col = self.color.get() or "#00FF00"
        t = self.ctype.get() or "cross"

        inner = max(gap // 2, 1) if gap else 1
        outer = size // 2

        try:
            if t == "dot":
                r = max(2, outer)
                self.canvas.create_oval(cx - r, cy - r, cx + r, cy + r, fill=col, outline="")

            elif t == "cross":
                self.canvas.create_line(cx, cy + inner, cx, cy + outer, fill=col,
                                        width=thick, capstyle=tk.ROUND)
                self.canvas.create_line(cx, cy - inner, cx, cy - outer, fill=col,
                                        width=thick, capstyle=tk.ROUND)
                self.canvas.create_line(cx + inner, cy, cx + outer, cy, fill=col,
                                        width=thick, capstyle=tk.ROUND)
                self.canvas.create_line(cx - inner, cy, cx - outer, cy, fill=col,
                                        width=thick, capstyle=tk.ROUND)

            elif t == "circle":
                r = max(2, outer)
                self.canvas.create_oval(cx - r, cy - r, cx + r, cy + r,
                                        outline=col, width=thick)

            elif t == "cross_circle":
                r = max(2, outer)
                self.canvas.create_oval(cx - r, cy - r, cx + r, cy + r,
                                        outline=col, width=thick)
                self.canvas.create_line(cx, cy + inner, cx, cy + outer, fill=col,
                                        width=thick, capstyle=tk.ROUND)
                self.canvas.create_line(cx, cy - inner, cx, cy - outer, fill=col,
                                        width=thick, capstyle=tk.ROUND)
                self.canvas.create_line(cx + inner, cy, cx + outer, cy, fill=col,
                                        width=thick, capstyle=tk.ROUND)
                self.canvas.create_line(cx - inner, cy, cx - outer, cy, fill=col,
                                        width=thick, capstyle=tk.ROUND)

            elif t == "t_shape":
                self.canvas.create_line(cx, cy + inner, cx, cy + outer, fill=col,
                                        width=thick, capstyle=tk.ROUND)
                self.canvas.create_line(cx - outer, cy + outer, cx + outer, cy + outer,
                                        fill=col, width=thick, capstyle=tk.ROUND)

            elif t == "cross_gap":
                g = gap + 2
                self.canvas.create_line(cx, cy + g, cx, cy + outer, fill=col,
                                        width=thick, capstyle=tk.ROUND)
                self.canvas.create_line(cx, cy - g, cx, cy - outer, fill=col,
                                        width=thick, capstyle=tk.ROUND)
                self.canvas.create_line(cx + g, cy, cx + outer, cy, fill=col,
                                        width=thick, capstyle=tk.ROUND)
                self.canvas.create_line(cx - g, cy, cx - outer, cy, fill=col,
                                        width=thick, capstyle=tk.ROUND)
        except Exception as e:
            self.status_var.set(f"Errore disegno: {e}")

    def center_overlay(self):
        if not self.overlay or not self.overlay.winfo_exists():
            return
        try:
            self.overlay.update_idletasks()
            sw = self.overlay.winfo_screenwidth()
            sh = self.overlay.winfo_screenheight()
            w = self.overlay.winfo_width()
            h = self.overlay.winfo_height()
            x = max(0, (sw - w) // 2)
            y = max(0, (sh - h) // 2)
            self.overlay.geometry(f"{w}x{h}+{x}+{y}")
        except Exception as e:
            self.status_var.set(f"Errore centratura: {e}")

    # --------------------------------------------------------------- colore
    def pick_color(self):
        try:
            colore = colorchooser.askcolor(color=self.color.get(), title="Scegli colore del mirino")
            if colore and colore[1]:
                self.color.set(colore[1])
                self.color_btn.config(bg=colore[1])
                self.apply_settings()
        except Exception as e:
            self.status_var.set(f"Errore selezione colore: {e}")

    # ------------------------------------------------------------- profili
    def save_profile(self):
        prof = {
            "ctype": self.ctype.get(),
            "color": self.color.get(),
            "size": self.size.get(),
            "thickness": self.thickness.get(),
            "opacity": self.opacity.get(),
            "gap": self.gap.get(),
            "click_through": self.click_through.get(),
        }
        try:
            data = {}
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
            data["last"] = prof
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            self.status_var.set("Profilo salvato.")
        except Exception as exc:
            messagebox.showerror("Errore salvataggio", str(exc))

    def load_last_profile(self):
        if not os.path.exists(CONFIG_FILE):
            return
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            prof = data.get("last")
            if not prof:
                return
            self.ctype.set(prof.get("ctype", "cross"))
            self.color.set(prof.get("color", "#00FF00"))
            self.color_btn.config(bg=prof.get("color", "#00FF00"))
            self.size.set(int(prof.get("size", 40)))
            self.thickness.set(int(prof.get("thickness", 3)))
            self.opacity.set(float(prof.get("opacity", 100)))
            self.gap.set(int(prof.get("gap", 6)))
            self.click_through.set(bool(prof.get("click_through", True)))
        except Exception:
            pass

    def on_close(self):
        self.hide_overlay()
        self.root.destroy()


def main():
    root = tk.Tk()
    CrosshairOverlay(root)
    root.mainloop()


if __name__ == "__main__":
    main()
