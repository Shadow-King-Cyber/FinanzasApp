from dataclasses import dataclass, field
from datetime import datetime, date
from typing import Optional, List


@dataclass
class Categoria:
    nombre: str
    tipo: str = ""
    id: Optional[int] = None


@dataclass
class Transaccion:
    tipo: str
    monto: float
    descripcion: str
    categoria: str
    fecha: datetime = field(default_factory=datetime.now)
    id: Optional[int] = None


@dataclass
class Cuenta:
    nombre: str
    balance: float = 0.0
    tipo: str = "general"
    id: Optional[int] = None


@dataclass
class Presupuesto:
    categoria: str
    limite: float
    periodo: str = "mensual"
    id: Optional[int] = None


@dataclass
class MetaAhorro:
    nombre: str
    monto_objetivo: float
    monto_actual: float = 0.0
    fecha_limite: Optional[date] = None
    id: Optional[int] = None


@dataclass
class HistorialCambio:
    accion: str
    entidad: str
    entidad_id: int
    detalle: str
    fecha: datetime = field(default_factory=datetime.now)
    id: Optional[int] = None
