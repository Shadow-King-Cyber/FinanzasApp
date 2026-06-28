import tkinter as tk
from tkinter import ttk
from datetime import datetime
from typing import List, Tuple


COLORES = {
    "ingreso": "#2ecc71",
    "egreso": "#e74c3c",
    "fondo": "#f8f9fa",
    "borde": "#dee2e6",
    "texto": "#212529",
    "accent": "#0078d4",
    "warning": "#f39c12",
    "paleta": ["#3498db", "#e74c3c", "#2ecc71", "#f39c12", "#9b59b6",
               "#1abc9c", "#e67e22", "#34495e", "#16a085", "#c0392b",
               "#2980b9", "#8e44ad", "#f1c40f", "#2c3e50", "#d35400"],
}


def dibujar_grafico_barras(canvas: tk.Canvas, datos: List[Tuple[str, float, float]],
                           titulo: str = "", ancho: int = 600, alto: int = 300) -> None:
    canvas.delete("all")
    if not datos:
        canvas.create_text(ancho // 2, alto // 2, text="Sin datos", fill=COLORES["texto"])
        return

    margen_izq, margen_der, margen_sup, margen_inf = 60, 20, 40, 50
    area_ancho = ancho - margen_izq - margen_der
    area_alto = alto - margen_sup - margen_inf

    max_val = max(max(d[1], d[2]) for d in datos) * 1.15 or 1

    if titulo:
        canvas.create_text(ancho // 2, 16, text=titulo, fill=COLORES["texto"],
                           font=("Segoe UI", 11, "bold"))

    barras_por_grupo = 2
    espacio_grupo = area_ancho / len(datos)
    ancho_barra = (espacio_grupo * 0.7) / barras_por_grupo

    for i, (label, val1, val2) in enumerate(datos):
        x_centro = margen_izq + espacio_grupo * i + espacio_grupo / 2

        h1 = (val1 / max_val) * area_alto
        x1 = x_centro - ancho_barra - 1
        y1 = margen_sup + area_alto - h1
        canvas.create_rectangle(x1, y1, x1 + ancho_barra, margen_sup + area_alto,
                                fill=COLORES["ingreso"], outline="", width=0)
        canvas.create_text(x1 + ancho_barra / 2, y1 - 8, text=f"${val1:.0f}",
                           fill=COLORES["ingreso"], font=("Segoe UI", 7), anchor=tk.S)

        h2 = (val2 / max_val) * area_alto
        x2 = x_centro + 1
        y2 = margen_sup + area_alto - h2
        canvas.create_rectangle(x2, y2, x2 + ancho_barra, margen_sup + area_alto,
                                fill=COLORES["egreso"], outline="", width=0)
        canvas.create_text(x2 + ancho_barra / 2, y2 - 8, text=f"${val2:.0f}",
                           fill=COLORES["egreso"], font=("Segoe UI", 7), anchor=tk.S)

        canvas.create_text(x_centro, margen_sup + area_alto + 12, text=label,
                           fill=COLORES["texto"], font=("Segoe UI", 8), anchor=tk.N)

    canvas.create_text(margen_izq + 20, margen_sup + 8, text="Ingreso",
                       fill=COLORES["ingreso"], font=("Segoe UI", 8, "bold"), anchor=tk.W)
    canvas.create_text(margen_izq + 20, margen_sup + 22, text="Egreso",
                       fill=COLORES["egreso"], font=("Segoe UI", 8, "bold"), anchor=tk.W)


def dibujar_grafico_pastel(canvas: tk.Canvas, datos: List[Tuple[str, float]],
                           titulo: str = "", ancho: int = 400, alto: int = 300) -> Tuple[int, int]:
    canvas.delete("all")
    if not datos:
        canvas.create_text(ancho // 2, alto // 2, text="Sin datos", fill=COLORES["texto"])
        return ancho // 2, alto // 2

    total = sum(d[1] for d in datos)
    if total == 0:
        canvas.create_text(ancho // 2, alto // 2, text="Sin datos", fill=COLORES["texto"])
        return ancho // 2, alto // 2

    if titulo:
        canvas.create_text(ancho // 2, 14, text=titulo, fill=COLORES["texto"],
                           font=("Segoe UI", 11, "bold"))

    cx, cy = ancho // 2 - 40, alto // 2 + 10
    radio = min(ancho, alto) // 2 - 40

    angulo_inicio = 0
    leyenda_y = 30

    datos_ord = sorted(datos, key=lambda x: x[1], reverse=True)

    for i, (label, valor) in enumerate(datos_ord):
        angulo = (valor / total) * 360
        if angulo < 0.5:
            continue
        color = COLORES["paleta"][i % len(COLORES["paleta"])]
        canvas.create_arc(cx - radio, cy - radio, cx + radio, cy + radio,
                          start=angulo_inicio, extent=angulo, fill=color, outline="white", width=1)
        angulo_inicio += angulo

        y = leyenda_y + i * 20
        canvas.create_rectangle(ancho - 140, y, ancho - 125, y + 12,
                                fill=color, outline="")
        pct = valor / total * 100
        canvas.create_text(ancho - 120, y + 6, text=f"{label} ({pct:.1f}%)",
                           fill=COLORES["texto"], font=("Segoe UI", 8), anchor=tk.W)

    return cx, cy


def dibujar_grafico_linea(canvas: tk.Canvas, datos: List[Tuple[str, float]],
                          titulo: str = "", ancho: int = 600, alto: int = 250) -> None:
    canvas.delete("all")
    if len(datos) < 2:
        canvas.create_text(ancho // 2, alto // 2, text="Se necesitan al menos 2 puntos",
                           fill=COLORES["texto"])
        return

    margen_izq, margen_der, margen_sup, margen_inf = 50, 20, 35, 45
    area_ancho = ancho - margen_izq - margen_der
    area_alto = alto - margen_sup - margen_inf

    valores = [d[1] for d in datos]
    min_val = min(valores) * 0.9
    max_val = max(valores) * 1.1
    if max_val == min_val:
        max_val = min_val + 1
    rango = max_val - min_val

    if titulo:
        canvas.create_text(ancho // 2, 14, text=titulo, fill=COLORES["texto"],
                           font=("Segoe UI", 11, "bold"))

    paso_x = area_ancho / (len(datos) - 1) if len(datos) > 1 else area_ancho

    puntos = []
    for i, (label, valor) in enumerate(datos):
        x = margen_izq + paso_x * i
        y = margen_sup + area_alto - ((valor - min_val) / rango) * area_alto
        puntos.append((x, y, label, valor))

        canvas.create_oval(x - 3, y - 3, x + 3, y + 3, fill=COLORES["accent"], outline="")
        canvas.create_text(x, margen_sup + area_alto + 12, text=label,
                           fill=COLORES["texto"], font=("Segoe UI", 7), anchor=tk.N)

    for i in range(len(puntos) - 1):
        x1, y1, _, _ = puntos[i]
        x2, y2, _, _ = puntos[i + 1]
        canvas.create_line(x1, y1, x2, y2, fill=COLORES["accent"], width=2, smooth=True)

    for i, (px, py, label, valor) in enumerate(puntos):
        if i % max(1, len(puntos) // 8) == 0:
            canvas.create_text(px, py - 10, text=f"${valor:.0f}",
                               fill=COLORES["accent"], font=("Segoe UI", 7), anchor=tk.S)


def dibujar_calendario_mensual(canvas: tk.Canvas, anio: int, mes: int,
                               montos_por_dia: dict,
                               ancho: int = 600, alto: int = 350) -> None:
    canvas.delete("all")

    import calendar
    cal = calendar.monthcalendar(anio, mes)
    nombre_mes = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
                  "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"][mes - 1]

    canvas.create_text(ancho // 2, 14, text=f"{nombre_mes} {anio}",
                       fill=COLORES["texto"], font=("Segoe UI", 12, "bold"))

    dias_sem = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
    cols, filas = 7, len(cal) + 1
    celda_ancho = ancho // cols
    celda_alto = (alto - 30) // filas

    for i, dia in enumerate(dias_sem):
        x = i * celda_ancho + celda_ancho // 2
        canvas.create_text(x, 36, text=dia, fill=COLORES["texto"],
                           font=("Segoe UI", 9, "bold"))

    for fi, semana in enumerate(cal):
        y = 44 + fi * celda_alto
        for di, dia_num in enumerate(semana):
            x = di * celda_ancho
            if dia_num == 0:
                continue

            monto = montos_por_dia.get(dia_num, 0)
            color = "#f0f0f0"
            txt_color = COLORES["texto"]

            if monto > 0:
                intensidad = min(monto / 500, 0.8)
                color = f"#{int(232 * (1 - intensidad)):02x}{int(245 * (1 - intensidad)):02x}{int(238 * (1 - intensidad)):02x}"

            canvas.create_rectangle(x + 1, y + 1, x + celda_ancho - 1, y + celda_alto - 1,
                                    fill=color, outline=COLORES["borde"], width=1)

            hoy = datetime.now()
            if dia_num == hoy.day and mes == hoy.month and anio == hoy.year:
                canvas.create_rectangle(x + 2, y + 2, x + celda_ancho - 2, y + celda_alto - 2,
                                        outline=COLORES["accent"], width=2)

            canvas.create_text(x + celda_ancho // 2, y + 10, text=str(dia_num),
                               fill=txt_color, font=("Segoe UI", 9))

            if monto > 0:
                s = f"${monto:.0f}" if monto < 1000 else f"${monto / 1000:.1f}K"
                canvas.create_text(x + celda_ancho // 2, y + celda_alto - 8, text=s,
                                   fill="#e74c3c" if monto < 0 else "#2ecc71",
                                   font=("Segoe UI", 7))
