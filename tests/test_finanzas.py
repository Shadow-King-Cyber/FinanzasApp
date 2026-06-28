import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from datetime import datetime, timedelta, date

from src.core.calculadora import sumar, restar, multiplicar, dividir, porcentaje, promedio
from src.core.finanzas import (
    calcular_balance,
    calcular_balance_desde_lista,
    calcular_presupuesto_restante,
    aplicar_transaccion,
    resumen_por_categoria,
    top_categorias,
    filtrar_por_fecha,
    calcular_promedio_mensual,
    calcular_ahorro,
    presupuesto_vs_real,
    balance_por_mes,
    progreso_meta,
)
from src.data.modelos import Transaccion, Cuenta, Presupuesto, MetaAhorro


# ======================================================================
#  Calculadora
# ======================================================================

class TestCalculadora:
    def test_sumar(self):
        assert sumar(2, 3) == 5
        assert sumar(-1, 1) == 0
        assert sumar(0.1, 0.2) == pytest.approx(0.3)

    def test_restar(self):
        assert restar(10, 4) == 6
        assert restar(0, 5) == -5

    def test_multiplicar(self):
        assert multiplicar(3, 4) == 12
        assert multiplicar(-2, 5) == -10

    def test_dividir(self):
        assert dividir(10, 2) == 5
        assert dividir(7, 2) == 3.5

    def test_dividir_entre_cero(self):
        with pytest.raises(ZeroDivisionError):
            dividir(5, 0)

    def test_validacion_tipo(self):
        with pytest.raises(TypeError):
            sumar("a", 2)
        with pytest.raises(TypeError):
            restar(1, None)

    def test_validacion_infinito(self):
        with pytest.raises(ValueError):
            sumar(float("inf"), 1)

    def test_porcentaje(self):
        assert porcentaje(25, 100) == 25.0
        assert porcentaje(50, 200) == 25.0
        assert porcentaje(0, 100) == 0.0

    def test_porcentaje_total_cero(self):
        with pytest.raises(ZeroDivisionError):
            porcentaje(10, 0)

    def test_promedio(self):
        assert promedio(2, 4, 6) == 4.0
        assert promedio(10, 20) == 15.0
        assert promedio(5,) == 5.0

    def test_promedio_sin_valores(self):
        with pytest.raises(ValueError):
            promedio()


# ======================================================================
#  Finanzas
# ======================================================================

