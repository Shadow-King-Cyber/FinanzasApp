import tkinter as tk
from tkinter import ttk, messagebox
import os
import sys
try:
    import pyperclip
except ImportError:
    pyperclip = None

from src.auth.seguridad import existe_cuenta, registrar, autenticar, cambiar_password, obtener_pista, recuperar_con_recovery


class LoginDialog(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("FinanzasApp — Inicio de sesión")
        self.geometry("420x420")
        self.resizable(False, False)
        self._establecer_icono()

        self._cifrador = None
        self._usuario = None
        self._es_registro = not existe_cuenta()

        self._crear_interfaz()

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

    def _crear_interfaz(self):
        frame = ttk.Frame(self, padding=30)
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frame, text="FinanzasApp", font=("Segoe UI", 18, "bold")).pack(pady=(0, 4))
        ttk.Label(frame, text="Control financiero personal", font=("Segoe UI", 10)).pack(pady=(0, 20))

        ttk.Label(frame, text="Usuario:").pack(anchor=tk.W)
        self.entry_usuario = ttk.Entry(frame, width=30)
        self.entry_usuario.pack(fill=tk.X, pady=(2, 10))
        if self._es_registro:
            self.entry_usuario.insert(0, "admin")

        ttk.Label(frame, text="Contraseña:").pack(anchor=tk.W)
        self.entry_password = ttk.Entry(frame, width=30, show="*")
        self.entry_password.pack(fill=tk.X, pady=(2, 10))
        self.entry_password.bind("<Return>", lambda e: self._aceptar())

        self.lbl_pista = ttk.Label(frame, text="Pista (opcional):")
        self.entry_pista = ttk.Entry(frame, width=30)
        if not self._es_registro:
            self.lbl_pista.pack_forget()
            self.entry_pista.pack_forget()
        else:
            self.entry_pista.pack(fill=tk.X, pady=(2, 10))

        self.btn_principal = ttk.Button(
            frame, text="Crear cuenta" if self._es_registro else "Iniciar sesión",
            command=self._aceptar,
        )
        self.btn_principal.pack(pady=6)

        self.lbl_cambio = ttk.Label(frame, text="", foreground="#0078d4", cursor="hand2")
        self.lbl_cambio.pack(pady=2)
        if self._es_registro:
            self.lbl_cambio.config(text="¿Ya tienes cuenta? Inicia sesión")
            self.lbl_cambio.bind("<Button-1>", lambda e: self._alternar_modo())
        else:
            self.lbl_cambio.config(text="¿Primera vez? Crea una cuenta")
            self.lbl_cambio.bind("<Button-1>", lambda e: self._alternar_modo())

        self.lbl_recuperar = ttk.Label(frame, text="¿Olvidaste tu contraseña?", foreground="#cc0000", cursor="hand2")
        if not self._es_registro:
            self.lbl_recuperar.bind("<Button-1>", lambda e: self._mostrar_recuperacion())
            self.lbl_recuperar.pack(pady=2)

        self.btn_cancelar = ttk.Button(frame, text="Salir", command=self.destroy)
        self.btn_cancelar.pack(pady=4)

        self.entry_password.focus()

    def _alternar_modo(self):
        self._es_registro = not self._es_registro
        if self._es_registro:
            self.btn_principal.config(text="Crear cuenta")
            self.lbl_cambio.config(text="¿Ya tienes cuenta? Inicia sesión")
            self.lbl_recuperar.pack_forget()
            self.lbl_pista.pack(anchor=tk.W)
            self.entry_pista.pack(fill=tk.X, pady=(2, 10))
            self.geometry("420x420")
        else:
            self.btn_principal.config(text="Iniciar sesión")
            self.lbl_cambio.config(text="¿Primera vez? Crea una cuenta")
            self.lbl_pista.pack_forget()
            self.entry_pista.pack_forget()
            self.lbl_recuperar.pack(pady=2)
            self.geometry("420x380")

    def _aceptar(self):
        usuario = self.entry_usuario.get().strip()
        password = self.entry_password.get()

        if not usuario:
            messagebox.showerror("Error", "Ingrese un nombre de usuario")
            return
        if not password:
            messagebox.showerror("Error", "Ingrese la contraseña")
            return
        if len(password) < 4:
            messagebox.showerror("Error", "La contraseña debe tener al menos 4 caracteres")
            return

        if self._es_registro:
            if existe_cuenta():
                messagebox.showerror("Error", "Ya existe una cuenta registrada")
                return
            pista = self.entry_pista.get().strip()
            try:
                cifrador, recovery = registrar(usuario, password, pista)
                self._cifrador = cifrador
                self._usuario = usuario
                self._mostrar_recovery(recovery)
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo crear la cuenta: {e}")
        else:
            resultado = autenticar(password)
            if resultado is None:
                messagebox.showerror("Error", "Usuario o contraseña incorrectos")
                self.entry_password.delete(0, tk.END)
                self.entry_password.focus()
                return
            self._cifrador, self._usuario = resultado
            self.destroy()

    def _mostrar_recovery(self, recovery: str):
        top = tk.Toplevel(self)
        top.title("Código de recuperación")
        top.geometry("460x220")
        top.resizable(False, False)
        top.transient(self)
        top.grab_set()

        frame = ttk.Frame(top, padding=20)
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frame, text="¡GUARDA ESTE CÓDIGO!", font=("Segoe UI", 14, "bold"),
                  foreground="#cc0000").pack(pady=(0, 8))
        ttk.Label(frame, text="Si olvidas tu contraseña, usa este código para recuperarla.",
                  wraplength=400).pack(pady=(0, 12))

        codigo_frame = ttk.Frame(frame)
        codigo_frame.pack(pady=4)
        ttk.Label(codigo_frame, text=recovery, font=("Consolas", 18, "bold"),
                  foreground="#0078d4").pack(side=tk.LEFT, padx=(0, 8))

        def copiar():
            try:
                if pyperclip:
                    pyperclip.copy(recovery)
                else:
                    top.clipboard_clear()
                    top.clipboard_append(recovery)
            except Exception:
                top.clipboard_clear()
                top.clipboard_append(recovery)
            messagebox.showinfo("Copiado", "Código copiado al portapapeles", parent=top)

        ttk.Button(codigo_frame, text="Copiar", command=copiar).pack(side=tk.LEFT)

        ttk.Button(frame, text="Continuar", command=lambda: (top.destroy(), self.destroy())
                   ).pack(pady=(12, 0))

    def _mostrar_recuperacion(self):
        pista = obtener_pista()
        mensaje = f"Pista: {pista}" if pista else "No hay pista guardada."
        if messagebox.askyesno("¿Olvidaste tu contraseña?", f"{mensaje}\n\n¿Tienes el código de recuperación?"):
            self._dialogo_recovery()

    def _dialogo_recovery(self):
        top = tk.Toplevel(self)
        top.title("Recuperar cuenta")
        top.geometry("400x200")
        top.resizable(False, False)
        top.transient(self)
        top.grab_set()

        frame = ttk.Frame(top, padding=20)
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frame, text="Ingresa tu código de recuperación",
                  font=("Segoe UI", 11)).pack(pady=(0, 12))

        entry = ttk.Entry(frame, width=30, font=("Consolas", 12))
        entry.pack(fill=tk.X, pady=(0, 12))
        entry.focus()
        entry.bind("<Return>", lambda e: recuperar())

        def recuperar():
            codigo = entry.get().strip()
            if not codigo:
                return
            resultado = recuperar_con_recovery(codigo)
            if resultado is None:
                messagebox.showerror("Error", "Código inválido", parent=top)
                return
            cifrador, nueva_pass, nueva_recovery = resultado
            top.destroy()
            self._mostrar_nueva_password(nueva_pass, nueva_recovery)
            self._cifrador = cifrador
            self._usuario = "admin"
            self.destroy()

        ttk.Button(frame, text="Recuperar", command=recuperar).pack(pady=6)

    def _mostrar_nueva_password(self, password: str, recovery: str):
        messagebox.showinfo(
            "Cuenta recuperada",
            f"Tu nueva contraseña es:\n\n{password}\n\n"
            f"Guárdala. También se generó un nuevo código de recuperación.\n\n"
            f"Nuevo código: {recovery}"
        )

    def obtener_cifrador(self):
        return self._cifrador

    def obtener_usuario(self):
        return self._usuario


