from collections import defaultdict
from datetime import datetime, date
from typing import List, Dict, Tuple

from src.core.calculadora import sumar, restar, dividir, porcentaje, promedio
from src.data.modelos import Transaccion, Cuenta, Presupuesto, MetaAhorro


def _separar_ingresos_egresos(transacciones: List[Transaccion]) -> Tuple[List[Transaccion], List[Transaccion]]:
    ingresos = [t for t in transacciones if t.tipo == "ingreso"]
    egresos = [t for t in transacciones if t.tipo == "egreso"]
    return ingresos, egresos


def calcular_balance(ingresos: List[Transaccion], egresos: List[Transaccion]) -> float:
    total_ingresos = sum(t.monto for t in ingresos)
    total_egresos = sum(t.monto for t in egresos)
    return restar(total_ingresos, total_egresos)


def calcular_balance_desde_lista(transacciones: List[Transaccion]) -> float:
    ingresos, egresos = _separar_ingresos_egresos(transacciones)
    return calcular_balance(ingresos, egresos)


def calcular_presupuesto_restante(presupuesto: Presupuesto, gastado: float) -> float:
    return restar(presupuesto.limite, gastado)


def aplicar_transaccion(cuenta: Cuenta, transaccion: Transaccion) -> None:
    if transaccion.tipo == "ingreso":
        cuenta.balance = sumar(cuenta.balance, transaccion.monto)
    elif transaccion.tipo == "egreso":
        cuenta.balance = restar(cuenta.balance, transaccion.monto)
    else:
        raise ValueError(f"Tipo de transacción inválido: {transaccion.tipo}")


def resumen_por_categoria(transacciones: List[Transaccion]) -> Dict[str, Dict[str, float]]:
    resumen: Dict[str, Dict[str, float]] = {}
    for t in transacciones:
        if t.categoria not in resumen:
            resumen[t.categoria] = {"ingreso": 0.0, "egreso": 0.0}
        resumen[t.categoria][t.tipo] = sumar(resumen[t.categoria][t.tipo], t.monto)
    return resumen


def top_categorias(transacciones: List[Transaccion], tipo: str = "egreso", limite: int = 5) -> List[Tuple[str, float]]:
    filtradas = [t for t in transacciones if t.tipo == tipo]
    agrupado: Dict[str, float] = defaultdict(float)
    for t in filtradas:
        agrupado[t.categoria] = sumar(agrupado[t.categoria], t.monto)
    return sorted(agrupado.items(), key=lambda x: x[1], reverse=True)[:limite]


def filtrar_por_fecha(transacciones: List[Transaccion], desde: datetime, hasta: datetime) -> List[Transaccion]:
    return [t for t in transacciones if desde <= t.fecha <= hasta]


def calcular_promedio_mensual(transacciones: List[Transaccion]) -> float:
    _, egresos = _separar_ingresos_egresos(transacciones)
    if not egresos:
        return 0.0
    meses = len({(t.fecha.year, t.fecha.month) for t in egresos}) or 1
    return dividir(sum(t.monto for t in egresos), meses)


def calcular_ahorro(transacciones: List[Transaccion]) -> float:
    ingresos, egresos = _separar_ingresos_egresos(transacciones)
    total_ingresos = sum(t.monto for t in ingresos)
    total_egresos = sum(t.monto for t in egresos)
    if total_ingresos == 0:
        return 0.0
    ahorrado = restar(total_ingresos, total_egresos)
    return porcentaje(ahorrado, total_ingresos)


def presupuesto_vs_real(transacciones: List[Transaccion], presupuesto: Presupuesto) -> Tuple[float, float, float]:
    gastado = sum(t.monto for t in transacciones if t.tipo == "egreso" and t.categoria == presupuesto.categoria)
    restante = calcular_presupuesto_restante(presupuesto, gastado)
    usado = porcentaje(gastado, presupuesto.limite) if presupuesto.limite > 0 else 0.0
    return gastado, restante, usado


def balance_por_mes(transacciones: List[Transaccion]) -> Dict[str, float]:
    por_mes: Dict[str, float] = defaultdict(float)
    for t in transacciones:
        clave = t.fecha.strftime("%Y-%m")
        if t.tipo == "ingreso":
            por_mes[clave] = sumar(por_mes[clave], t.monto)
        else:
            por_mes[clave] = restar(por_mes[clave], t.monto)
    return dict(sorted(por_mes.items()))


def progreso_meta(meta: MetaAhorro) -> float:
    if meta.monto_objetivo <= 0:
        return 0.0
    return porcentaje(meta.monto_actual, meta.monto_objetivo)
