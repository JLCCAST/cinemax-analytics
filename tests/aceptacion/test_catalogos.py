"""Funciones, películas, salas y clientes con la forma que les da CineMax."""

import itertools
from collections import Counter, defaultdict
from datetime import UTC, date, datetime, time

from apoyo import (
    CLASE_FUNCION,
    CLASE_PELICULA,
    decimal_mongo,
    en_lima,
    fecha_mongo,
    hora_mongo,
    primeros,
)
from bson import Decimal128

CAMPOS_FUNCION = {
    "_id", "_class", "showDate", "startTime", "endTime", "languageFormat", "baseTicketPrice",
    "availableSeats", "status", "movieId", "idRoom", "idVenue",
}  # fmt: skip
CAMPOS_PELICULA = {
    "_id", "_class", "titleMovie", "synopsis", "durationMinutes", "posterUrl", "director",
    "releaseDate", "status", "createdAt", "isActive", "premiereWeek", "genreIds",
    "classificationId",
}  # fmt: skip


def generadas(coleccion: dict) -> list[dict]:
    """Lo que escribió el generador lleva _class, como lo que guarda el servicio."""
    return [d for d in coleccion.values() if "_class" in d]


def test_funciones_del_seed_intactas(datos):
    seed = [f for f in datos.funciones.values() if "_class" not in f]
    assert len(seed) == 8
    assert all(isinstance(f["baseTicketPrice"], Decimal128) for f in seed)


def test_funciones_con_la_forma_del_servicio(datos):
    funciones = generadas(datos.funciones)
    assert funciones, "No hay funciones generadas"
    malas = []
    for f in funciones:
        clave = str(f["_id"])
        campos = set(f) - {"soldSeats"}
        if campos != CAMPOS_FUNCION:
            malas.append((clave, "campos", CAMPOS_FUNCION ^ campos))
            continue
        sala = datos.salas.get(f["idRoom"])
        pelicula = datos.peliculas.get(f["movieId"])
        inicio, fin = hora_mongo(f["startTime"]), hora_mongo(f["endTime"])
        # El servicio guarda las horas con la fecha del día en que se creó la función.
        creada = fecha_mongo(f["startTime"])
        dia = fecha_mongo(f["showDate"])
        problemas = {
            "_class": f["_class"] != CLASE_FUNCION,
            "precio como texto": not isinstance(f["baseTicketPrice"], str),
            "precio": not 8 <= decimal_mongo(f["baseTicketPrice"]) <= 40,
            "sala y sede": sala is None or sala["id_venue"] != f["idVenue"],
            "estado": f["status"] not in {"Programada", "Cancelada"},
            "idioma": f["languageFormat"] not in {"Doblada", "Subtitulada"},
            "película": pelicula is None,
            "horario": not time(10, 0) <= inicio < fin,
            "fecha a medianoche UTC": f["showDate"].astimezone(UTC).time() != time(0),
            "creada antes de la función": not creada < dia or fecha_mongo(f["endTime"]) != creada,
            "después del estreno": pelicula is not None
            and dia < fecha_mongo(pelicula["releaseDate"]),
            "dura lo que la película": pelicula is not None
            and _minutos(inicio, fin) < pelicula["durationMinutes"],
        }
        malas += [(clave, nombre) for nombre, falla in problemas.items() if falla]
    assert not malas, primeros(malas)


def test_sin_cruces_en_la_misma_sala(datos):
    por_sala = defaultdict(list)
    for f in datos.funciones.values():
        if f["status"] != "Cancelada":
            clave = (f.get("idRoom") or f.get("roomId"), fecha_mongo(f["showDate"]))
            por_sala[clave].append(
                (hora_mongo(f["startTime"]), hora_mongo(f["endTime"]), str(f["_id"]))
            )
    cruces = []
    for clave, lista in por_sala.items():
        lista.sort()
        for anterior, siguiente in itertools.pairwise(lista):
            if siguiente[0] < anterior[1]:
                cruces.append((clave, anterior[2], siguiente[2]))
    assert not cruces, primeros(cruces)


def test_butacas_vendidas_y_disponibles(datos):
    vendidas = datos.vendidas_por_funcion()
    malas = []
    for clave, f in datos.funciones.items():
        n = vendidas.get(clave, 0)
        if "_class" not in f and n == 0:
            continue
        capacidad = datos.salas[f["idRoom"]]["capacity"]
        if (
            (f.get("soldSeats") or 0) != n
            or f["availableSeats"] != capacidad - n
            or (f["status"] == "Cancelada" and n > 0)
        ):
            malas.append((clave, n, f.get("soldSeats"), f["availableSeats"], capacidad))
    assert not malas, primeros(malas)


