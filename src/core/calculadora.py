import math


def _validar_numeros(*args):
    for arg in args:
        if not isinstance(arg, (int, float)):
            raise TypeError(f"Se esperaba un número, se recibió {type(arg).__name__}")
        if math.isinf(arg) or math.isnan(arg):
            raise ValueError("No se permiten valores infinitos o NaN")


def sumar(a, b):
    _validar_numeros(a, b)
    return a + b


def restar(a, b):
    _validar_numeros(a, b)
    return a - b


def multiplicar(a, b):
    _validar_numeros(a, b)
    return a * b


def dividir(a, b):
    _validar_numeros(a, b)
    if b == 0:
        raise ZeroDivisionError("No se puede dividir entre cero")
    return a / b


def porcentaje(valor, total):
    _validar_numeros(valor, total)
    if total == 0:
        raise ZeroDivisionError("El total no puede ser cero para calcular porcentaje")
    return dividir(multiplicar(valor, 100), total)


def promedio(*valores):
    if not valores:
        raise ValueError("Se requiere al menos un valor")
    for v in valores:
        _validar_numeros(v)
    return dividir(sum(valores), len(valores))