class CambioPasswordDialog(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Cambiar contraseña")
        self.geometry("360x220")
        self.resizable(False, False)
        self._nuevo_cifrador = None

        frame = ttk.Frame(self, padding=20)
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frame, text="Contraseña actual:").pack(anchor=tk.W)
        self.entry_actual = ttk.Entry(frame, show="*", width=28)
        self.entry_actual.pack(fill=tk.X, pady=(2, 8))

        ttk.Label(frame, text="Contraseña nueva:").pack(anchor=tk.W)
        self.entry_nueva = ttk.Entry(frame, show="*", width=28)
        self.entry_nueva.pack(fill=tk.X, pady=(2, 8))

        ttk.Button(frame, text="Cambiar", command=self._cambiar).pack(pady=6)

        self.entry_actual.focus()

    def _cambiar(self):
        actual = self.entry_actual.get()
        nueva = self.entry_nueva.get()
        if not actual or not nueva:
            messagebox.showerror("Error", "Complete ambos campos", parent=self)
            return
        if len(nueva) < 4:
            messagebox.showerror("Error", "La nueva contraseña debe tener al menos 4 caracteres", parent=self)
            return

        resultado = cambiar_password(actual, nueva)
        if resultado is None:
            messagebox.showerror("Error", "Contraseña actual incorrecta", parent=self)
            self.entry_actual.delete(0, tk.END)
            self.entry_nueva.delete(0, tk.END)
            return

        self._nuevo_cifrador = resultado
        messagebox.showinfo("Éxito", "Contraseña cambiada correctamente", parent=self)
        self.destroy()

    def obtener_nuevo_cifrador(self):
        return self._nuevo_cifrador