def test_cada_entrada_es_una_butaca_activa_de_su_sala(datos):
    malas = []
    for lista in datos.entradas.values():
        for e in lista:
            butaca = datos.butacas.get(e["id_seat"])
            funcion = datos.funciones[e["id_showtime"]]
            if (
                butaca is None
                or butaca["id_room"] != funcion["idRoom"]
                or butaca["status"] != "ACTIVO"
            ):
                malas.append(e["id_ticket"])
    assert not malas, primeros(malas)


def test_no_se_vende_antes_de_crear_la_funcion(datos):
    malas = []
    for v in datos.ventas:
        funcion = datos.funciones.get(v["id_showtime"]) if v["id_showtime"] else None
        generada = funcion is not None and "_class" in funcion
        if generada and en_lima(v["payment_date"]).date() < fecha_mongo(funcion["startTime"]):
            malas.append(v["id_transaction"])
    assert not malas, primeros(malas)


def test_peliculas_generadas(datos):
    peliculas = generadas(datos.peliculas)
    assert len(peliculas) >= 30, f"Solo {len(peliculas)} películas generadas"
    malas = []
    for p in peliculas:
        clave = str(p["_id"])
        if set(p) != CAMPOS_PELICULA:
            malas.append((clave, "campos", CAMPOS_PELICULA ^ set(p)))
            continue
        estreno = fecha_mongo(p["releaseDate"])
        problemas = {
            "_class": p["_class"] != CLASE_PELICULA,
            "estreno en jueves": estreno.isoweekday() != 4,
            "duración": not 80 <= p["durationMinutes"] <= 190,
            "géneros": not p["genreIds"] or not set(p["genreIds"]) <= set(datos.generos),
            "clasificación": p["classificationId"] not in datos.clasificaciones,
            "estado": p["status"] not in {"Cartelera", "Estreno", "Preventa"},
            "creada antes del estreno": not fecha_mongo(p["createdAt"]) < estreno,
        }
        malas += [(clave, nombre) for nombre, falla in problemas.items() if falla]
    titulos = Counter(p["titleMovie"] for p in datos.peliculas.values())
    malas += [("título repetido", t) for t, n in titulos.items() if n > 1]
    assert not malas, primeros(malas)


def test_sedes_y_salas(datos):
    assert len(datos.sedes) >= 3, "Se esperaban sedes nuevas"
    activas = Counter(b["id_room"] for b in datos.butacas.values() if b["status"] == "ACTIVO")
    codigos = Counter(
        (b["id_room"], b["row_name"], b["column_number"]) for b in datos.butacas.values()
    )
    malas = [
        (s["id_room"], "capacidad")
        for s in datos.salas.values()
        if s["capacity"] != activas[s["id_room"]]
    ]
    malas += [(clave, "butaca repetida") for clave, n in codigos.items() if n > 1]
    salas_por_sede = Counter(s["id_venue"] for s in datos.salas.values())
    malas += [(sede, "sin salas") for sede in datos.sedes if salas_por_sede[sede] == 0]
    assert not malas, primeros(malas)
    assert any(b["id_seat_type"] == 2 for b in datos.butacas.values()), (
        "Sin butacas para silla de ruedas"
    )


def test_clientes_sinteticos(datos):
    clientes = [u for u in datos.usuarios.values() if u["role_name"] == "CLIENTE"]
    assert len(clientes) >= 5000, f"Solo {len(clientes)} clientes"
    malos = [
        c["id_user"]
        for c in clientes
        if c["status"] != "Activo" or c["id_venue"] is not None or not c["email"].endswith(".test")
    ]
    assert not malos, primeros(malos)
    nacimientos = [c["datebirth"] for c in clientes if c["datebirth"]]
    assert len(nacimientos) >= 0.95 * len(clientes)
    referencia = date(2026, 12, 31)
    fuera = [n for n in nacimientos if not 10 <= (referencia - n).days / 365.25 <= 90]
    assert not fuera, primeros(fuera)


def _minutos(inicio: time, fin: time) -> int:
    hoy = date(2000, 1, 1)
    return int((datetime.combine(hoy, fin) - datetime.combine(hoy, inicio)).total_seconds() // 60)
