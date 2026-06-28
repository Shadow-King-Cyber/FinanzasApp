import sqlite3
import os
import sys
import shutil
import json
from datetime import datetime, date, timedelta
from typing import List, Optional, Tuple

from cryptography.fernet import Fernet

from src.data.modelos import Transaccion, Cuenta, Presupuesto, MetaAhorro, Categoria, HistorialCambio


if getattr(sys, "frozen", False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

DB_PATH = os.path.join(BASE_DIR, "finanzas.db")
BACKUP_DIR = os.path.join(BASE_DIR, "backups")

_cifrador: Optional[Fernet] = None


def set_cifrador(cifrador: Fernet) -> None:
    global _cifrador
    _cifrador = cifrador


def _cifrar(texto: str) -> str:
    if _cifrador is None:
        return texto
    return _cifrador.encrypt(texto.encode("utf-8")).decode("utf-8")


def _descifrar(cifrado: str) -> str:
    if _cifrador is None:
        return cifrado
    try:
        return _cifrador.decrypt(cifrado.encode("utf-8")).decode("utf-8")
    except Exception:
        return cifrado


def _conectar() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


SCHEMA_VERSION = 3


def _version_bd(conn: sqlite3.Connection) -> int:
    try:
        row = conn.execute("SELECT version FROM _schema_version").fetchone()
        return row["version"] if row else 0
    except sqlite3.OperationalError:
        conn.execute("CREATE TABLE IF NOT EXISTS _schema_version (version INTEGER)")
        conn.execute("INSERT INTO _schema_version (version) VALUES (0)")
        return 0


def inicializar_bd() -> None:
    with _conectar() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS cuentas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL,
                balance TEXT NOT NULL DEFAULT '0',
                tipo TEXT NOT NULL DEFAULT 'general'
            );
            CREATE TABLE IF NOT EXISTS transacciones (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cuenta_id INTEGER,
                tipo TEXT NOT NULL CHECK(tipo IN ('ingreso','egreso')),
                monto TEXT NOT NULL,
                descripcion TEXT NOT NULL,
                categoria TEXT NOT NULL,
                fecha TEXT NOT NULL,
                FOREIGN KEY (cuenta_id) REFERENCES cuentas(id)
            );
            CREATE TABLE IF NOT EXISTS presupuestos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                categoria TEXT NOT NULL UNIQUE,
                limite TEXT NOT NULL,
                periodo TEXT NOT NULL DEFAULT 'mensual'
            );
            CREATE TABLE IF NOT EXISTS metas_ahorro (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL,
                monto_objetivo TEXT NOT NULL,
                monto_actual TEXT NOT NULL DEFAULT '0',
                fecha_limite TEXT
            );
            CREATE TABLE IF NOT EXISTS categorias (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL UNIQUE,
                tipo TEXT NOT NULL DEFAULT ''
            );
            CREATE TABLE IF NOT EXISTS historial_cambios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                accion TEXT NOT NULL,
                entidad TEXT NOT NULL,
                entidad_id INTEGER NOT NULL,
                detalle TEXT NOT NULL,
                fecha TEXT NOT NULL
            );
        """)
        _migrar_bd(conn)


def _columna_existe(conn: sqlite3.Connection, tabla: str, columna: str) -> bool:
    cursor = conn.execute(f"PRAGMA table_info({tabla})")
    return any(r["name"] == columna for r in cursor.fetchall())


def _safe_alter(conn: sqlite3.Connection, sql: str) -> None:
    try:
        conn.execute(sql)
    except sqlite3.OperationalError:
        pass


def _tabla_existe(conn: sqlite3.Connection, tabla: str) -> bool:
    r = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (tabla,)).fetchone()
    return r is not None


def _migrar_bd(conn: sqlite3.Connection) -> None:
    version = _version_bd(conn)

    if version < 1:
        if not _columna_existe(conn, "cuentas", "tipo"):
            _safe_alter(conn, "ALTER TABLE cuentas ADD COLUMN tipo TEXT NOT NULL DEFAULT 'general'")
        if not _columna_existe(conn, "presupuestos", "periodo"):
            _safe_alter(conn, "ALTER TABLE presupuestos ADD COLUMN periodo TEXT NOT NULL DEFAULT 'mensual'")
        conn.execute("CREATE TABLE IF NOT EXISTS metas_ahorro (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT NOT NULL, monto_objetivo REAL NOT NULL, monto_actual REAL NOT NULL DEFAULT 0, fecha_limite TEXT)")
        version = 1

    if version < 2:
        if _cifrador is not None:
            _encrypt_existing_data(conn)
        version = 2

    if version < 3:
        if not _tabla_existe(conn, "categorias"):
            conn.execute("CREATE TABLE categorias (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT NOT NULL UNIQUE, tipo TEXT NOT NULL DEFAULT '')")
        if not _tabla_existe(conn, "historial_cambios"):
            conn.execute("CREATE TABLE historial_cambios (id INTEGER PRIMARY KEY AUTOINCREMENT, accion TEXT NOT NULL, entidad TEXT NOT NULL, entidad_id INTEGER NOT NULL, detalle TEXT NOT NULL, fecha TEXT NOT NULL)")
        _seed_categorias(conn)
        version = 3

    conn.execute("DELETE FROM _schema_version")
    conn.execute("INSERT INTO _schema_version (version) VALUES (?)", (SCHEMA_VERSION,))


def _seed_categorias(conn: sqlite3.Connection) -> None:
    existentes = {r["nombre"] for r in conn.execute("SELECT nombre FROM categorias").fetchall()}
    defaults = [
        ("Salario", "ingreso"), ("Freelance", "ingreso"), ("Inversiones", "ingreso"),
        ("Otros ingresos", "ingreso"), ("Alimentación", "egreso"), ("Transporte", "egreso"),
        ("Vivienda", "egreso"), ("Servicios", "egreso"), ("Entretenimiento", "egreso"),
        ("Salud", "egreso"), ("Educación", "egreso"), ("Otros egresos", "egreso"),
    ]
    for nombre, tipo in defaults:
        if nombre not in existentes:
            conn.execute("INSERT INTO categorias (nombre, tipo) VALUES (?, ?)", (nombre, tipo))


def _encrypt_existing_data(conn: sqlite3.Connection) -> None:
    rows = conn.execute("SELECT id, nombre, balance FROM cuentas").fetchall()
    for r in rows:
        conn.execute("UPDATE cuentas SET nombre=?, balance=? WHERE id=?",
                     (_cifrar(r["nombre"]), _cifrar(str(r["balance"])), r["id"]))

    rows = conn.execute("SELECT id, monto, descripcion FROM transacciones").fetchall()
    for r in rows:
        conn.execute("UPDATE transacciones SET monto=?, descripcion=? WHERE id=?",
                     (_cifrar(str(r["monto"])), _cifrar(r["descripcion"]), r["id"]))

    rows = conn.execute("SELECT id, limite FROM presupuestos").fetchall()
    for r in rows:
        conn.execute("UPDATE presupuestos SET limite=? WHERE id=?",
                     (_cifrar(str(r["limite"])), r["id"]))

    rows = conn.execute("SELECT id, nombre, monto_objetivo, monto_actual FROM metas_ahorro").fetchall()
    for r in rows:
        conn.execute("UPDATE metas_ahorro SET nombre=?, monto_objetivo=?, monto_actual=? WHERE id=?",
                     (_cifrar(r["nombre"]), _cifrar(str(r["monto_objetivo"])),
                      _cifrar(str(r["monto_actual"])), r["id"]))


# ===================================================================
#  Backups
# ===================================================================

def crear_backup() -> str:
    os.makedirs(BACKUP_DIR, exist_ok=True)
    fecha = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"finanzas_backup_{fecha}.db"
    backup_path = os.path.join(BACKUP_DIR, backup_name)
    shutil.copy2(DB_PATH, backup_path)

    if _cifrador is not None:
        with open(backup_path, "rb") as f:
            data = f.read()
        encrypted = _cifrador.encrypt(data)
        enc_path = backup_path + ".enc"
        with open(enc_path, "wb") as f:
            f.write(encrypted)
        os.remove(backup_path)
        return enc_path

    return backup_path


def listar_backups() -> List[dict]:
    os.makedirs(BACKUP_DIR, exist_ok=True)
    backups = []
    for fname in sorted(os.listdir(BACKUP_DIR), reverse=True):
        fpath = os.path.join(BACKUP_DIR, fname)
        if os.path.isfile(fpath):
            backups.append({
                "nombre": fname,
                "ruta": fpath,
                "tamano": os.path.getsize(fpath),
                "fecha": datetime.fromtimestamp(os.path.getmtime(fpath)),
            })
    return backups



# ===================================================================
#  Historial de cambios
# ===================================================================

def registrar_cambio(accion: str, entidad: str, entidad_id: int, detalle: str) -> None:
    with _conectar() as conn:
        conn.execute(
            "INSERT INTO historial_cambios (accion, entidad, entidad_id, detalle, fecha) VALUES (?, ?, ?, ?, ?)",
            (accion, entidad, entidad_id, detalle, datetime.now().isoformat()),
        )


def cargar_historial(limite: int = 200) -> List[HistorialCambio]:
    with _conectar() as conn:
        filas = conn.execute(
            "SELECT id, accion, entidad, entidad_id, detalle, fecha FROM historial_cambios ORDER BY fecha DESC LIMIT ?",
            (limite,),
        ).fetchall()
    return [
        HistorialCambio(
            id=r["id"], accion=r["accion"], entidad=r["entidad"],
            entidad_id=r["entidad_id"], detalle=r["detalle"],
            fecha=datetime.fromisoformat(r["fecha"]),
        )
        for r in filas
    ]


# ===================================================================
#  Categorías
# ===================================================================

def guardar_categoria(cat: Categoria) -> Categoria:
    with _conectar() as conn:
        try:
            cur = conn.execute(
                "INSERT INTO categorias (nombre, tipo) VALUES (?, ?)",
                (cat.nombre, cat.tipo),
            )
            cat.id = cur.lastrowid
        except sqlite3.IntegrityError:
            cur = conn.execute(
                "UPDATE categorias SET tipo=? WHERE nombre=?",
                (cat.tipo, cat.nombre),
            )
            fila = conn.execute("SELECT id FROM categorias WHERE nombre=?", (cat.nombre,)).fetchone()
            cat.id = fila["id"] if fila else cat.id
    return cat


def cargar_categorias() -> List[Categoria]:
    with _conectar() as conn:
        filas = conn.execute("SELECT id, nombre, tipo FROM categorias ORDER BY nombre").fetchall()
    return [Categoria(id=r["id"], nombre=r["nombre"], tipo=r["tipo"]) for r in filas]


def eliminar_categoria(categoria_id: int) -> None:
    with _conectar() as conn:
        conn.execute("DELETE FROM categorias WHERE id = ?", (categoria_id,))


def renombrar_categoria(categoria_id: int, nuevo_nombre: str) -> None:
    with _conectar() as conn:
        conn.execute("UPDATE categorias SET nombre=? WHERE id=?", (nuevo_nombre, categoria_id))


# ===================================================================
#  Cuentas
# ===================================================================

def guardar_cuenta(cuenta: Cuenta) -> Cuenta:
    with _conectar() as conn:
        try:
            cur = conn.execute(
                "INSERT INTO cuentas (nombre, balance, tipo) VALUES (?, ?, ?)",
                (_cifrar(cuenta.nombre), _cifrar(str(cuenta.balance)), cuenta.tipo),
            )
            cuenta.id = cur.lastrowid
        except sqlite3.OperationalError:
            _migrar_bd(conn)
            cur = conn.execute(
                "INSERT INTO cuentas (nombre, balance, tipo) VALUES (?, ?, ?)",
                (_cifrar(cuenta.nombre), _cifrar(str(cuenta.balance)), cuenta.tipo),
            )
            cuenta.id = cur.lastrowid
    registrar_cambio("crear", "cuenta", cuenta.id, f"Cuenta creada: {cuenta.nombre}")
    return cuenta


def actualizar_cuenta(cuenta: Cuenta) -> None:
    with _conectar() as conn:
        conn.execute(
            "UPDATE cuentas SET nombre=?, balance=?, tipo=? WHERE id=?",
            (_cifrar(cuenta.nombre), _cifrar(str(cuenta.balance)), cuenta.tipo, cuenta.id),
        )
    registrar_cambio("actualizar", "cuenta", cuenta.id, f"Cuenta actualizada: {cuenta.nombre}")


def eliminar_cuenta(cuenta_id: int) -> None:
    with _conectar() as conn:
        conn.execute("DELETE FROM transacciones WHERE cuenta_id = ?", (cuenta_id,))
        conn.execute("DELETE FROM cuentas WHERE id = ?", (cuenta_id,))
    registrar_cambio("eliminar", "cuenta", cuenta_id, "Cuenta eliminada")


def cargar_cuentas() -> List[Cuenta]:
    with _conectar() as conn:
        try:
            filas = conn.execute("SELECT id, nombre, balance, tipo FROM cuentas").fetchall()
        except sqlite3.OperationalError:
            _migrar_bd(conn)
            filas = conn.execute("SELECT id, nombre, balance, tipo FROM cuentas").fetchall()
    return [
        Cuenta(
            id=r["id"],
            nombre=_descifrar(r["nombre"]),
            balance=float(_descifrar(r["balance"])),
            tipo=r["tipo"],
        )
        for r in filas
    ]


# ===================================================================
#  Transacciones
# ===================================================================

def guardar_transaccion(transaccion: Transaccion, cuenta_id: int) -> Transaccion:
    with _conectar() as conn:
        cur = conn.execute(
            "INSERT INTO transacciones (cuenta_id, tipo, monto, descripcion, categoria, fecha) VALUES (?, ?, ?, ?, ?, ?)",
            (cuenta_id, transaccion.tipo, _cifrar(str(transaccion.monto)),
             _cifrar(transaccion.descripcion), transaccion.categoria,
             transaccion.fecha.isoformat()),
        )
        transaccion.id = cur.lastrowid
    registrar_cambio("crear", "transaccion", transaccion.id,
                     f"{transaccion.tipo}: ${transaccion.monto:.2f} - {transaccion.descripcion}")
    return transaccion


def actualizar_transaccion(transaccion: Transaccion) -> None:
    with _conectar() as conn:
        conn.execute(
            "UPDATE transacciones SET tipo=?, monto=?, descripcion=?, categoria=?, fecha=? WHERE id=?",
            (transaccion.tipo, _cifrar(str(transaccion.monto)),
             _cifrar(transaccion.descripcion), transaccion.categoria,
             transaccion.fecha.isoformat(), transaccion.id),
        )
    registrar_cambio("actualizar", "transaccion", transaccion.id,
                     f"{transaccion.tipo}: ${transaccion.monto:.2f} - {transaccion.descripcion}")


def eliminar_transaccion(transaccion_id: int) -> None:
    with _conectar() as conn:
        conn.execute("DELETE FROM transacciones WHERE id = ?", (transaccion_id,))
    registrar_cambio("eliminar", "transaccion", transaccion_id, "Transacción eliminada")


def cargar_transacciones(cuenta_id: Optional[int] = None) -> List[Transaccion]:
    with _conectar() as conn:
        if cuenta_id is not None:
            filas = conn.execute(
                "SELECT id, tipo, monto, descripcion, categoria, fecha FROM transacciones WHERE cuenta_id = ? ORDER BY fecha DESC",
                (cuenta_id,),
            ).fetchall()
        else:
            filas = conn.execute(
                "SELECT id, tipo, monto, descripcion, categoria, fecha FROM transacciones ORDER BY fecha DESC"
            ).fetchall()
    return [
        Transaccion(
            id=r["id"],
            tipo=r["tipo"],
            monto=float(_descifrar(r["monto"])),
            descripcion=_descifrar(r["descripcion"]),
            categoria=r["categoria"],
            fecha=datetime.fromisoformat(r["fecha"]),
        )
        for r in filas
    ]


def cargar_transacciones_por_rango(cuenta_id: int, desde: datetime, hasta: datetime) -> List[Transaccion]:
    with _conectar() as conn:
        filas = conn.execute(
            "SELECT id, tipo, monto, descripcion, categoria, fecha FROM transacciones "
            "WHERE cuenta_id = ? AND fecha >= ? AND fecha <= ? ORDER BY fecha DESC",
            (cuenta_id, desde.isoformat(), hasta.isoformat()),
        ).fetchall()
    return [
        Transaccion(
            id=r["id"], tipo=r["tipo"],
            monto=float(_descifrar(r["monto"])),
            descripcion=_descifrar(r["descripcion"]),
            categoria=r["categoria"],
            fecha=datetime.fromisoformat(r["fecha"]),
        )
        for r in filas
    ]


def buscar_transacciones(cuenta_id: int, texto: str = "", desde: Optional[datetime] = None,
                         hasta: Optional[datetime] = None, tipo: str = "",
                         categoria: str = "", pagina: int = 1, por_pagina: int = 50
                         ) -> Tuple[List[Transaccion], int]:
    condiciones = ["cuenta_id = ?"]
    params: list = [cuenta_id]

    if desde:
        condiciones.append("fecha >= ?")
        params.append(desde.isoformat())
    if hasta:
        condiciones.append("fecha <= ?")
        params.append(hasta.isoformat())
    if tipo:
        condiciones.append("tipo = ?")
        params.append(tipo)
    if categoria:
        condiciones.append("categoria = ?")
        params.append(categoria)

    where = " AND ".join(condiciones)

    with _conectar() as conn:
        total_row = conn.execute(
            f"SELECT COUNT(*) as cnt FROM transacciones WHERE {where}", params
        ).fetchone()
        total = total_row["cnt"]

        filas = conn.execute(
            f"SELECT id, tipo, monto, descripcion, categoria, fecha FROM transacciones WHERE {where} ORDER BY fecha DESC",
            params,
        ).fetchall()

    transacciones = [
        Transaccion(
            id=r["id"], tipo=r["tipo"],
            monto=float(_descifrar(r["monto"])),
            descripcion=_descifrar(r["descripcion"]),
            categoria=r["categoria"],
            fecha=datetime.fromisoformat(r["fecha"]),
        )
        for r in filas
    ]

    if texto:
        texto_low = texto.lower()
        transacciones = [t for t in transacciones if texto_low in t.descripcion.lower()]

    total = len(transacciones)

    inicio = (pagina - 1) * por_pagina
    transacciones = transacciones[inicio:inicio + por_pagina]

    return transacciones, total


def transacciones_por_mes(cuenta_id: int, anio: int) -> List[Tuple[int, float, float]]:
    with _conectar() as conn:
        filas = conn.execute(
            "SELECT tipo, monto, fecha FROM transacciones WHERE cuenta_id = ? AND fecha >= ? AND fecha < ?",
            (cuenta_id, f"{anio}-01-01", f"{anio + 1}-01-01"),
        ).fetchall()
    por_mes: dict = {}
    for r in filas:
        mes = int(r["fecha"][5:7])
        monto = float(_descifrar(r["monto"]))
        if mes not in por_mes:
            por_mes[mes] = {"ingreso": 0.0, "egreso": 0.0}
        por_mes[mes][r["tipo"]] += monto
    return [(m, d["ingreso"], d["egreso"]) for m, d in sorted(por_mes.items())]


# ===================================================================
#  Presupuestos
# ===================================================================

def guardar_presupuesto(presupuesto: Presupuesto) -> Presupuesto:
    with _conectar() as conn:
        try:
            cur = conn.execute(
                "INSERT OR REPLACE INTO presupuestos (categoria, limite, periodo) VALUES (?, ?, ?)",
                (presupuesto.categoria, _cifrar(str(presupuesto.limite)), presupuesto.periodo),
            )
            presupuesto.id = cur.lastrowid
        except sqlite3.OperationalError:
            _migrar_bd(conn)
            cur = conn.execute(
                "INSERT OR REPLACE INTO presupuestos (categoria, limite, periodo) VALUES (?, ?, ?)",
                (presupuesto.categoria, _cifrar(str(presupuesto.limite)), presupuesto.periodo),
            )
            presupuesto.id = cur.lastrowid
    registrar_cambio("crear", "presupuesto", presupuesto.id, f"Presupuesto: {presupuesto.categoria} = ${presupuesto.limite:.2f}")
    return presupuesto


def eliminar_presupuesto(presupuesto_id: int) -> None:
    with _conectar() as conn:
        conn.execute("DELETE FROM presupuestos WHERE id = ?", (presupuesto_id,))
    registrar_cambio("eliminar", "presupuesto", presupuesto_id, "Presupuesto eliminado")


def cargar_presupuestos() -> List[Presupuesto]:
    with _conectar() as conn:
        try:
            filas = conn.execute("SELECT id, categoria, limite, periodo FROM presupuestos").fetchall()
        except sqlite3.OperationalError:
            _migrar_bd(conn)
            filas = conn.execute("SELECT id, categoria, limite, periodo FROM presupuestos").fetchall()
    return [
        Presupuesto(
            id=r["id"],
            categoria=r["categoria"],
            limite=float(_descifrar(r["limite"])),
            periodo=r["periodo"],
        )
        for r in filas
    ]


# ===================================================================
#  Metas de ahorro
# ===================================================================

def guardar_meta(meta: MetaAhorro) -> MetaAhorro:
    with _conectar() as conn:
        cur = conn.execute(
            "INSERT INTO metas_ahorro (nombre, monto_objetivo, monto_actual, fecha_limite) VALUES (?, ?, ?, ?)",
            (_cifrar(meta.nombre), _cifrar(str(meta.monto_objetivo)),
             _cifrar(str(meta.monto_actual)),
             meta.fecha_limite.isoformat() if meta.fecha_limite else None),
        )
        meta.id = cur.lastrowid
    registrar_cambio("crear", "meta", meta.id, f"Meta: {meta.nombre} - ${meta.monto_objetivo:.2f}")
    return meta


def actualizar_meta(meta: MetaAhorro) -> None:
    with _conectar() as conn:
        conn.execute(
            "UPDATE metas_ahorro SET nombre=?, monto_objetivo=?, monto_actual=?, fecha_limite=? WHERE id=?",
            (_cifrar(meta.nombre), _cifrar(str(meta.monto_objetivo)),
             _cifrar(str(meta.monto_actual)),
             meta.fecha_limite.isoformat() if meta.fecha_limite else None, meta.id),
        )
    registrar_cambio("actualizar", "meta", meta.id, f"Meta actualizada: {meta.nombre}")


def eliminar_meta(meta_id: int) -> None:
    with _conectar() as conn:
        conn.execute("DELETE FROM metas_ahorro WHERE id = ?", (meta_id,))
    registrar_cambio("eliminar", "meta", meta_id, "Meta eliminada")


def cargar_metas() -> List[MetaAhorro]:
    with _conectar() as conn:
        filas = conn.execute("SELECT id, nombre, monto_objetivo, monto_actual, fecha_limite FROM metas_ahorro").fetchall()
    result = []
    for r in filas:
        fl = None
        if r["fecha_limite"]:
            fl = date.fromisoformat(r["fecha_limite"])
        result.append(MetaAhorro(
            id=r["id"],
            nombre=_descifrar(r["nombre"]),
            monto_objetivo=float(_descifrar(r["monto_objetivo"])),
            monto_actual=float(_descifrar(r["monto_actual"])),
            fecha_limite=fl,
        ))
    return result


def restablecer_datos() -> None:
    with _conectar() as conn:
        conn.executescript("""
            DELETE FROM transacciones;
            DELETE FROM presupuestos;
            DELETE FROM metas_ahorro;
            DELETE FROM historial_cambios;
            DELETE FROM cuentas;
            DELETE FROM categorias;
        """)
        _seed_categorias(conn)
    guardar_cuenta(Cuenta(nombre="Principal"))
