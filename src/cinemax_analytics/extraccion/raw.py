"""Tablas del esquema raw y registro de cada carga."""

from datetime import datetime

import psycopg
from psycopg import sql

Columnas = list[tuple[str, str]]  # (nombre, tipo de PostgreSQL)

META = ("_fuente", "_extraido_en")


def preparar_registro(dwh: psycopg.Connection) -> None:
    dwh.execute(
        """
        CREATE TABLE IF NOT EXISTS raw._cargas (
            corrida      timestamptz NOT NULL,
            fuente       text        NOT NULL,
            tabla_origen text        NOT NULL,
            tabla_raw    text        NOT NULL,
            filas_origen bigint      NOT NULL,
            filas_raw    bigint      NOT NULL,
            cargado_en   timestamptz NOT NULL DEFAULT clock_timestamp(),
            PRIMARY KEY (corrida, tabla_raw)
        )
        """
    )


def columnas_actuales(dwh: psycopg.Connection, tabla: str) -> Columnas:
    filas = dwh.execute(
        """
        SELECT a.attname, format_type(a.atttypid, a.atttypmod)
        FROM pg_attribute a
        WHERE a.attrelid = to_regclass(%s) AND a.attnum > 0 AND NOT a.attisdropped
          AND a.attname <> ALL(%s)
        ORDER BY a.attnum
        """,
        (f"raw.{tabla}", list(META)),
    ).fetchall()
    return [(nombre, tipo) for nombre, tipo in filas]


def preparar(dwh: psycopg.Connection, tabla: str, columnas: Columnas, fuente: str) -> None:
    """Deja raw.<tabla> vacía. Si la fuente cambió de columnas, la vuelve a crear."""
    destino = sql.Identifier("raw", tabla)
    if columnas_actuales(dwh, tabla) != columnas:
        # CASCADE borra las vistas de staging que dependen de ella; dbt las recrea.
        dwh.execute(sql.SQL("DROP TABLE IF EXISTS {} CASCADE").format(destino))
        definicion = [
            sql.SQL("{} {}").format(sql.Identifier(nombre), sql.SQL(tipo))
            for nombre, tipo in columnas
        ]
        definicion += [
            sql.SQL("_fuente text NOT NULL DEFAULT {}").format(sql.Literal(fuente)),
            sql.SQL("_extraido_en timestamptz NOT NULL DEFAULT now()"),
        ]
        dwh.execute(sql.SQL("CREATE TABLE {} ({})").format(destino, sql.SQL(", ").join(definicion)))
    else:
        dwh.execute(sql.SQL("TRUNCATE {}").format(destino))


def contar(dwh: psycopg.Connection, tabla: str) -> int:
    return dwh.execute(
        sql.SQL("SELECT count(*) FROM {}").format(sql.Identifier("raw", tabla))
    ).fetchone()[0]


def copiar_a(dwh: psycopg.Connection, tabla: str, nombres: list[str]):
    """Abre un COPY ... FROM STDIN hacia raw.<tabla> con esas columnas."""
    return dwh.cursor().copy(
        sql.SQL("COPY {} ({}) FROM STDIN").format(
            sql.Identifier("raw", tabla),
            sql.SQL(", ").join(map(sql.Identifier, nombres)),
        )
    )


def registrar(
    dwh: psycopg.Connection,
    corrida: datetime,
    fuente: str,
    tabla_origen: str,
    tabla_raw: str,
    filas_origen: int,
    filas_raw: int,
) -> None:
    dwh.execute(
        "INSERT INTO raw._cargas (corrida, fuente, tabla_origen, tabla_raw, filas_origen, filas_raw) "
        "VALUES (%s, %s, %s, %s, %s, %s)",
        (corrida, fuente, tabla_origen, tabla_raw, filas_origen, filas_raw),
    )
