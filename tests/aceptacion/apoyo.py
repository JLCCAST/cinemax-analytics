"""Carga de las 5 fuentes y utilidades para las pruebas de aceptación."""

from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, date, datetime, time
from decimal import Decimal
from zoneinfo import ZoneInfo

import pymysql
from bson import Decimal128
from psycopg.rows import dict_row

from cinemax_analytics.fuentes import FUENTES, conectar_mongo, conectar_mysql, conectar_postgres
from cinemax_analytics.generador.promociones import Promocion, cargar_promociones

LIMA = ZoneInfo("America/Lima")
CLASE_FUNCION = "com.cinemax.cartelera.entity.Showtime"
CLASE_PELICULA = "com.cinemax.cartelera.entity.Movie"


def en_lima(utc_sin_zona: datetime) -> datetime:
    """payment_date y created_at se guardan en UTC, sin zona."""
    return utc_sin_zona.replace(tzinfo=UTC).astimezone(LIMA).replace(tzinfo=None)


def decimal_mongo(valor) -> Decimal:
    """El seed guarda Decimal128; cartelera-service, texto ("18.00" o "20")."""
    if isinstance(valor, Decimal128):
        return valor.to_decimal()
    return Decimal(str(valor))


def fecha_mongo(valor: datetime) -> date:
    return valor.astimezone(UTC).date()


def hora_mongo(valor: datetime) -> time:
    """Hora de Lima guardada como si fuera UTC: se toma tal cual."""
    return valor.astimezone(UTC).time().replace(tzinfo=None)


@dataclass
class Datos:
    ventas: list[dict]  # en orden de created_at
    entradas: dict[int, list[dict]]  # por id_transaction, en orden de id_ticket
    lineas: dict[int, list[dict]]  # por id_transaction, en orden de id_detail
    funciones: dict[str, dict]
    peliculas: dict[str, dict]
    generos: dict[str, str]
    clasificaciones: set[str]
    sedes: dict[int, dict]
    salas: dict[int, dict]
    butacas: dict[int, dict]
    productos: dict[int, dict]
    stock: set[tuple[int, int]]  # (id_snack, id_venue)
    usuarios: dict[int, dict]
    promociones: list[Promocion]
    secuencias: list[tuple[str, int, int]]  # (tabla, último valor, id máximo)

    def vendidas_por_funcion(self) -> dict[str, int]:
        vendidas: dict[str, int] = defaultdict(int)
        for lista in self.entradas.values():
            for entrada in lista:
                vendidas[entrada["id_showtime"]] += 1
        return vendidas


def _secuencias(cursor, columnas: list[tuple[str, str]]) -> list[tuple[str, int, int]]:
    resultado = []
    for tabla, columna in columnas:
        fila = cursor.execute(
            f"SELECT pg_sequence_last_value(pg_get_serial_sequence('{tabla}', '{columna}')"
            f"::regclass) AS ultimo, coalesce(max({columna}), 0) AS maximo FROM {tabla}"
        ).fetchone()
        resultado.append((tabla, fila["ultimo"] or 0, fila["maximo"]))
    return resultado


def _facturacion() -> dict:
    with conectar_postgres(FUENTES["facturacion"]) as conexion:
        promociones = cargar_promociones(conexion)
        cursor = conexion.cursor(row_factory=dict_row)
        ventas = cursor.execute(
            "SELECT t.*, s.name_status AS estado FROM sale_transaction t "
            "JOIN transaction_status s USING (id_transaction_status) "
            "ORDER BY t.created_at, t.id_transaction"
        ).fetchall()
        entradas = defaultdict(list)
        for fila in cursor.execute("SELECT * FROM sale_ticket_detail ORDER BY id_ticket"):
            entradas[fila["id_transaction"]].append(fila)
        lineas = defaultdict(list)
        for fila in cursor.execute("SELECT * FROM sale_snack_detail ORDER BY id_detail"):
            lineas[fila["id_transaction"]].append(fila)
        secuencias = _secuencias(
            cursor,
            [
                ("sale_transaction", "id_transaction"),
                ("sale_ticket_detail", "id_ticket"),
                ("sale_snack_detail", "id_detail"),
            ],
        )
    return {
        "ventas": ventas,
        "entradas": entradas,
        "lineas": lineas,
        "promociones": promociones,
        "secuencias": secuencias,
    }


def _usuarios() -> tuple[dict, list]:
    with conectar_postgres(FUENTES["usuarios"]) as conexion:
        cursor = conexion.cursor(row_factory=dict_row)
        filas = cursor.execute(
            "SELECT u.id_user, u.email, u.status, u.id_venue, u.datebirth, r.role_name "
            "FROM user_account u JOIN role r USING (id_role)"
        ).fetchall()
        secuencias = _secuencias(cursor, [("user_account", "id_user")])
    return {f["id_user"]: f for f in filas}, secuencias


def _mysql(nombre: str, consultas: dict[str, str]) -> dict[str, list[dict]]:
    conexion = conectar_mysql(FUENTES[nombre], cursorclass=pymysql.cursors.DictCursor)
    try:
        with conexion.cursor() as cursor:
            resultado = {}
            for clave, consulta in consultas.items():
                cursor.execute(consulta)
                resultado[clave] = list(cursor.fetchall())
            return resultado
    finally:
        conexion.close()


def cargar() -> Datos:
    facturacion = _facturacion()
    usuarios, secuencias_usuarios = _usuarios()
    sucursales = _mysql(
        "sucursales",
        {
            "sedes": "SELECT * FROM venue",
            "salas": "SELECT * FROM room",
            "butacas": "SELECT * FROM seat",
        },
    )
    confiteria = _mysql(
        "confiteria",
        {
            "productos": "SELECT * FROM snack",
            "stock": "SELECT id_snack, id_venue FROM snack_venue_stock",
        },
    )
    db = conectar_mongo()
    return Datos(
        ventas=facturacion["ventas"],
        entradas=facturacion["entradas"],
        lineas=facturacion["lineas"],
        funciones={str(d["_id"]): d for d in db.showtimes.find()},
        peliculas={str(d["_id"]): d for d in db.movies.find()},
        generos={str(d["_id"]): d["nameGenre"] for d in db.genres.find()},
        clasificaciones={str(d["_id"]) for d in db.classifications.find()},
        sedes={f["id_venue"]: f for f in sucursales["sedes"]},
        salas={f["id_room"]: f for f in sucursales["salas"]},
        butacas={f["id_seat"]: f for f in sucursales["butacas"]},
        productos={f["id_snack"]: f for f in confiteria["productos"]},
        stock={(f["id_snack"], f["id_venue"]) for f in confiteria["stock"]},
        usuarios=usuarios,
        promociones=facturacion["promociones"],
        secuencias=facturacion["secuencias"] + secuencias_usuarios,
    )


def primeros(lista: list, n: int = 5) -> list:
    """Para los mensajes de error: unos pocos ejemplos, no miles."""
    return lista[:n]
