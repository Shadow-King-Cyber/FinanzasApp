import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime, date, timedelta
from typing import Optional, List
import threading
import calendar as cal_mod
import os
import sys

from src.core.finanzas import (
    calcular_balance, aplicar_transaccion, resumen_por_categoria,
    calcular_ahorro, calcular_promedio_mensual, presupuesto_vs_real, progreso_meta,
)
from src.data.modelos import Transaccion, Cuenta, Presupuesto, MetaAhorro, Categoria
from src.data.persistencia import (
    inicializar_bd, set_cifrador, restablecer_datos,
    guardar_transaccion, actualizar_transaccion, eliminar_transaccion as db_eliminar_transaccion,
    cargar_transacciones, buscar_transacciones, transacciones_por_mes,
    guardar_cuenta, actualizar_cuenta, eliminar_cuenta as db_eliminar_cuenta, cargar_cuentas,
    guardar_presupuesto, eliminar_presupuesto as db_eliminar_presupuesto, cargar_presupuestos,
    guardar_meta, actualizar_meta, eliminar_meta as db_eliminar_meta, cargar_metas,
    guardar_categoria, cargar_categorias, eliminar_categoria as db_eliminar_categoria,
    renombrar_categoria,
    crear_backup, listar_backups, cargar_historial,
)
from src.utils.helpers import formatear_moneda, formatear_fecha, validar_numero, parsear_fecha
from src.ui.preferencias import GestorEstilos, FUENTES_COMUNES, TEMAS
from src.ui.graficos import dibujar_grafico_barras, dibujar_grafico_pastel, dibujar_grafico_linea, dibujar_calendario_mensual

PAGINA_TAM = 50


class ToolTip:
    def __init__(self, widget, texto):
        self.widget = widget
        self.texto = texto
        self.tipwindow = None
        widget.bind("<Enter>", self.enter)
        widget.bind("<Leave>", self.leave)

    def enter(self, _):
        x, y, _, _ = self.widget.bbox("insert") if hasattr(self.widget, "bbox") and self.widget.bbox("insert") else (0, 0, 0, 0)
        x += self.widget.winfo_rootx() + 20
        y += self.widget.winfo_rooty() + 20
        self.tipwindow = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        lbl = tk.Label(tw, text=self.texto, background="#ffffcc", relief="solid",
                       borderwidth=1, font=("Segoe UI", 8))
        lbl.pack()

    def leave(self, _):
        if self.tipwindow:
            self.tipwindow.destroy()
            self.tipwindow = None


class GestionCategoriasDialog(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Gestionar Categorías")
        self.geometry("400x350")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        frame = ttk.Frame(self, padding=16)
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frame, text="Categorías", font=("Segoe UI", 12, "bold")).pack(anchor=tk.W)

        list_frame = ttk.Frame(frame)
        list_frame.pack(fill=tk.BOTH, expand=True, pady=8)

        self.tree = ttk.Treeview(list_frame, columns=("nombre", "tipo"), show="headings", height=8)
        self.tree.heading("nombre", text="Nombre")
        self.tree.heading("tipo", text="Tipo")
        self.tree.column("nombre", width=200)
        self.tree.column("tipo", width=120)
        scroll = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)

        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill=tk.X, pady=4)
        ttk.Button(btn_frame, text="Agregar", command=self._agregar).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="Renombrar", command=self._renombrar).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="Eliminar", command=self._eliminar).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="Cerrar", command=self.destroy).pack(side=tk.RIGHT, padx=2)

        self._cargar()

    def _cargar(self):
        for row in self.tree.get_children():
            self.tree.delete(row)
        for c in cargar_categorias():
            tipo_txt = {"ingreso": "Ingreso", "egreso": "Egreso", "": "Ambos"}.get(c.tipo, c.tipo)
            self.tree.insert("", tk.END, values=(c.nombre, tipo_txt), iid=str(c.id))

    def _agregar(self):
        d = DialogoSimple(self, "Nueva categoría", "Nombre:")
        if d.resultado is None:
            return
        guardar_categoria(Categoria(nombre=d.resultado))
        self._cargar()

    def _renombrar(self):
        sel = self.tree.selection()
        if not sel:
            return
        old = self.tree.item(sel[0], "values")[0]
        d = DialogoSimple(self, "Renombrar", "Nuevo nombre:", valor_inicial=old)
        if d.resultado is None or d.resultado == old:
            return
        renombrar_categoria(int(sel[0]), d.resultado)
        self._cargar()

    def _eliminar(self):
        sel = self.tree.selection()
        if not sel:
            return
        nombre = self.tree.item(sel[0], "values")[0]
        if messagebox.askyesno("Confirmar", f"¿Eliminar '{nombre}'?", parent=self):
            db_eliminar_categoria(int(sel[0]))
            self._cargar()


class DialogoSimple(tk.Toplevel):
    def __init__(self, parent, titulo, etiqueta, valor_inicial=""):
        super().__init__(parent)
        self.title(titulo)
        self.geometry("320x120")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        self.resultado = None

        frame = ttk.Frame(self, padding=16)
        frame.pack(fill=tk.BOTH, expand=True)
        ttk.Label(frame, text=etiqueta).pack(anchor=tk.W)
        self.entry = ttk.Entry(frame, width=30)
        self.entry.pack(fill=tk.X, pady=8)
        self.entry.insert(0, valor_inicial)
        self.entry.focus()
        self.entry.bind("<Return>", lambda e: self._ok())
        ttk.Button(frame, text="OK", command=self._ok).pack()
        self.protocol("WM_DELETE_WINDOW", self._cancel)

    def _ok(self):
        self.resultado = self.entry.get().strip()
        self.destroy()

    def _cancel(self):
        self.resultado = None
        self.destroy()


class BackupDialog(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Copias de seguridad")
        self.geometry("500x350")
        self.transient(parent)
        self.grab_set()

        frame = ttk.Frame(self, padding=16)
        frame.pack(fill=tk.BOTH, expand=True)
        ttk.Label(frame, text="Copias de seguridad", font=("Segoe UI", 12, "bold")).pack(anchor=tk.W)

        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill=tk.X, pady=6)
        ttk.Button(btn_frame, text="Crear respaldo ahora", command=self._crear).pack(side=tk.LEFT, padx=2)

        tree_frame = ttk.Frame(frame)
        tree_frame.pack(fill=tk.BOTH, expand=True)

        self.tree = ttk.Treeview(tree_frame, columns=("nombre", "tamano", "fecha"), show="headings", height=10)
        self.tree.heading("nombre", text="Archivo")
        self.tree.heading("tamano", text="Tamaño")
        self.tree.heading("fecha", text="Fecha")
        self.tree.column("nombre", width=220)
        self.tree.column("tamano", width=80, anchor=tk.E)
        self.tree.column("fecha", width=140, anchor=tk.CENTER)
        scroll = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self._cargar()

    def _crear(self):
        try:
            ruta = crear_backup()
            messagebox.showinfo("Respaldo", f"Respaldo creado:\n{ruta}", parent=self)
            self._cargar()
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo crear respaldo: {e}", parent=self)

    def _cargar(self):
        for row in self.tree.get_children():
            self.tree.delete(row)
        for b in listar_backups():
            kb = b["tamano"] / 1024
            self.tree.insert("", tk.END, values=(
                b["nombre"], f"{kb:.1f} KB", b["fecha"].strftime("%d/%m/%Y %H:%M"),
            ))