class TestFinanzas:
    def test_calcular_balance(self):
        ingresos = [Transaccion("ingreso", 1000, "Sueldo", "Salario")]
        egresos = [Transaccion("egreso", 300, "Comida", "Alimentación")]
        assert calcular_balance(ingresos, egresos) == 700

    def test_calcular_balance_vacio(self):
        assert calcular_balance([], []) == 0

    def test_calcular_balance_desde_lista(self):
        ts = [
            Transaccion("ingreso", 1000, "Sueldo", "Salario"),
            Transaccion("egreso", 300, "Comida", "Alimentación"),
        ]
        assert calcular_balance_desde_lista(ts) == 700

    def test_presupuesto_restante(self):
        p = Presupuesto("Alimentación", 500)
        assert calcular_presupuesto_restante(p, 300) == 200
        assert calcular_presupuesto_restante(p, 600) == -100

    def test_aplicar_transaccion_ingreso(self):
        cuenta = Cuenta("Principal", 100)
        t = Transaccion("ingreso", 50, "Pago", "Salario")
        aplicar_transaccion(cuenta, t)
        assert cuenta.balance == 150

    def test_aplicar_transaccion_egreso(self):
        cuenta = Cuenta("Principal", 100)
        t = Transaccion("egreso", 30, "Compra", "Alimentación")
        aplicar_transaccion(cuenta, t)
        assert cuenta.balance == 70

    def test_aplicar_transaccion_invalida(self):
        cuenta = Cuenta("Principal", 0)
        t = Transaccion("invalido", 10, "Test", "Otros")
        with pytest.raises(ValueError):
            aplicar_transaccion(cuenta, t)

    def test_resumen_por_categoria(self):
        transacciones = [
            Transaccion("ingreso", 1000, "Sueldo", "Salario"),
            Transaccion("egreso", 200, "Comida", "Alimentación"),
            Transaccion("egreso", 150, "Cena", "Alimentación"),
            Transaccion("ingreso", 500, "Freelo", "Freelance"),
        ]
        resumen = resumen_por_categoria(transacciones)
        assert resumen["Salario"]["ingreso"] == 1000
        assert resumen["Alimentación"]["egreso"] == 350
        assert resumen["Freelance"]["ingreso"] == 500

    def test_top_categorias(self):
        ts = [
            Transaccion("egreso", 500, "Renta", "Vivienda"),
            Transaccion("egreso", 300, "Comida", "Alimentación"),
            Transaccion("egreso", 200, "Gasolina", "Transporte"),
            Transaccion("egreso", 100, "Netflix", "Entretenimiento"),
        ]
        top = top_categorias(ts, tipo="egreso", limite=2)
        assert len(top) == 2
        assert top[0][0] == "Vivienda"
        assert top[0][1] == 500

    def test_top_categorias_ingresos(self):
        ts = [
            Transaccion("ingreso", 2000, "Sueldo", "Salario"),
            Transaccion("ingreso", 500, "Freelo", "Freelance"),
        ]
        top = top_categorias(ts, tipo="ingreso")
        assert len(top) == 2
        assert top[0][0] == "Salario"

    def test_filtrar_por_fecha(self):
        hoy = datetime.now()
        ayer = hoy - timedelta(days=1)
        manana = hoy + timedelta(days=1)

        t1 = Transaccion("ingreso", 100, "Ayer", "Salario", fecha=ayer)
        t2 = Transaccion("ingreso", 200, "Hoy", "Salario", fecha=hoy)
        t3 = Transaccion("ingreso", 300, "Mañana", "Salario", fecha=manana)

        filtradas = filtrar_por_fecha([t1, t2, t3], ayer, hoy)
        assert len(filtradas) == 2
        assert t1 in filtradas
        assert t2 in filtradas
        assert t3 not in filtradas

    def test_promedio_mensual(self):
        ts = [
            Transaccion("egreso", 600, "Renta", "Vivienda",
                        fecha=datetime(2024, 1, 5)),
            Transaccion("egreso", 600, "Renta", "Vivienda",
                        fecha=datetime(2024, 2, 5)),
        ]
        assert calcular_promedio_mensual(ts) == 600.0

    def test_promedio_mensual_vacio(self):
        assert calcular_promedio_mensual([]) == 0.0

    def test_calcular_ahorro(self):
        ts = [
            Transaccion("ingreso", 3000, "Sueldo", "Salario"),
            Transaccion("egreso", 1000, "Gastos", "Vivienda"),
            Transaccion("egreso", 500, "Comida", "Alimentación"),
        ]
        assert calcular_ahorro(ts) == pytest.approx(50.0)

    def test_calcular_ahorro_sin_ingresos(self):
        assert calcular_ahorro([]) == 0.0

    def test_presupuesto_vs_real(self):
        p = Presupuesto("Alimentación", 1000)
        ts = [
            Transaccion("egreso", 300, "Comida", "Alimentación"),
            Transaccion("egreso", 200, "Cena", "Alimentación"),
        ]
        gastado, restante, usado = presupuesto_vs_real(ts, p)
        assert gastado == 500
        assert restante == 500
        assert usado == 50.0

    def test_balance_por_mes(self):
        ts = [
            Transaccion("ingreso", 3000, "Sueldo", "Salario",
                        fecha=datetime(2024, 1, 1)),
            Transaccion("egreso", 1000, "Renta", "Vivienda",
                        fecha=datetime(2024, 1, 5)),
            Transaccion("ingreso", 3000, "Sueldo", "Salario",
                        fecha=datetime(2024, 2, 1)),
        ]
        por_mes = balance_por_mes(ts)
        assert por_mes["2024-01"] == 2000
        assert por_mes["2024-02"] == 3000

    def test_progreso_meta(self):
        meta = MetaAhorro("Viaje", 10000, 2500)
        assert progreso_meta(meta) == 25.0

    def test_progreso_meta_objetivo_cero(self):
        meta = MetaAhorro("Test", 0, 0)
        assert progreso_meta(meta) == 0.0
