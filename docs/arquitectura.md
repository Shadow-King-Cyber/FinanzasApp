# Arquitectura de FinanzasApp

## Vista general

```
┌─────────────────────────────────────────────────────┐
│                     main.py                          │
│   Punto de entrada: instancia Dashboard y loop       │
└──────────────┬──────────────────────────────────────┘
               │
┌──────────────▼──────────────────────────────────────┐
│              ui/dashboard.py                         │
│   Interfaz Tkinter con Notebook (4 pestañas):       │
│   - Resumen: balance, ingresos, egresos + tabla     │
│   - Agregar: formulario de transacciones             │
│   - Transacciones: listado con Treeview              │
│   - Presupuestos: CRUD de límites por categoría      │
└──────┬──────────────────────┬───────────────────────┘
       │                      │
┌──────▼──────────┐  ┌───────▼───────────────────────┐
│   core/         │  │       data/                    │
│  (lógica)       │  │    (persistencia)              │
│                 │  │                                │
│  calculadora.py │  │  modelos.py (dataclasses)      │
│   - +, -, *, /  │  │   - Transaccion                │
│   - validación  │  │   - Cuenta                     │
│                 │  │   - Presupuesto                │
│  finanzas.py    │  │                                │
│   - balance     │  │  persistencia.py               │
│   - presupuesto │  │   - SQLite3                    │
│   - categorías  │  │   - CRUD completo              │
│   - filtros     │  │                                │
└─────────────────┘  └───────┬───────────────────────┘
                             │
                    ┌────────▼────────┐
                    │   utils/        │
                    │   helpers.py    │
                    │  - formatos     │
                    │  - validación   │
                    │  - exportación  │
                    └─────────────────┘
```

## Flujo de datos

1. El usuario interactúa con el Dashboard (Tkinter).
2. El Dashboard llama a `persistencia.py` para guardar/cargar datos en SQLite.
3. Las operaciones lógicas (balance, presupuesto) se delegan a `finanzas.py`.
4. `finanzas.py` usa `calculadora.py` para operaciones aritméticas con validación.
5. `helpers.py` proporciona utilidades de formato y exportación a CSV.

## Módulos

| Módulo          | Responsabilidad                                  |
|-----------------|--------------------------------------------------|
| `main.py`       | Arranque de la aplicación                        |
| `ui/dashboard`  | Interfaz gráfica completa                        |
| `core/calculadora` | Operaciones matemáticas con validación        |
| `core/finanzas` | Lógica financiera (balance, presupuestos)        |
| `data/modelos`  | Estructuras de datos (dataclasses)               |
| `data/persistencia` | Persistencia en SQLite                       |
| `utils/helpers` | Funciones auxiliares                             |

## Tecnologías

- **Python 3.10+** — Lenguaje principal
- **Tkinter / ttk** — Interfaz gráfica (incluida en Python)
- **SQLite3** — Base de datos local (incluida en Python)
- **pytest** — Pruebas unitarias
