import csv
import re
from datetime import datetime
from typing import List

from src.data.modelos import Transaccion


def formatear_fecha(fecha: datetime) -> str:
    return fecha.strftime("%d/%m/%Y")


def parsear_fecha(cadena: str) -> datetime:
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"):
        try:
            return datetime.strptime(cadena, fmt)
        except ValueError:
            continue
    raise ValueError(f"Formato de fecha no reconocido: '{cadena}'")


def formatear_moneda(monto: float) -> str:
    return f"${monto:,.2f}"


def validar_numero(valor: str) -> float:
    valor = valor.strip().replace(",", ".")
    if not re.match(r"^-?\d+(\.\d+)?$", valor):
        raise ValueError(f"'{valor}' no es un número válido")
    return float(valor)


def _sanitizar_csv(valor) -> str:
    texto = str(valor)
    if texto.startswith(("=", "+", "-", "@", "\t")):
        return "'" + texto
    return texto


def exportar_csv(transacciones: List[Transaccion], archivo: str) -> None:
    with open(archivo, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["ID", "Tipo", "Monto", "Descripción", "Categoría", "Fecha"])
        for t in transacciones:
            writer.writerow([
                _sanitizar_csv(t.id or ""),
                _sanitizar_csv(t.tipo),
                _sanitizar_csv(t.monto),
                _sanitizar_csv(t.descripcion),
                _sanitizar_csv(t.categoria),
                _sanitizar_csv(formatear_fecha(t.fecha)),
            ])