class HistorialDialog(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Historial de cambios")
        self.geometry("600x400")
        self.transient(parent)
        self.grab_set()

        frame = ttk.Frame(self, padding=16)
        frame.pack(fill=tk.BOTH, expand=True)
        ttk.Label(frame, text="Historial de cambios", font=("Segoe UI", 12, "bold")).pack(anchor=tk.W)

        tree_frame = ttk.Frame(frame)
        tree_frame.pack(fill=tk.BOTH, expand=True, pady=8)

        cols = ("fecha", "accion", "entidad", "detalle")
        self.tree = ttk.Treeview(tree_frame, columns=cols, show="headings", height=16)
        self.tree.heading("fecha", text="Fecha")
        self.tree.heading("accion", text="Acción")
        self.tree.heading("entidad", text="Entidad")
        self.tree.heading("detalle", text="Detalle")
        self.tree.column("fecha", width=140, anchor=tk.CENTER)
        self.tree.column("accion", width=80, anchor=tk.CENTER)
        self.tree.column("entidad", width=100)
        self.tree.column("detalle", width=250)
        scroll = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)

        for h in cargar_historial():
            colores = {"crear": "#2ecc71", "actualizar": "#3498db", "eliminar": "#e74c3c"}
            tag = h.accion
            self.tree.insert("", tk.END, values=(
                h.fecha.strftime("%d/%m/%Y %H:%M"), h.accion.capitalize(),
                h.entidad.capitalize(), h.detalle,
            ), tags=(tag,))
            self.tree.tag_configure("crear", foreground="#2ecc71")
            self.tree.tag_configure("actualizar", foreground="#3498db")
            self.tree.tag_configure("eliminar", foreground="#e74c3c")


