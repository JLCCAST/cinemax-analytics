"""Los patrones de demanda que el generador programa tienen que verse en los datos.

Las tolerancias son amplias: solo prueban que cada patrón existe y va en la
dirección correcta. Medirlo bien le toca al dashboard.
"""

from collections import Counter, defaultdict
from datetime import timedelta
from statistics import mean

from apoyo import en_lima, fecha_mongo

COMBOS = 2


def _funciones_pasadas(datos) -> list[tuple[str, dict]]:
    ultima = en_lima(max(v["payment_date"] for v in datos.ventas)).date()
    return [
        (clave, f)
        for clave, f in datos.funciones.items()
        if "_class" in f and f["status"] == "Programada" and fecha_mongo(f["showDate"]) <= ultima
    ]


def test_ocupacion_media(datos):
    vendidas = datos.vendidas_por_funcion()
    ocupacion = mean(
        vendidas.get(clave, 0) / datos.salas[f["idRoom"]]["capacity"]
        for clave, f in _funciones_pasadas(datos)
    )
    assert 0.12 <= ocupacion <= 0.45, f"Ocupación media {ocupacion:.1%}"


def test_fin_de_semana_vende_mas(datos):
    vendidas = datos.vendidas_por_funcion()
    por_dia = defaultdict(list)
    for clave, f in _funciones_pasadas(datos):
        por_dia[fecha_mongo(f["showDate"]).isoweekday() >= 5].append(vendidas.get(clave, 0))
    razon = mean(por_dia[True]) / mean(por_dia[False])
    assert razon >= 1.25, f"Viernes a domingo / lunes a jueves = {razon:.2f}"


def test_las_peliculas_caen_semana_a_semana(datos):
    vendidas = datos.vendidas_por_funcion()
    por_semana = defaultdict(list)
    for clave, f in _funciones_pasadas(datos):
        pelicula = datos.peliculas[f["movieId"]]
        semana = (fecha_mongo(f["showDate"]) - fecha_mongo(pelicula["releaseDate"])).days // 7
        capacidad = datos.salas[f["idRoom"]]["capacity"]
        por_semana[(f["movieId"], semana)].append(vendidas.get(clave, 0) / capacidad)
    comparables = [
        mean(por_semana[(p, 0)]) > mean(por_semana[(p, 2)])
        for p in {p for p, _ in por_semana}
        if len(por_semana[(p, 0)]) >= 10 and len(por_semana[(p, 2)]) >= 10
    ]
    assert len(comparables) >= 10, f"Solo {len(comparables)} películas con 3 semanas en cartelera"
    assert sum(comparables) / len(comparables) >= 0.75


def test_mas_ninos_en_animacion(datos):
    animacion = {g for g, nombre in datos.generos.items() if nombre == "Animación"}
    conteo = defaultdict(Counter)
    for lista in datos.entradas.values():
        for e in lista:
            pelicula = datos.peliculas[datos.funciones[e["id_showtime"]]["movieId"]]
            es_animacion = bool(animacion & set(pelicula.get("genreIds", [])))
            conteo[es_animacion][e["fare_category"] == "NINO"] += 1
    proporcion = {k: c[True] / (c[True] + c[False]) for k, c in conteo.items()}
    assert proporcion[True] >= 2 * proporcion[False], proporcion


def test_promociones_en_uso(datos):
    nombres = {p.id: p.nombre for p in datos.promociones}
    usadas = Counter(nombres[v["id_promotion"]] for v in datos.ventas if v["id_promotion"])
    proporcion = sum(usadas.values()) / len(datos.ventas)
    assert 0.10 <= proporcion <= 0.65, f"{proporcion:.1%} de ventas con promoción"
    for nombre in ("Miércoles de cine", "Martes 2x1", "Matiné", "Combo + película"):
        assert usadas[nombre] > 0, f"Nunca se aplicó {nombre}"
    assert usadas["Cumpleañero"] >= 10, usadas
    assert usadas["Cupón de la app"] >= 10, usadas


def test_combos_en_grupos(datos):
    con_combo = defaultdict(list)
    for v in datos.ventas:
        entradas = len(datos.entradas.get(v["id_transaction"], []))
        if entradas == 0:
            continue
        combo = any(
            datos.productos[ln["id_snack"]]["id_snack_category"] == COMBOS
            for ln in datos.lineas.get(v["id_transaction"], [])
        )
        con_combo[min(entradas, 3)].append(combo)
    assert mean(con_combo[3]) > mean(con_combo[1]), {
        k: round(mean(v), 3) for k, v in con_combo.items()
    }


def test_frecuencia_desigual_de_clientes(datos):
    compras = Counter(v["id_user"] for v in datos.ventas)
    una_vez = sum(1 for n in compras.values() if n == 1) / len(compras)
    mayores = sorted(compras.values(), reverse=True)[: max(1, len(compras) // 10)]
    assert una_vez >= 0.30, f"Solo {una_vez:.0%} compró una vez"
    assert sum(mayores) / len(datos.ventas) >= 0.30, "El 10 % más fiel compra menos del 30 %"


def test_ventas_todos_los_dias_y_en_horas_razonables(datos):
    momentos = [en_lima(v["payment_date"]) for v in datos.ventas]
    dias = {m.date() for m in momentos}
    primero, ultimo = min(dias), max(dias)
    faltan = [
        primero + timedelta(days=i)
        for i in range((ultimo - primero).days + 1)
        if primero + timedelta(days=i) not in dias
    ]
    assert not faltan, faltan[:5]
    madrugada = sum(1 for m in momentos if 1 <= m.hour < 7) / len(momentos)
    assert madrugada < 0.02, f"{madrugada:.1%} de compras entre la 1 y las 7"
