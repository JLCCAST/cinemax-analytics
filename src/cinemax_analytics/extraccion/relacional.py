"""Extracción de las fuentes PostgreSQL (usuarios, facturación) y MySQL (sucursales, confitería)."""

from datetime import timedelta

import psycopg
import pymysql
from psycopg import sql

from cinemax_analytics.extraccion import COLUMNAS_EXCLUIDAS, TABLAS_EXCLUIDAS
from cinemax_analytics.extraccion.raw import Columnas, copiar_a

ENTEROS_MYSQL = {
    "tinyint": "smallint",
    "smallint": "smallint",
    "mediumint": "integer",
    "int": "integer",
    "bigint": "bigint",
}
TEXTOS_MYSQL = {"char", "varchar", "tinytext", "text", "mediumtext", "longtext", "enum", "set"}


def tipo_postgres(tipo_mysql: str, precision, escala, tipo_columna: str) -> str:
    """Tipo de PostgreSQL equivalente, escrito como lo devuelve format_type()."""
    tipo = tipo_mysql.lower()
    if tipo in ENTEROS_MYSQL:
        if "unsigned" in tipo_columna.lower():
            return "numeric(20,0)" if tipo == "bigint" else "bigint"
        return ENTEROS_MYSQL[tipo]
    if tipo == "decimal":
        return f"numeric({precision},{escala})"
    if tipo in TEXTOS_MYSQL:
        return "text"
    equivalentes = {
        "float": "real",
        "double": "double precision",
        "date": "date",
        "datetime": "timestamp without time zone",
        "timestamp": "timestamp without time zone",
        "time": "time without time zone",
        "year": "integer",
        "bit": "integer",
        "json": "jsonb",
    }
    if tipo not in equivalentes:
        raise ValueError(f"Tipo de MySQL sin equivalente: {tipo_columna}")
    return equivalentes[tipo]


def valor_mysql(valor):
    """PyMySQL devuelve TIME como timedelta y BIT como bytes."""
    if isinstance(valor, timedelta):
        segundos = int(valor.total_seconds())
        return f"{segundos // 3600:02d}:{segundos % 3600 // 60:02d}:{segundos % 60:02d}"
    if isinstance(valor, bytes):
        return int.from_bytes(valor, "big")
    return valor


def _sin_excluidas(fuente: str, tabla: str, columnas: Columnas) -> Columnas:
    excluidas = COLUMNAS_EXCLUIDAS.get((fuente, tabla), set())
    return [(nombre, tipo) for nombre, tipo in columnas if nombre not in excluidas]


# ---- PostgreSQL ------------------------------------------------------------------------


def tablas_postgres(origen: psycopg.Connection) -> list[str]:
    filas = origen.execute(
        "SELECT table_name FROM information_schema.tables "
        "WHERE table_schema = 'public' AND table_type = 'BASE TABLE' ORDER BY table_name"
    ).fetchall()
    return [tabla for (tabla,) in filas if tabla not in TABLAS_EXCLUIDAS]


def columnas_postgres(origen: psycopg.Connection, fuente: str, tabla: str) -> Columnas:
    filas = origen.execute(
        """
        SELECT a.attname, format_type(a.atttypid, a.atttypmod)
        FROM pg_attribute a
        WHERE a.attrelid = to_regclass(%s) AND a.attnum > 0 AND NOT a.attisdropped
        ORDER BY a.attnum
        """,
        (f"public.{tabla}",),
    ).fetchall()
    return _sin_excluidas(fuente, tabla, [(nombre, tipo) for nombre, tipo in filas])


def copiar_postgres(origen, dwh, tabla: str, destino: str, columnas: Columnas) -> int:
    nombres = [nombre for nombre, _ in columnas]
    filas = origen.execute(
        sql.SQL("SELECT count(*) FROM {}").format(sql.Identifier(tabla))
    ).fetchone()[0]
    consulta = sql.SQL("COPY (SELECT {} FROM {}) TO STDOUT").format(
        sql.SQL(", ").join(map(sql.Identifier, nombres)), sql.Identifier(tabla)
    )
    # Mismos tipos en los dos lados: el formato de texto de COPY pasa tal cual.
    with origen.cursor().copy(consulta) as entrada, copiar_a(dwh, destino, nombres) as salida:
        for bloque in entrada:
            salida.write(bloque)
    return filas


# ---- MySQL -----------------------------------------------------------------------------


def tablas_mysql(origen: pymysql.Connection) -> list[str]:
    with origen.cursor() as cursor:
        cursor.execute(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = DATABASE() AND table_type = 'BASE TABLE' ORDER BY table_name"
        )
        return [tabla for (tabla,) in cursor.fetchall() if tabla not in TABLAS_EXCLUIDAS]


def columnas_mysql(origen: pymysql.Connection, fuente: str, tabla: str) -> Columnas:
    with origen.cursor() as cursor:
        cursor.execute(
            "SELECT column_name, data_type, numeric_precision, numeric_scale, column_type "
            "FROM information_schema.columns "
            "WHERE table_schema = DATABASE() AND table_name = %s ORDER BY ordinal_position",
            (tabla,),
        )
        columnas = [
            (nombre, tipo_postgres(tipo, precision, escala, tipo_columna))
            for nombre, tipo, precision, escala, tipo_columna in cursor.fetchall()
        ]
    return _sin_excluidas(fuente, tabla, columnas)


def copiar_mysql(
    origen: pymysql.Connection, dwh, tabla: str, destino: str, columnas: Columnas
) -> int:
    nombres = [nombre for nombre, _ in columnas]
    lista = ", ".join(f"`{nombre}`" for nombre in nombres)
    with origen.cursor() as cursor:
        cursor.execute(f"SELECT count(*) FROM `{tabla}`")
        filas = cursor.fetchone()[0]
    with (
        origen.cursor(pymysql.cursors.SSCursor) as cursor,
        copiar_a(dwh, destino, nombres) as salida,
    ):
        cursor.execute(f"SELECT {lista} FROM `{tabla}`")
        for fila in cursor:
            salida.write_row([valor_mysql(valor) for valor in fila])
    return filas
