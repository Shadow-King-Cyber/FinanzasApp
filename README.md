# FinanzasApp

Aplicación de escritorio para control financiero personal con interfaz gráfica Tkinter, persistencia SQLite cifrada y autenticación por contraseña maestra.

## Cómo funciona

1. **Registro único**: Al ejecutar la app por primera vez, se te pide crear un usuario, contraseña maestra y opcionalmente una pista. Se genera un **código de recuperación de 16 dígitos hexadecimales** — guárdalo, es la única forma de recuperar acceso si olvidas la contraseña.

2. **Login**: Cada vez que abras la app deberás ingresar tu contraseña maestra, que deriva la clave Fernet (PBKDF2-SHA256, 600k iteraciones) para descifrar los datos. Si olvidaste la contraseña, puedes usar el código de recuperación para generar una nueva.

3. **Dashboard** (7 pestañas):
   - **Resumen**: Balance general, selector/editor/eliminador de cuentas, tabla de ingresos vs egresos por categoría.
   - **Agregar Transacción**: Formulario para registrar ingresos/egresos con monto, descripción y categoría.
   - **Transacciones**: Lista paginada con filtros por texto, rango de fechas, tipo y categoría. Doble clic para editar.
   - **Gráficos** (4 sub-pestañas): Barras por categoría, pastel de distribución, evolución mensual y comparación año vs año.
   - **Calendario**: Heatmap mensual de gastos por día con navegación entre meses.
   - **Presupuestos**: Define límites por categoría. Alertas visuales (naranja >80%, rojo >100%) y popup al exceder 80%.
   - **Metas de Ahorro**: Define metas con monto objetivo, monto actual y fecha límite. Barra de progreso en porcentaje.

4. **Personalización**: Toolbar superior con selector de tema (5 temas), familia de fuente y tamaño (botones A+/A–). Las preferencias persisten entre sesiones.

5. **Atajos de teclado**: Ctrl+N (Agregar), Ctrl+E (exportar CSV), Ctrl+R (refrescar), Ctrl+F (buscar).

6. **Seguridad**: Todos los campos sensibles (montos, descripciones, nombres) se cifran con Fernet AES-128-CBC antes de escribirse a disco. Búsqueda de texto se realiza en memoria tras descifrado. Backup completo cifrado.

7. **Backup automático**: Al salir se genera una copia cifrada de la base de datos en `backups/`. Copias adicionales desde Archivo → Copias de seguridad.

8. **Exportación**: Archivo → Exportar transacciones (CSV) con codificación UTF-8 BOM.

9. **Restablecer datos**: Archivo → Restablecer datos (doble confirmación) borra todas las tablas y recrea la cuenta Principal con categorías por defecto.

## Topología del proyecto

```
FinanzasApp/
├── src/                        # Código fuente
│   ├── main.py                 # Punto de entrada
│   ├── auth/
│   │   └── seguridad.py        # PBKDF2, Fernet, registro, login, recovery
│   ├── core/
│   │   ├── calculadora.py      # Operaciones aritméticas validadas
│   │   └── finanzas.py         # Lógica de negocio (balance, presupuestos, etc.)
│   ├── data/
│   │   ├── modelos.py          # Dataclasses (Transaccion, Cuenta, etc.)
│   │   └── persistencia.py     # SQLite CRUD + cifrado + migraciones + backup
│   ├── ui/
│   │   ├── dashboard.py        # Ventana principal con Notebook de 7 pestañas
│   │   ├── login.py            # Login/registro/recuperación
│   │   ├── graficos.py         # Dibujo de gráficos en Canvas
│   │   └── preferencias.py     # Gestor de estilos (temas, fuentes)
│   └── utils/
│       └── helpers.py          # Formateo, validación, exportación CSV
├── tests/
│   └── test_finanzas.py        # 30 pruebas unitarias (calculadora + finanzas)
├── dist/
│   └── FinanzasApp.exe         # Ejecutable compilado (single-file, no requiere Python)
├── docs/                       # Documentación adicional
├── assets/                     # Recursos gráficos
└── requirements.txt            # Dependencias (solo desarrollo)
```

**Flujo de datos**: El usuario interactúa con el Dashboard (Tkinter) → llama a `persistencia.py` (SQLite cifrado) → las operaciones lógicas se delegan a `finanzas.py` → `calculadora.py` para aritmética validada → `helpers.py` para formatos.

## Ejecutable compilado

El archivo `dist/FinanzasApp.exe` es un ejecutable **portable** (single-file, PyInstaller) que no requiere Python ni dependencias externas. Al ejecutarse:

- Crea `finanzas.db` (base de datos SQLite cifrada) en el mismo directorio.
- Crea `finanzas.key` (almacén de clave derivada de la contraseña).
- Crea `finanzas_prefs.json` (preferencias de tema/fuente).
- Crea `backups/` (copias de seguridad cifradas).

Para desarrollar o modificar la app, clona el repositorio, instala las dependencias con `pip install -r requirements.txt` y ejecuta `python src/main.py`.
