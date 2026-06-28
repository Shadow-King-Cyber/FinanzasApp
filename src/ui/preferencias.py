import json
import os
import sys
import tkinter as tk
import tkinter.font as tkfont
from tkinter import ttk

if getattr(sys, "frozen", False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    )

PREFS_PATH = os.path.join(BASE_DIR, "finanzas_prefs.json")

PREFS_DEFAULT = {
    "font_family": "Segoe UI",
    "font_size": 10,
    "theme": "Clásico",
}

TEMAS = {
    "Clásico": {
        "bg": "#f5f5f5",
        "fg": "#1a1a1a",
        "selectbg": "#0078d7",
        "selectfg": "#ffffff",
        "entrybg": "#ffffff",
        "entryfg": "#1a1a1a",
        "treebg": "#ffffff",
        "treefg": "#1a1a1a",
        "headingbg": "#e0e0e0",
        "headingfg": "#1a1a1a",
        "frame_bg": "#f5f5f5",
        "accent": "#0078d7",
        "buttonbg": "#e1e1e1",
        "buttonfg": "#1a1a1a",
        "tab_bg": "#e8e8e8",
        "tab_fg": "#1a1a1a",
        "tab_sel_bg": "#ffffff",
        "notebook_bg": "#f5f5f5",
    },
    "Oscuro": {
        "bg": "#1e1e1e",
        "fg": "#e0e0e0",
        "selectbg": "#264f78",
        "selectfg": "#ffffff",
        "entrybg": "#3c3c3c",
        "entryfg": "#e0e0e0",
        "treebg": "#252526",
        "treefg": "#e0e0e0",
        "headingbg": "#333333",
        "headingfg": "#cccccc",
        "frame_bg": "#1e1e1e",
        "accent": "#0098ff",
        "buttonbg": "#3c3c3c",
        "buttonfg": "#e0e0e0",
        "tab_bg": "#2d2d2d",
        "tab_fg": "#999999",
        "tab_sel_bg": "#1e1e1e",
        "notebook_bg": "#252526",
    },
    "Azul": {
        "bg": "#e8f0fe",
        "fg": "#1a1a2e",
        "selectbg": "#1a73e8",
        "selectfg": "#ffffff",
        "entrybg": "#ffffff",
        "entryfg": "#1a1a2e",
        "treebg": "#ffffff",
        "treefg": "#1a1a2e",
        "headingbg": "#d2e3fc",
        "headingfg": "#1a1a2e",
        "frame_bg": "#e8f0fe",
        "accent": "#1a73e8",
        "buttonbg": "#d2e3fc",
        "buttonfg": "#1a1a2e",
        "tab_bg": "#c4d7f5",
        "tab_fg": "#1a1a2e",
        "tab_sel_bg": "#ffffff",
        "notebook_bg": "#e8f0fe",
    },
    "Verde": {
        "bg": "#e8f5e9",
        "fg": "#1b3a1b",
        "selectbg": "#2e7d32",
        "selectfg": "#ffffff",
        "entrybg": "#ffffff",
        "entryfg": "#1b3a1b",
        "treebg": "#ffffff",
        "treefg": "#1b3a1b",
        "headingbg": "#c8e6c9",
        "headingfg": "#1b3a1b",
        "frame_bg": "#e8f5e9",
        "accent": "#2e7d32",
        "buttonbg": "#c8e6c9",
        "buttonfg": "#1b3a1b",
        "tab_bg": "#b8d9ba",
        "tab_fg": "#1b3a1b",
        "tab_sel_bg": "#ffffff",
        "notebook_bg": "#e8f5e9",
    },
    "Lavanda": {
        "bg": "#f3e8ff",
        "fg": "#2d1b4e",
        "selectbg": "#7c4dff",
        "selectfg": "#ffffff",
        "entrybg": "#ffffff",
        "entryfg": "#2d1b4e",
        "treebg": "#ffffff",
        "treefg": "#2d1b4e",
        "headingbg": "#e1d5f7",
        "headingfg": "#2d1b4e",
        "frame_bg": "#f3e8ff",
        "accent": "#7c4dff",
        "buttonbg": "#e1d5f7",
        "buttonfg": "#2d1b4e",
        "tab_bg": "#d4c4ea",
        "tab_fg": "#2d1b4e",
        "tab_sel_bg": "#ffffff",
        "notebook_bg": "#f3e8ff",
    },
}