class Dashboard(tk.Tk):
    def __init__(self, cifrador):
        super().__init__()
        self.title("FinanzasApp — Control Financiero")
        self.geometry("1000x720")
        self.minsize(800, 600)
        self._establecer_icono()

        self._cifrador = cifrador
        set_cifrador(cifrador)

        self._modo_compacto = False
        self._pagina_actual = 1
        self._total_paginas = 1
        self._filtro_texto = ""
        self._filtro_desde: Optional[datetime] = None
        self._filtro_hasta: Optional[datetime] = None
        self._filtro_tipo = ""
        self._filtro_categoria = ""
        self._categorias_cache: List[Categoria] = []

        self.gestor = GestorEstilos(self)
        self.gestor.suscribir(self._actualizar_toolbar)

        inicializar_bd()
        self._recargar_categorias()

        self.cuenta_actual: Optional[Cuenta] = None
        self._transaccion_editando: Optional[Transaccion] = None
        self._inicializar_o_cargar_cuenta()
        self._crear_menu()
        self._crear_toolbar()
        self._crear_notebook()
        self._crear_barra_estado()
        self._bind_atajos()
        self._actualizar_resumen()

        self.protocol("WM_DELETE_WINDOW", self._al_salir)

    @staticmethod
    def _ruta_logo() -> str:
        if getattr(sys, "frozen", False):
            base = sys._MEIPASS
        else:
            base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        return os.path.join(base, "assets", "logo.ico")

    def _establecer_icono(self):
        ruta = self._ruta_logo()
        if os.path.exists(ruta):
            try:
                self.iconbitmap(ruta)
            except Exception:
                pass

    def _recargar_categorias(self):
        self._categorias_cache = cargar_categorias()

    def _nombres_categorias(self) -> List[str]:
        return [c.nombre for c in self._categorias_cache]

    def _inicializar_o_cargar_cuenta(self):
        cuentas = cargar_cuentas()
        if cuentas:
            self.cuenta_actual = cuentas[0]
        else:
            self.cuenta_actual = guardar_cuenta(Cuenta(nombre="Principal"))

    def _crear_menu(self):
        barra = tk.Menu(self)
        self.config(menu=barra)

        menu_archivo = tk.Menu(barra, tearoff=0)
        menu_archivo.add_command(label="Exportar transacciones (CSV)", command=self._exportar_csv)
        menu_archivo.add_command(label="Copias de seguridad", command=self._abrir_backup)
        menu_archivo.add_separator()
        menu_archivo.add_command(label="Restablecer datos", command=self._restablecer_datos)
        menu_archivo.add_separator()
        menu_archivo.add_command(label="Gestionar categorías", command=self._gestionar_categorias)
        menu_archivo.add_command(label="Historial de cambios", command=self._abrir_historial)
        menu_archivo.add_separator()
        menu_archivo.add_command(label="Cambiar contraseña", command=self._cambiar_password)
        menu_archivo.add_separator()
        menu_archivo.add_command(label="Salir", command=self._al_salir)
        barra.add_cascade(label="Archivo", menu=menu_archivo)

        menu_ver = tk.Menu(barra, tearoff=0)
        menu_ver.add_command(label="Actualizar todo", command=self._actualizar_todo)
        menu_ver.add_separator()
        self._compacto_var = tk.BooleanVar(value=False)
        menu_ver.add_checkbutton(label="Modo compacto", variable=self._compacto_var,
                                 command=self._alternar_compacto)
        barra.add_cascade(label="Ver", menu=menu_ver)

        menu_ayuda = tk.Menu(barra, tearoff=0)
        menu_ayuda.add_command(label="Acerca de", command=self._acerca_de)
        barra.add_cascade(label="Ayuda", menu=menu_ayuda)

    def _crear_toolbar(self):
        pad = 4 if self._modo_compacto else 8
        tool = ttk.Frame(self)
        tool.pack(fill=tk.X, padx=10, pady=(pad, 0))

        ttk.Label(tool, text="Fuente:").pack(side=tk.LEFT, padx=(0, 4))
        self.cmb_fuente = ttk.Combobox(tool, values=FUENTES_COMUNES, state="readonly", width=16)
        self.cmb_fuente.pack(side=tk.LEFT, padx=(0, 16))
        self.cmb_fuente.set(self.gestor.obtener_familia())
        self.cmb_fuente.bind("<<ComboboxSelected>>",
                             lambda e: self.gestor.cambiar_fuente(self.cmb_fuente.get()))

        self.btn_reducir = ttk.Button(tool, text="A–", width=3,
                   command=lambda: self.gestor.cambiar_tamano(-1))
        self.btn_reducir.pack(side=tk.LEFT, padx=(0, 2))
        ToolTip(self.btn_reducir, "Reducir tamaño de fuente")
        self.lbl_tamano = ttk.Label(tool, text=str(self.gestor.obtener_tamano()), width=3, anchor=tk.CENTER)
        self.lbl_tamano.pack(side=tk.LEFT, padx=2)
        self.btn_aumentar = ttk.Button(tool, text="A+", width=3,
                   command=lambda: self.gestor.cambiar_tamano(1))
        self.btn_aumentar.pack(side=tk.LEFT, padx=(2, 16))
        ToolTip(self.btn_aumentar, "Aumentar tamaño de fuente")

        ttk.Label(tool, text="Tema:").pack(side=tk.LEFT, padx=(0, 4))
        self.cmb_tema = ttk.Combobox(tool, values=list(TEMAS.keys()), state="readonly", width=14)
        self.cmb_tema.pack(side=tk.LEFT)
        self.cmb_tema.set(self.gestor.obtener_tema())
        self.cmb_tema.bind("<<ComboboxSelected>>",
                           lambda e: self.gestor.cambiar_tema(self.cmb_tema.get()))

    def _actualizar_toolbar(self):
        self.cmb_fuente.set(self.gestor.obtener_familia())
        self.lbl_tamano.config(text=str(self.gestor.obtener_tamano()))
        self.cmb_tema.set(self.gestor.obtener_tema())

    def _alternar_compacto(self):
        self._modo_compacto = self._compacto_var.get()
        self._reconstruir_ui()

    def _reconstruir_ui(self):
        for w in self.winfo_children():
            w.destroy()
        self._crear_toolbar()
        self._crear_notebook()
        self._crear_barra_estado()
        self._bind_atajos()
        self._actualizar_todo()

    def _bind_atajos(self):
        self.bind("<Control-n>", lambda e: self.notebook.select(self.frame_agregar))
        self.bind("<Control-N>", lambda e: self.notebook.select(self.frame_agregar))
        self.bind("<Control-e>", lambda e: self._exportar_csv())
        self.bind("<Control-E>", lambda e: self._exportar_csv())
        self.bind("<Control-r>", lambda e: self._actualizar_todo())
        self.bind("<Control-R>", lambda e: self._actualizar_todo())
        self.bind("<Control-f>", lambda e: self._enfocar_busqueda())
        self.bind("<Control-F>", lambda e: self._enfocar_busqueda())

    def _enfocar_busqueda(self):
        self.notebook.select(self.frame_trans)
        if hasattr(self, "entry_busqueda"):
            self.entry_busqueda.focus()

    def _al_salir(self):
        if messagebox.askokcancel("Salir", "¿Estás seguro de que deseas salir?"):
            try:
                crear_backup()
            except Exception:
                pass
            self.destroy()

    def _crear_barra_estado(self):
        self.barra_estado = ttk.Frame(self, relief=tk.SUNKEN)
        self.barra_estado.pack(fill=tk.X, side=tk.BOTTOM, padx=2, pady=(0, 2))

        self.lbl_stat_ahorro = ttk.Label(self.barra_estado, text="Ahorro: --", padding=(8, 2))
        self.lbl_stat_ahorro.pack(side=tk.LEFT)

        self.lbl_stat_promedio = ttk.Label(self.barra_estado, text="Prom. mensual: --", padding=(8, 2))
        self.lbl_stat_promedio.pack(side=tk.LEFT)

        self.lbl_stat_transac = ttk.Label(self.barra_estado, text="Transacciones: 0", padding=(8, 2))
        self.lbl_stat_transac.pack(side=tk.RIGHT)

    def _actualizar_barra_estado(self):
        transacciones = cargar_transacciones(self.cuenta_actual.id)
        cant = len(transacciones)
        self.lbl_stat_transac.config(text=f"Transacciones: {cant}")
        if cant > 0:
            ahorro = calcular_ahorro(transacciones)
            prom = calcular_promedio_mensual(transacciones)
            self.lbl_stat_ahorro.config(text=f"Ahorro: {ahorro:.1f}%")
            self.lbl_stat_promedio.config(text=f"Prom. mensual: {formatear_moneda(prom)}")
        else:
            self.lbl_stat_ahorro.config(text="Ahorro: --")
            self.lbl_stat_promedio.config(text="Prom. mensual: --")

    def _crear_notebook(self):
        pad = 4 if self._modo_compacto else 8
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=(pad, 4))
        self.notebook.bind("<<NotebookTabChanged>>", self._animar_cambio_pestana)

        self._crear_pestana_resumen()
        self._crear_pestana_agregar()
        self._crear_pestana_transacciones()
        self._crear_pestana_graficos()
        self._crear_pestana_calendario()
        self._crear_pestana_presupuestos()
        self._crear_pestana_metas()

    def _animar_cambio_pestana(self, _=None):
        tab = self.notebook.nametowidget(self.notebook.select())
        original = tab.cget("style") if hasattr(tab, "cget") else "TFrame"
        try:
            tab.configure(style="Alerta.TFrame")
            self.after(200, lambda: tab.configure(style=original))
        except tk.TclError:
            pass

    # ==================================================================
    #  Pestaña Resumen
    # ==================================================================
    def _crear_pestana_resumen(self):
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="Resumen")

        pad = 8 if self._modo_compacto else 16
        ttk.Label(frame, text="Resumen Financiero", style="Title.TLabel").pack(pady=(pad, 4))

        sel_frame = ttk.Frame(frame)
        sel_frame.pack(fill=tk.X, padx=20)
        ttk.Label(sel_frame, text="Cuenta:").pack(side=tk.LEFT, padx=(0, 4))
        self.cmb_cuentas = ttk.Combobox(sel_frame, state="readonly", width=20)
        self.cmb_cuentas.pack(side=tk.LEFT)
        self.cmb_cuentas.bind("<<ComboboxSelected>>", self._cambiar_cuenta)
        ttk.Button(sel_frame, text="Editar", command=self._editar_cuenta).pack(side=tk.LEFT, padx=4)
        ttk.Button(sel_frame, text="Eliminar", command=self._eliminar_cuenta).pack(side=tk.LEFT)
        self._actualizar_selector_cuentas()

        info = ttk.Frame(frame)
        info.pack(pady=pad)

        self.lbl_balance = ttk.Label(info, text="Balance: $0.00", style="Heading.TLabel")
        self.lbl_balance.grid(row=0, column=0, padx=24, pady=4)

        self.lbl_ingresos = ttk.Label(info, text="Ingresos: $0.00", style="Heading.TLabel")
        self.lbl_ingresos.grid(row=0, column=1, padx=24, pady=4)

        self.lbl_egresos = ttk.Label(info, text="Egresos: $0.00", style="Heading.TLabel")
        self.lbl_egresos.grid(row=0, column=2, padx=24, pady=4)

        ttk.Separator(frame, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=24, pady=6)

        btn_ref = ttk.Button(frame, text="Actualizar", command=self._actualizar_todo)
        btn_ref.pack(pady=4)
        ToolTip(btn_ref, "Actualizar todo (Ctrl+R)")

        tree_frame = ttk.Frame(frame)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=(4, 12))

        cols = ("categoria", "ingreso", "egreso")
        self.tree_resumen = ttk.Treeview(tree_frame, columns=cols, show="headings", height=10)
        self.tree_resumen.heading("categoria", text="Categoría")
        self.tree_resumen.heading("ingreso", text="Ingresos")
        self.tree_resumen.heading("egreso", text="Egresos")
        self.tree_resumen.column("categoria", width=220, minwidth=140)
        self.tree_resumen.column("ingreso", width=160, minwidth=100, anchor=tk.E)
        self.tree_resumen.column("egreso", width=160, minwidth=100, anchor=tk.E)
        scroll = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree_resumen.yview)
        self.tree_resumen.configure(yscrollcommand=scroll.set)
        self.tree_resumen.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)

    def _actualizar_selector_cuentas(self):
        cuentas = cargar_cuentas()
        self.cmb_cuentas["values"] = [f"{c.nombre} ({c.tipo})" for c in cuentas]
        for i, c in enumerate(cuentas):
            if c.id == self.cuenta_actual.id:
                self.cmb_cuentas.current(i)
                break

    def _cambiar_cuenta(self, _=None):
        cuentas = cargar_cuentas()
        idx = self.cmb_cuentas.current()
        if 0 <= idx < len(cuentas):
            self.cuenta_actual = cuentas[idx]
            self._actualizar_todo()

    def _editar_cuenta(self):
        d = DialogoSimple(self, "Editar cuenta", "Nuevo nombre:", self.cuenta_actual.nombre)
        if d.resultado and d.resultado != self.cuenta_actual.nombre:
            self.cuenta_actual.nombre = d.resultado
            actualizar_cuenta(self.cuenta_actual)
            self._actualizar_selector_cuentas()
            self._actualizar_resumen()

    def _eliminar_cuenta(self):
        cuentas = cargar_cuentas()
        if len(cuentas) <= 1:
            messagebox.showwarning("Advertencia", "No puedes eliminar la única cuenta")
            return
        if messagebox.askyesno("Confirmar", f"¿Eliminar '{self.cuenta_actual.nombre}' y todas sus transacciones?"):
            db_eliminar_cuenta(self.cuenta_actual.id)
            cuentas = cargar_cuentas()
            if cuentas:
                self.cuenta_actual = cuentas[0]
            self._actualizar_selector_cuentas()
            self._actualizar_todo()

    def _restablecer_datos(self):
        if not messagebox.askyesno(
            "Restablecer datos",
            "¿Estás seguro? Se eliminarán TODAS las transacciones, cuentas, presupuestos, metas y categorías.\n\n"
            "Se creará una cuenta 'Principal' por defecto y se restaurarán las categorías originales.\n\n"
            "Esta acción NO se puede deshacer.",
        ):
            return
        if not messagebox.askyesno("Confirmar", "¿Estás ABSOLUTAMENTE seguro?"):
            return
        restablecer_datos()
        self.cuenta_actual = cargar_cuentas()[0]
        self._recargar_categorias()
        self._actualizar_selector_cuentas()
        self._actualizar_todo()
        messagebox.showinfo("Listo", "Datos restablecidos al estado inicial")

    # ==================================================================
    #  Pestaña Agregar
    # ==================================================================
    def _crear_pestana_agregar(self):
        self.frame_agregar = ttk.Frame(self.notebook)
        self.notebook.add(self.frame_agregar, text="Agregar Transacción")

        ttk.Label(self.frame_agregar, text="Nueva Transacción", style="Title.TLabel").pack(pady=(16, 4))

        formulario = ttk.LabelFrame(self.frame_agregar, text="Datos de la transacción", padding=16)
        formulario.pack(pady=12, padx=40, fill=tk.X)

        ttk.Label(formulario, text="Tipo:").grid(row=0, column=0, sticky=tk.W, pady=6, padx=(0, 8))
        self.tipo_var = tk.StringVar(value="egreso")
        cmb_tipo = ttk.Combobox(formulario, textvariable=self.tipo_var,
                                values=["ingreso", "egreso"], state="readonly", width=24)
        cmb_tipo.grid(row=0, column=1, pady=6)

        ttk.Label(formulario, text="Monto ($):").grid(row=1, column=0, sticky=tk.W, pady=6, padx=(0, 8))
        self.entry_monto = ttk.Entry(formulario, width=26)
        self.entry_monto.grid(row=1, column=1, pady=6)

        ttk.Label(formulario, text="Descripción:").grid(row=2, column=0, sticky=tk.W, pady=6, padx=(0, 8))
        self.entry_desc = ttk.Entry(formulario, width=26)
        self.entry_desc.grid(row=2, column=1, pady=6)

        ttk.Label(formulario, text="Categoría:").grid(row=3, column=0, sticky=tk.W, pady=6, padx=(0, 8))
        self.cat_var = tk.StringVar()
        self.cmb_categoria_agregar = ttk.Combobox(formulario, textvariable=self.cat_var,
                                                  values=self._nombres_categorias(), state="readonly", width=24)
        self.cmb_categoria_agregar.grid(row=3, column=1, pady=6)

        self._crear_botones_formulario()

    def _crear_botones_formulario(self):
        self.btn_frame = ttk.Frame(self.frame_agregar)
        self.btn_frame.pack(pady=12)

        self.btn_guardar = ttk.Button(self.btn_frame, text="Guardar Transacción",
                                      command=self._guardar_transaccion_ui)
        self.btn_guardar.pack(side=tk.LEFT, padx=6)
        ToolTip(self.btn_guardar, "Guardar transacción (Ctrl+N)")

        self.btn_cancelar_edicion = ttk.Button(self.btn_frame, text="Cancelar edición",
                                               command=self._cancelar_edicion)
        self.btn_cancelar_edicion.pack(side=tk.LEFT, padx=6)

        self.lbl_modo_edicion = ttk.Label(self.frame_agregar, text="", foreground="#cc0000")
        self.lbl_modo_edicion.pack()

    # ==================================================================
    #  Pestaña Transacciones (búsqueda + paginación)
    # ==================================================================
    def _crear_pestana_transacciones(self):
        self.frame_trans = ttk.Frame(self.notebook)
        self.notebook.add(self.frame_trans, text="Transacciones")

        filtro_frame = ttk.LabelFrame(self.frame_trans, text="Filtros", padding=8)
        filtro_frame.pack(fill=tk.X, padx=8, pady=(8, 4))

        ttk.Label(filtro_frame, text="Buscar:").grid(row=0, column=0, padx=(0, 4))
        self.entry_busqueda = ttk.Entry(filtro_frame, width=20)
        self.entry_busqueda.grid(row=0, column=1, padx=(0, 12))
        self.entry_busqueda.bind("<Return>", lambda e: self._aplicar_filtros())

        ttk.Label(filtro_frame, text="Desde:").grid(row=0, column=2, padx=(0, 4))
        self.entry_desde = ttk.Entry(filtro_frame, width=12)
        self.entry_desde.grid(row=0, column=3, padx=(0, 4))
        self.entry_desde.insert(0, (datetime.now() - timedelta(days=30)).strftime("%d/%m/%Y"))

        ttk.Label(filtro_frame, text="Hasta:").grid(row=0, column=4, padx=(0, 4))
        self.entry_hasta = ttk.Entry(filtro_frame, width=12)
        self.entry_hasta.grid(row=0, column=5, padx=(0, 12))
        self.entry_hasta.insert(0, datetime.now().strftime("%d/%m/%Y"))

        ttk.Label(filtro_frame, text="Tipo:").grid(row=0, column=6, padx=(0, 4))
        self.filtro_tipo_var = tk.StringVar(value="")
        cmb_ft = ttk.Combobox(filtro_frame, textvariable=self.filtro_tipo_var,
                              values=["", "ingreso", "egreso"], state="readonly", width=10)
        cmb_ft.grid(row=0, column=7, padx=(0, 12))

        ttk.Label(filtro_frame, text="Categoría:").grid(row=0, column=8, padx=(0, 4))
        self.filtro_cat_var = tk.StringVar(value="")
        self.cmb_filtro_categoria = ttk.Combobox(filtro_frame, textvariable=self.filtro_cat_var,
                                                 values=[""] + self._nombres_categorias(), state="readonly", width=14)
        self.cmb_filtro_categoria.grid(row=0, column=9, padx=(0, 8))

        ttk.Button(filtro_frame, text="Filtrar", command=self._aplicar_filtros).grid(row=0, column=10, padx=2)
        ttk.Button(filtro_frame, text="Limpiar", command=self._limpiar_filtros).grid(row=0, column=11, padx=2)

        btn_frame = ttk.Frame(self.frame_trans)
        btn_frame.pack(fill=tk.X, padx=8, pady=(4, 2))

        ttk.Button(btn_frame, text="Actualizar",
                   command=self._aplicar_filtros).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="Editar seleccionada",
                   command=self._editar_transaccion).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="Eliminar seleccionada",
                   command=self._eliminar_transaccion).pack(side=tk.LEFT, padx=2)

        tree_frame = ttk.Frame(self.frame_trans)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=(2, 4))

        cols = ("id", "tipo", "monto", "descripcion", "categoria", "fecha")
        self.tree_trans = ttk.Treeview(tree_frame, columns=cols, show="headings", height=14)
        self.tree_trans.heading("id", text="ID")
        self.tree_trans.heading("tipo", text="Tipo")
        self.tree_trans.heading("monto", text="Monto")
        self.tree_trans.heading("descripcion", text="Descripción")
        self.tree_trans.heading("categoria", text="Categoría")
        self.tree_trans.heading("fecha", text="Fecha")
        self.tree_trans.column("id", width=50, minwidth=40, anchor=tk.CENTER)
        self.tree_trans.column("tipo", width=80, minwidth=60, anchor=tk.CENTER)
        self.tree_trans.column("monto", width=100, minwidth=70, anchor=tk.E)
        self.tree_trans.column("descripcion", width=200, minwidth=100)
        self.tree_trans.column("categoria", width=130, minwidth=80)
        self.tree_trans.column("fecha", width=100, minwidth=70, anchor=tk.CENTER)

        scroll = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree_trans.yview)
        self.tree_trans.configure(yscrollcommand=scroll.set)
        self.tree_trans.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree_trans.bind("<Double-1>", lambda e: self._editar_transaccion())

        pag_frame = ttk.Frame(self.frame_trans)
        pag_frame.pack(fill=tk.X, padx=8, pady=(0, 6))

        self.btn_pag_ant = ttk.Button(pag_frame, text="◀ Anterior", command=self._pag_anterior)
        self.btn_pag_ant.pack(side=tk.LEFT, padx=2)
        self.lbl_pag = ttk.Label(pag_frame, text="Página 1 de 1")
        self.lbl_pag.pack(side=tk.LEFT, padx=12)
        self.btn_pag_sig = ttk.Button(pag_frame, text="Siguiente ▶", command=self._pag_siguiente)
        self.btn_pag_sig.pack(side=tk.LEFT, padx=2)

        self._aplicar_filtros()

    def _aplicar_filtros(self):
        self._filtro_texto = self.entry_busqueda.get().strip()
        self._filtro_tipo = self.filtro_tipo_var.get()
        self._filtro_categoria = self.filtro_cat_var.get()

        try:
            desde_str = self.entry_desde.get().strip()
            self._filtro_desde = parsear_fecha(desde_str) if desde_str else None
        except ValueError:
            self._filtro_desde = None

        try:
            hasta_str = self.entry_hasta.get().strip()
            self._filtro_hasta = parsear_fecha(hasta_str) if hasta_str else None
        except ValueError:
            self._filtro_hasta = None

        self._pagina_actual = 1
        self._cargar_transacciones_paginadas()

    def _limpiar_filtros(self):
        self.entry_busqueda.delete(0, tk.END)
        self.filtro_tipo_var.set("")
        self.filtro_cat_var.set("")
        hoy = datetime.now()
        self.entry_desde.delete(0, tk.END)
        self.entry_desde.insert(0, (hoy - timedelta(days=30)).strftime("%d/%m/%Y"))
        self.entry_hasta.delete(0, tk.END)
        self.entry_hasta.insert(0, hoy.strftime("%d/%m/%Y"))
        self._aplicar_filtros()

    def _cargar_transacciones_paginadas(self):
        for row in self.tree_trans.get_children():
            self.tree_trans.delete(row)

        def _cargar():
            trans, total = buscar_transacciones(
                self.cuenta_actual.id,
                texto=self._filtro_texto,
                desde=self._filtro_desde,
                hasta=self._filtro_hasta,
                tipo=self._filtro_tipo,
                categoria=self._filtro_categoria,
                pagina=self._pagina_actual,
                por_pagina=PAGINA_TAM,
            )
            self.after(0, lambda: self._mostrar_pagina(trans, total))

        threading.Thread(target=_cargar, daemon=True).start()

    def _mostrar_pagina(self, trans: List[Transaccion], total: int):
        for t in trans:
            self.tree_trans.insert("", tk.END, values=(
                t.id, t.tipo.capitalize(), formatear_moneda(t.monto),
                t.descripcion, t.categoria, formatear_fecha(t.fecha),
            ))
        self._total_paginas = max(1, (total + PAGINA_TAM - 1) // PAGINA_TAM)
        self.lbl_pag.config(text=f"Página {self._pagina_actual} de {self._total_paginas}")
        self.btn_pag_ant.config(state=tk.NORMAL if self._pagina_actual > 1 else tk.DISABLED)
        self.btn_pag_sig.config(state=tk.NORMAL if self._pagina_actual < self._total_paginas else tk.DISABLED)

    def _pag_anterior(self):
        if self._pagina_actual > 1:
            self._pagina_actual -= 1
            self._cargar_transacciones_paginadas()

    def _pag_siguiente(self):
        if self._pagina_actual < self._total_paginas:
            self._pagina_actual += 1
            self._cargar_transacciones_paginadas()

    # ==================================================================
    #  Pestaña Gráficos
    # ==================================================================
    def _crear_pestana_graficos(self):
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="Gráficos")

        control = ttk.Frame(frame)
        control.pack(fill=tk.X, padx=8, pady=6)

        ttk.Label(control, text="Año:").pack(side=tk.LEFT, padx=(0, 4))
        self.graf_anio_var = tk.StringVar(value=str(datetime.now().year))
        cmb_anio = ttk.Combobox(control, textvariable=self.graf_anio_var,
                                values=[str(y) for y in range(2020, 2031)], state="readonly", width=8)
        cmb_anio.pack(side=tk.LEFT, padx=(0, 12))
        cmb_anio.bind("<<ComboboxSelected>>", lambda e: self._dibujar_todos_graficos())

        ttk.Button(control, text="Actualizar gráficos",
                   command=self._dibujar_todos_graficos).pack(side=tk.LEFT, padx=4)

        nb_graf = ttk.Notebook(frame)
        nb_graf.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 8))

        # Pestaña: Barras por categoría
        self.graf_cat_frame = ttk.Frame(nb_graf)
        nb_graf.add(self.graf_cat_frame, text="Por categoría")
        self.canvas_barras = tk.Canvas(self.graf_cat_frame, bg="white", height=300)
        self.canvas_barras.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        # Pestaña: Pastel
        self.graf_pie_frame = ttk.Frame(nb_graf)
        nb_graf.add(self.graf_pie_frame, text="Distribución")
        self.canvas_pie = tk.Canvas(self.graf_pie_frame, bg="white", height=300)
        self.canvas_pie.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        # Pestaña: Línea mensual
        self.graf_linea_frame = ttk.Frame(nb_graf)
        nb_graf.add(self.graf_linea_frame, text="Evolución mensual")
        self.canvas_linea = tk.Canvas(self.graf_linea_frame, bg="white", height=250)
        self.canvas_linea.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        # Pestaña: Comparación año vs año
        self.graf_comp_frame = ttk.Frame(nb_graf)
        nb_graf.add(self.graf_comp_frame, text="Año vs Año")
        self.canvas_comparacion = tk.Canvas(self.graf_comp_frame, bg="white", height=300)
        self.canvas_comparacion.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        self._dibujar_todos_graficos()

    def _dibujar_todos_graficos(self):
        anio = int(self.graf_anio_var.get())

        def _tarea():
            trans = cargar_transacciones(self.cuenta_actual.id)
            trans_anio = [t for t in trans if t.fecha.year == anio]

            cats_ing: dict = {}
            cats_egr: dict = {}
            total_egr: dict = {}
            gasto_diario: dict = {}
            for t in trans_anio:
                if t.tipo == "ingreso":
                    cats_ing[t.categoria] = cats_ing.get(t.categoria, 0) + t.monto
                else:
                    cats_egr[t.categoria] = cats_egr.get(t.categoria, 0) + t.monto
                    total_egr[t.categoria] = total_egr.get(t.categoria, 0) + t.monto
                    dia = t.fecha.day
                    gasto_diario[dia] = gasto_diario.get(dia, 0) + t.monto

            todas_cats = sorted(set(list(cats_ing.keys()) + list(cats_egr.keys())))
            datos_barras = [(c, cats_ing.get(c, 0), cats_egr.get(c, 0)) for c in todas_cats]

            pie_datos = [(c, v) for c, v in sorted(total_egr.items(), key=lambda x: -x[1])]

            mensual = transacciones_por_mes(self.cuenta_actual.id, anio)
            meses = ["Ene", "Feb", "Mar", "Abr", "May", "Jun",
                     "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
            linea_datos = [(meses[m - 1], ing - egr) for m, ing, egr in mensual]

            anio_ant = anio - 1
            mensual_ant = transacciones_por_mes(self.cuenta_actual.id, anio_ant) if anio_ant >= 2020 else []
            comp_datos = []
            for m_idx in range(1, 13):
                ing_act = egr_act = ing_ant = egr_ant = 0
                for m, ing, egr in mensual:
                    if m == m_idx:
                        ing_act, egr_act = ing, egr
                for m, ing, egr in mensual_ant:
                    if m == m_idx:
                        ing_ant, egr_ant = ing, egr
                comp_datos.append((meses[m_idx - 1], egr_act, egr_ant))

            self.after(0, lambda: self._render_graficos(
                datos_barras, pie_datos, linea_datos, comp_datos, gasto_diario, anio,
            ))

        threading.Thread(target=_tarea, daemon=True).start()

    def _render_graficos(self, datos_barras, pie_datos, linea_datos, comp_datos,
                         gasto_diario, anio):
        cw = self.canvas_barras.winfo_width() or 600
        ch = self.canvas_barras.winfo_height() or 300
        dibujar_grafico_barras(self.canvas_barras, datos_barras, "Ingresos vs Egresos por categoría", cw, ch)

        cw = self.canvas_pie.winfo_width() or 500
        ch = self.canvas_pie.winfo_height() or 300
        dibujar_grafico_pastel(self.canvas_pie, pie_datos, "Distribución de gastos", cw, ch)

        cw = self.canvas_linea.winfo_width() or 600
        ch = self.canvas_linea.winfo_height() or 250
        dibujar_grafico_linea(self.canvas_linea, linea_datos, "Balance mensual", cw, ch)

        cw = self.canvas_comparacion.winfo_width() or 600
        ch = self.canvas_comparacion.winfo_height() or 300
        dibujar_grafico_barras(self.canvas_comparacion, comp_datos,
                               f"Gastos {anio} vs {anio - 1}", cw, ch)

    # ==================================================================
    #  Pestaña Calendario
    # ==================================================================
    def _crear_pestana_calendario(self):
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="Calendario")

        control = ttk.Frame(frame)
        control.pack(fill=tk.X, padx=8, pady=6)

        def _cambiar_mes(delta):
            nuevo = self.cal_fecha_actual.replace(day=1)
            if delta:
                if delta > 0:
                    nuevo = datetime(nuevo.year + (nuevo.month // 12), (nuevo.month % 12) + 1, 1)
                else:
                    if nuevo.month == 1:
                        nuevo = datetime(nuevo.year - 1, 12, 1)
                    else:
                        nuevo = datetime(nuevo.year, nuevo.month - 1, 1)
            self.cal_fecha_actual = nuevo
            self._dibujar_calendario()

        ttk.Button(control, text="◀", width=3, command=lambda: _cambiar_mes(-1)).pack(side=tk.LEFT, padx=2)
        self.cal_fecha_actual = datetime.now()
        self.lbl_cal_mes = ttk.Label(control, text="", font=("Segoe UI", 11, "bold"))
        self.lbl_cal_mes.pack(side=tk.LEFT, padx=12)
        ttk.Button(control, text="▶", width=3, command=lambda: _cambiar_mes(1)).pack(side=tk.LEFT, padx=2)

        self.canvas_cal = tk.Canvas(frame, bg="white", height=350)
        self.canvas_cal.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 8))

        self._dibujar_calendario()

    def _dibujar_calendario(self):
        anio = self.cal_fecha_actual.year
        mes = self.cal_fecha_actual.month
        nombre_mes = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
                      "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"][mes - 1]
        self.lbl_cal_mes.config(text=f"{nombre_mes} {anio}")

        def _tarea():
            trans = cargar_transacciones(self.cuenta_actual.id)
            montos: dict = {}
            for t in trans:
                if t.fecha.year == anio and t.fecha.month == mes and t.tipo == "egreso":
                    montos[t.fecha.day] = montos.get(t.fecha.day, 0) + t.monto

            cw = self.canvas_cal.winfo_width() or 600
            ch = self.canvas_cal.winfo_height() or 350
            self.after(0, lambda: dibujar_calendario_mensual(
                self.canvas_cal, anio, mes, montos, cw, ch))

        threading.Thread(target=_tarea, daemon=True).start()

    # ==================================================================
    #  Pestaña Presupuestos (con alertas)
    # ==================================================================
    def _crear_pestana_presupuestos(self):
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="Presupuestos")

        ttk.Label(frame, text="Administrar Presupuestos", style="Title.TLabel").pack(pady=(16, 4))

        form = ttk.LabelFrame(frame, text="Nuevo presupuesto", padding=16)
        form.pack(pady=12, padx=40, fill=tk.X)

        ttk.Label(form, text="Categoría:").grid(row=0, column=0, sticky=tk.W, pady=6, padx=(0, 8))
        self.pres_cat_var = tk.StringVar()
        self.cmb_categoria_presupuesto = ttk.Combobox(form, textvariable=self.pres_cat_var,
                                                      values=self._nombres_categorias(), state="readonly", width=24)
        self.cmb_categoria_presupuesto.grid(row=0, column=1, pady=6)

        ttk.Label(form, text="Límite ($):").grid(row=1, column=0, sticky=tk.W, pady=6, padx=(0, 8))
        self.entry_limite = ttk.Entry(form, width=26)
        self.entry_limite.grid(row=1, column=1, pady=6)

        ttk.Label(form, text="Período:").grid(row=2, column=0, sticky=tk.W, pady=6, padx=(0, 8))
        self.pres_periodo_var = tk.StringVar(value="mensual")
        cmb_per = ttk.Combobox(form, textvariable=self.pres_periodo_var,
                               values=["semanal", "mensual", "anual"], state="readonly", width=24)
        cmb_per.grid(row=2, column=1, pady=6)

        ttk.Button(frame, text="Guardar Presupuesto",
                   command=self._guardar_presupuesto_ui).pack(pady=6)
        ttk.Button(frame, text="Eliminar seleccionado",
                   command=self._eliminar_presupuesto).pack(pady=(0, 6))

        ttk.Separator(frame, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=24, pady=6)
        ttk.Label(frame, text="Progreso de presupuestos", style="Heading.TLabel").pack(pady=4)

        tree_frame = ttk.Frame(frame)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=(4, 12))

        cols = ("categoria", "limite", "gastado", "restante", "usado")
        self.tree_pres = ttk.Treeview(tree_frame, columns=cols, show="headings", height=8)
        self.tree_pres.heading("categoria", text="Categoría")
        self.tree_pres.heading("limite", text="Límite")
        self.tree_pres.heading("gastado", text="Gastado")
        self.tree_pres.heading("restante", text="Restante")
        self.tree_pres.heading("usado", text="% Usado")

        self.tree_pres.column("categoria", width=180, minwidth=120)
        self.tree_pres.column("limite", width=120, minwidth=80, anchor=tk.E)
        self.tree_pres.column("gastado", width=120, minwidth=80, anchor=tk.E)
        self.tree_pres.column("restante", width=120, minwidth=80, anchor=tk.E)
        self.tree_pres.column("usado", width=100, minwidth=70, anchor=tk.CENTER)

        scroll = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree_pres.yview)
        self.tree_pres.configure(yscrollcommand=scroll.set)
        self.tree_pres.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self._cargar_presupuestos_tabla()

    def _cargar_presupuestos_tabla(self):
        for row in self.tree_pres.get_children():
            self.tree_pres.delete(row)

        transacciones = cargar_transacciones(self.cuenta_actual.id)
        for p in cargar_presupuestos():
            gastado, restante, usado = presupuesto_vs_real(transacciones, p)
            tag = ""
            if usado >= 100:
                tag = "critico"
            elif usado >= 80:
                tag = "alerta"
            self.tree_pres.insert("", tk.END, values=(
                p.categoria, formatear_moneda(p.limite), formatear_moneda(gastado),
                formatear_moneda(restante), f"{usado:.1f}%",
            ), tags=(tag,) if tag else ())
        self.tree_pres.tag_configure("alerta", foreground="#e67e22")
        self.tree_pres.tag_configure("critico", foreground="#e74c3c")

    # ==================================================================
    #  Pestaña Metas
    # ==================================================================
    def _crear_pestana_metas(self):
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="Metas de Ahorro")

        ttk.Label(frame, text="Mis Metas de Ahorro", style="Title.TLabel").pack(pady=(16, 4))

        form = ttk.LabelFrame(frame, text="Nueva meta", padding=16)
        form.pack(pady=12, padx=40, fill=tk.X)

        ttk.Label(form, text="Nombre:").grid(row=0, column=0, sticky=tk.W, pady=6, padx=(0, 8))
        self.meta_nombre_var = tk.StringVar()
        ttk.Entry(form, textvariable=self.meta_nombre_var, width=26).grid(row=0, column=1, pady=6)

        ttk.Label(form, text="Objetivo ($):").grid(row=1, column=0, sticky=tk.W, pady=6, padx=(0, 8))
        self.meta_objetivo_var = tk.StringVar()
        ttk.Entry(form, textvariable=self.meta_objetivo_var, width=26).grid(row=1, column=1, pady=6)

        ttk.Label(form, text="Actual ($):").grid(row=2, column=0, sticky=tk.W, pady=6, padx=(0, 8))
        self.meta_actual_var = tk.StringVar(value="0")
        ttk.Entry(form, textvariable=self.meta_actual_var, width=26).grid(row=2, column=1, pady=6)

        ttk.Label(form, text="Fecha límite:").grid(row=3, column=0, sticky=tk.W, pady=6, padx=(0, 8))
        self.meta_fecha_var = tk.StringVar()
        ttk.Entry(form, textvariable=self.meta_fecha_var, width=26).grid(row=3, column=1, pady=6)

        ttk.Button(frame, text="Guardar Meta",
                   command=self._guardar_meta_ui).pack(pady=4)
        ttk.Button(frame, text="Eliminar seleccionada",
                   command=self._eliminar_meta).pack(pady=(0, 6))

        ttk.Separator(frame, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=24, pady=6)
        ttk.Label(frame, text="Progreso", style="Heading.TLabel").pack(pady=4)

        tree_frame = ttk.Frame(frame)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=(4, 12))

        cols = ("nombre", "objetivo", "actual", "progreso", "fecha_limite")
        self.tree_metas = ttk.Treeview(tree_frame, columns=cols, show="headings", height=8)
        self.tree_metas.heading("nombre", text="Nombre")
        self.tree_metas.heading("objetivo", text="Objetivo")
        self.tree_metas.heading("actual", text="Actual")
        self.tree_metas.heading("progreso", text="% Completado")
        self.tree_metas.heading("fecha_limite", text="Fecha límite")
        self.tree_metas.column("nombre", width=200, minwidth=120)
        self.tree_metas.column("objetivo", width=130, minwidth=80, anchor=tk.E)
        self.tree_metas.column("actual", width=130, minwidth=80, anchor=tk.E)
        self.tree_metas.column("progreso", width=120, minwidth=80, anchor=tk.CENTER)
        self.tree_metas.column("fecha_limite", width=120, minwidth=80, anchor=tk.CENTER)
        scroll = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree_metas.yview)
        self.tree_metas.configure(yscrollcommand=scroll.set)
        self.tree_metas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self._cargar_metas_tabla()

    # ==================================================================
    #  Acciones generales
    # ==================================================================
    def _actualizar_todo(self):
        self._actualizar_resumen()
        self._aplicar_filtros()
        self._cargar_presupuestos_tabla()
        self._cargar_metas_tabla()
        self._actualizar_barra_estado()
        self._recargar_categorias()
        self._actualizar_categorias_combos()

    def _actualizar_categorias_combos(self):
        cats = self._nombres_categorias()
        if hasattr(self, 'cmb_categoria_agregar') and self.cmb_categoria_agregar.winfo_exists():
            self.cmb_categoria_agregar["values"] = cats
        if hasattr(self, 'cmb_categoria_presupuesto') and self.cmb_categoria_presupuesto.winfo_exists():
            self.cmb_categoria_presupuesto["values"] = cats
        if hasattr(self, 'cmb_filtro_categoria') and self.cmb_filtro_categoria.winfo_exists():
            self.cmb_filtro_categoria["values"] = [""] + cats

    def _actualizar_resumen(self):
        transacciones = cargar_transacciones(self.cuenta_actual.id)

        ingresos = [t for t in transacciones if t.tipo == "ingreso"]
        egresos = [t for t in transacciones if t.tipo == "egreso"]

        total_ingresos = sum(t.monto for t in ingresos)
        total_egresos = sum(t.monto for t in egresos)
        balance = calcular_balance(ingresos, egresos)

        self.lbl_balance.config(text=f"Balance: {formatear_moneda(balance)}")
        self.lbl_ingresos.config(text=f"Ingresos: {formatear_moneda(total_ingresos)}")
        self.lbl_egresos.config(text=f"Egresos: {formatear_moneda(total_egresos)}")

        for row in self.tree_resumen.get_children():
            self.tree_resumen.delete(row)

        resumen = resumen_por_categoria(transacciones)
        for cat, datos in sorted(resumen.items()):
            self.tree_resumen.insert("", tk.END, values=(
                cat,
                formatear_moneda(datos["ingreso"]),
                formatear_moneda(datos["egreso"]),
            ))

        self._actualizar_barra_estado()

    # ---- Transacciones (CRUD) ---- #

    def _guardar_transaccion_ui(self):
        try:
            monto = validar_numero(self.entry_monto.get())
            if monto <= 0:
                raise ValueError("El monto debe ser positivo")
        except ValueError as e:
            messagebox.showerror("Error", str(e))
            return

        descripcion = self.entry_desc.get().strip()
        if not descripcion:
            messagebox.showerror("Error", "La descripción no puede estar vacía")
            return

        transaccion = Transaccion(
            tipo=self.tipo_var.get(),
            monto=monto,
            descripcion=descripcion,
            categoria=self.cat_var.get(),
            fecha=datetime.now(),
        )

        if self._transaccion_editando is not None:
            transaccion.id = self._transaccion_editando.id
            transaccion.fecha = self._transaccion_editando.fecha
            actualizar_transaccion(transaccion)
            self._transaccion_editando = None
            self.lbl_modo_edicion.config(text="")
            self.btn_guardar.config(text="Guardar Transacción")
            messagebox.showinfo("Éxito", "Transacción actualizada correctamente")
        else:
            guardar_transaccion(transaccion, self.cuenta_actual.id)
            aplicar_transaccion(self.cuenta_actual, transaccion)
            messagebox.showinfo("Éxito", "Transacción guardada correctamente")

        self.entry_monto.delete(0, tk.END)
        self.entry_desc.delete(0, tk.END)
        self._actualizar_todo()

    def _cancelar_edicion(self):
        self._transaccion_editando = None
        self.lbl_modo_edicion.config(text="")
        self.btn_guardar.config(text="Guardar Transacción")
        self.entry_monto.delete(0, tk.END)
        self.entry_desc.delete(0, tk.END)

    def _cargar_transacciones_tabla(self):
        self._aplicar_filtros()

    def _editar_transaccion(self):
        seleccion = self.tree_trans.selection()
        if not seleccion:
            messagebox.showwarning("Advertencia", "Seleccione una transacción")
            return

        valores = self.tree_trans.item(seleccion[0], "values")
        trans_id = int(valores[0])

        for t in cargar_transacciones(self.cuenta_actual.id):
            if t.id == trans_id:
                self._transaccion_editando = t
                break

        if self._transaccion_editando is None:
            return

        self.tipo_var.set(self._transaccion_editando.tipo)
        self.entry_monto.delete(0, tk.END)
        self.entry_monto.insert(0, str(self._transaccion_editando.monto))
        self.entry_desc.delete(0, tk.END)
        self.entry_desc.insert(0, self._transaccion_editando.descripcion)
        self.cat_var.set(self._transaccion_editando.categoria)
        self.lbl_modo_edicion.config(text=f"Editando transacción #{trans_id}")
        self.btn_guardar.config(text="Actualizar Transacción")
        self.notebook.select(self.frame_agregar)

    def _eliminar_transaccion(self):
        seleccion = self.tree_trans.selection()
        if not seleccion:
            messagebox.showwarning("Advertencia", "Seleccione una transacción")
            return

        valores = self.tree_trans.item(seleccion[0], "values")
        trans_id = int(valores[0])
        desc = valores[3]

        if not messagebox.askyesno("Confirmar", f"¿Eliminar '{desc}' (ID {trans_id})?"):
            return

        db_eliminar_transaccion(trans_id)
        self._actualizar_todo()

    # ---- Presupuestos ---- #

    def _guardar_presupuesto_ui(self):
        try:
            limite = validar_numero(self.entry_limite.get())
            if limite <= 0:
                raise ValueError("El límite debe ser positivo")
        except ValueError as e:
            messagebox.showerror("Error", str(e))
            return

        presupuesto = Presupuesto(
            categoria=self.pres_cat_var.get(),
            limite=limite,
            periodo=self.pres_periodo_var.get(),
        )
        guardar_presupuesto(presupuesto)
        self.entry_limite.delete(0, tk.END)
        self._cargar_presupuestos_tabla()
        messagebox.showinfo("Éxito", "Presupuesto guardado")

        usado = self._verificar_alerta_presupuesto(presupuesto.categoria)
        if usado >= 80:
            messagebox.showwarning("Alerta", f"¡Has usado el {usado:.1f}% del presupuesto de '{presupuesto.categoria}'!")

    def _verificar_alerta_presupuesto(self, categoria: str) -> float:
        for p in cargar_presupuestos():
            if p.categoria == categoria:
                trans = cargar_transacciones(self.cuenta_actual.id)
                gastado, _, usado = presupuesto_vs_real(trans, p)
                return usado
        return 0

    def _eliminar_presupuesto(self):
        seleccion = self.tree_pres.selection()
        if not seleccion:
            messagebox.showwarning("Advertencia", "Seleccione un presupuesto")
            return

        valores = self.tree_pres.item(seleccion[0], "values")
        pres_id = None
        for p in cargar_presupuestos():
            if p.categoria == valores[0]:
                pres_id = p.id
                break

        if pres_id is None:
            return

        if not messagebox.askyesno("Confirmar", f"¿Eliminar presupuesto '{valores[0]}'?"):
            return

        db_eliminar_presupuesto(pres_id)
        self._cargar_presupuestos_tabla()

    # ---- Metas ---- #

    def _guardar_meta_ui(self):
        nombre = self.meta_nombre_var.get().strip()
        if not nombre:
            messagebox.showerror("Error", "El nombre no puede estar vacío")
            return

        try:
            objetivo = validar_numero(self.meta_objetivo_var.get())
            if objetivo <= 0:
                raise ValueError("El objetivo debe ser positivo")
        except ValueError as e:
            messagebox.showerror("Error", str(e))
            return

        try:
            actual = validar_numero(self.meta_actual_var.get())
            if actual < 0:
                raise ValueError("El actual no puede ser negativo")
        except ValueError as e:
            messagebox.showerror("Error", str(e))
            return

        fecha_lim = None
        fecha_str = self.meta_fecha_var.get().strip()
        if fecha_str:
            try:
                fecha_lim = parsear_fecha(fecha_str).date()
            except ValueError:
                messagebox.showerror("Error", "Formato de fecha inválido (use DD/MM/AAAA)")
                return

        meta = MetaAhorro(nombre=nombre, monto_objetivo=objetivo, monto_actual=actual, fecha_limite=fecha_lim)
        guardar_meta(meta)
        self.meta_nombre_var.set("")
        self.meta_objetivo_var.set("")
        self.meta_actual_var.set("0")
        self.meta_fecha_var.set("")
        self._cargar_metas_tabla()
        messagebox.showinfo("Éxito", "Meta guardada")

    def _eliminar_meta(self):
        seleccion = self.tree_metas.selection()
        if not seleccion:
            messagebox.showwarning("Advertencia", "Seleccione una meta")
            return

        valores = self.tree_metas.item(seleccion[0], "values")
        meta_id = None
        for m in cargar_metas():
            if m.nombre == valores[0] and formatear_moneda(m.monto_objetivo) == valores[1]:
                meta_id = m.id
                break

        if meta_id is None:
            return

        if not messagebox.askyesno("Confirmar", f"¿Eliminar meta '{valores[0]}'?"):
            return

        db_eliminar_meta(meta_id)
        self._cargar_metas_tabla()

    def _cargar_metas_tabla(self):
        for row in self.tree_metas.get_children():
            self.tree_metas.delete(row)

        for m in cargar_metas():
            pct = progreso_meta(m)
            fl = m.fecha_limite.strftime("%d/%m/%Y") if m.fecha_limite else "--"
            tag = ""
            if pct >= 100:
                tag = "completa"
            self.tree_metas.insert("", tk.END, values=(
                m.nombre, formatear_moneda(m.monto_objetivo),
                formatear_moneda(m.monto_actual), f"{pct:.1f}%", fl,
            ), tags=(tag,) if tag else ())
        self.tree_metas.tag_configure("completa", foreground="#2ecc71")

    # ---- Exportación ---- #

    def _exportar_csv(self):
        from src.utils.helpers import exportar_csv

        archivo = asksaveasfilename(defaultextension=".csv", filetypes=[("CSV", "*.csv")])
        if archivo:
            transacciones = cargar_transacciones(self.cuenta_actual.id)
            exportar_csv(transacciones, archivo)
            messagebox.showinfo("Éxito", f"Transacciones exportadas a {archivo}")

    # ---- Diálogos ---- #

    def _gestionar_categorias(self):
        GestionCategoriasDialog(self)
        self._recargar_categorias()
        self._actualizar_categorias_combos()

    def _abrir_backup(self):
        BackupDialog(self)

    def _abrir_historial(self):
        HistorialDialog(self)

    def _cambiar_password(self):
        from src.ui.login import CambioPasswordDialog
        dialogo = CambioPasswordDialog(self)
        self.wait_window(dialogo)
        nuevo = dialogo.obtener_nuevo_cifrador()
        if nuevo is not None:
            self._cifrador = nuevo
            set_cifrador(nuevo)
            messagebox.showinfo("Éxito", "Contraseña cambiada correctamente")

    @staticmethod
    def _acerca_de():
        messagebox.showinfo(
            "Acerca de",
            "FinanzasApp v2.0\n"
            "Control financiero personal\n"
            "\nCaracterísticas:\n"
            "• Registro de ingresos y egresos\n"
            "• Presupuestos por categoría\n"
            "• Metas de ahorro\n"
            "• Gráficos interactivos\n"
            "• Calendario de gastos\n"
            "• Temas y fuente personalizable\n"
            "• Exportación a CSV\n"
            "• Copias de seguridad cifradas\n"
            "• Categorías personalizables\n"
            "• Historial de cambios\n"
            "• Atajos de teclado",
        )