FUENTES_COMUNES = [
    "Segoe UI", "Arial", "Helvetica", "Tahoma", "Verdana",
    "Calibri", "Cambria", "Georgia", "Times New Roman",
    "Consolas", "Courier New",
]


def _cargar_prefs() -> dict:
    try:
        with open(PREFS_PATH, "r", encoding="utf-8") as f:
            prefs = json.load(f)
        for k, v in PREFS_DEFAULT.items():
            prefs.setdefault(k, v)
        if prefs["theme"] not in TEMAS:
            prefs["theme"] = PREFS_DEFAULT["theme"]
        return prefs
    except (FileNotFoundError, json.JSONDecodeError):
        return dict(PREFS_DEFAULT)


def _guardar_prefs(prefs: dict) -> None:
    with open(PREFS_PATH, "w", encoding="utf-8") as f:
        json.dump(prefs, f, indent=2)


class GestorEstilos:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.style = ttk.Style()
        self.prefs = _cargar_prefs()
        self.fuente_actual: tkfont.Font | None = None
        self._observers: list = []
        self.aplicar()

    def suscribir(self, callback) -> None:
        self._observers.append(callback)

    def _notificar(self) -> None:
        for cb in self._observers:
            cb()

    def obtener_familia(self) -> str:
        return self.prefs["font_family"]

    def obtener_tamano(self) -> int:
        return self.prefs["font_size"]

    def obtener_tema(self) -> str:
        return self.prefs["theme"]

    def obtener_colores(self) -> dict:
        return TEMAS.get(self.prefs["theme"], TEMAS["Clásico"])

    def aplicar(self) -> None:
        colores = self.obtener_colores()
        family = self.prefs["font_family"]
        size = self.prefs["font_size"]

        self.fuente_actual = tkfont.Font(family=family, size=size)
        self.root.configure(bg=colores["frame_bg"])

        self.style.theme_use("vista")
        self.style.configure(".", font=(family, size))

        self.style.configure("TLabel", background=colores["frame_bg"], foreground=colores["fg"])
        self.style.configure("Heading.TLabel", font=(family, size + 4, "bold"))
        self.style.configure("Title.TLabel", font=(family, size + 8, "bold"))
        self.style.configure("TButton",
            background=colores["buttonbg"],
            foreground=colores["buttonfg"])
        self.style.map("TButton",
            background=[("active", colores["accent"]), ("pressed", colores["accent"])],
            foreground=[("active", "#ffffff"), ("pressed", "#ffffff")])
        self.style.configure("TEntry",
            fieldbackground=colores["entrybg"],
            foreground=colores["entryfg"])
        self.style.configure("TCombobox",
            fieldbackground=colores["entrybg"],
            foreground=colores["entryfg"])
        self.style.configure("TNotebook",
            background=colores["notebook_bg"],
            borderwidth=0)
        self.style.configure("TNotebook.Tab",
            background=colores["tab_bg"],
            foreground=colores["tab_fg"],
            padding=[10, 4])
        self.style.map("TNotebook.Tab",
            background=[("selected", colores["tab_sel_bg"])],
            foreground=[("selected", colores["fg"])])
        self.style.configure("Treeview",
            background=colores["treebg"],
            foreground=colores["treefg"],
            fieldbackground=colores["treebg"])
        self.style.configure("Treeview.Heading",
            background=colores["headingbg"],
            foreground=colores["headingfg"],
            font=(family, size, "bold"))
        self.style.configure("TFrame", background=colores["frame_bg"])
        self.style.configure("TLabelframe", background=colores["frame_bg"])
        self.style.configure("TLabelframe.Label",
            background=colores["frame_bg"],
            foreground=colores["fg"])
        self.style.configure("TScale", background=colores["frame_bg"])
        self._notificar()

    def cambiar_tamano(self, delta: int) -> None:
        nuevo = max(8, min(26, self.prefs["font_size"] + delta))
        if nuevo == self.prefs["font_size"]:
            return
        self.prefs["font_size"] = nuevo
        self.aplicar()
        _guardar_prefs(self.prefs)

    def cambiar_fuente(self, family: str) -> None:
        if family == self.prefs["font_family"]:
            return
        self.prefs["font_family"] = family
        self.aplicar()
        _guardar_prefs(self.prefs)

    def cambiar_tema(self, theme_name: str) -> None:
        if theme_name == self.prefs["theme"]:
            return
        self.prefs["theme"] = theme_name
        self.aplicar()
        _guardar_prefs(self.prefs)
