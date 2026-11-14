"""uv run python -m cinemax_analytics.extraccion [--fuente usuarios ...]"""

import argparse
import sys
from datetime import UTC, datetime

import pymysql

from cinemax_analytics.extraccion import mongo, raw, relacional
from cinemax_analytics.fuentes import (
    FUENTES,
    conectar_dwh,
    conectar_mongo,
    conectar_mysql,
    conectar_postgres,
)


def cargar(dwh, corrida, fuente: str, tabla: str, columnas, copiar) -> tuple[str, int, int]:
    destino = f"{fuente}__{tabla}"
    with dwh.transaction():
        raw.preparar(dwh, destino, columnas, fuente)
        filas_origen = copiar(destino)
        filas_raw = raw.contar(dwh, destino)
        raw.registrar(dwh, corrida, fuente, tabla, destino, filas_origen, filas_raw)
    return destino, filas_origen, filas_raw


def extraer(nombre: str, dwh, corrida) -> list[tuple[str, int, int]]:
    fuente = FUENTES[nombre]
    resultados = []
    if fuente.motor == "postgres":
        with conectar_postgres(fuente) as origen:
            for tabla in relacional.tablas_postgres(origen):
                columnas = relacional.columnas_postgres(origen, nombre, tabla)
                resultados.append(
                    cargar(
                        dwh,
                        corrida,
                        nombre,
                        tabla,
                        columnas,
                        lambda destino, t=tabla, c=columnas: relacional.copiar_postgres(
                            origen, dwh, t, destino, c
                        ),
                    )
                )
    elif fuente.motor == "mysql":
        origen: pymysql.Connection = conectar_mysql(fuente)
        try:
            for tabla in relacional.tablas_mysql(origen):
                columnas = relacional.columnas_mysql(origen, nombre, tabla)
                resultados.append(
                    cargar(
                        dwh,
                        corrida,
                        nombre,
                        tabla,
                        columnas,
                        lambda destino, t=tabla, c=columnas: relacional.copiar_mysql(
                            origen, dwh, t, destino, c
                        ),
                    )
                )
        finally:
            origen.close()
    else:
        db = conectar_mongo(fuente)
        for coleccion in mongo.colecciones(db):
            resultados.append(
                cargar(
                    dwh,
                    corrida,
                    nombre,
                    coleccion,
                    mongo.COLUMNAS,
                    lambda destino, c=coleccion: mongo.copiar_coleccion(db, dwh, c, destino),
                )
            )
    return resultados


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m cinemax_analytics.extraccion",
        description="Copia las bases de CineMax al esquema raw del warehouse.",
    )
    parser.add_argument(
        "--fuente",
        choices=list(FUENTES),
        action="append",
        help="Solo esta fuente (se puede repetir). Por defecto, las 5.",
    )
    args = parser.parse_args(argv)

    corrida = datetime.now(UTC)
    distintas = []
    with conectar_dwh() as dwh:
        dwh.autocommit = True
        raw.preparar_registro(dwh)
        for nombre in args.fuente or list(FUENTES):
            for destino, filas_origen, filas_raw in extraer(nombre, dwh, corrida):
                marca = "" if filas_origen == filas_raw else "  <- no coincide"
                print(f"raw.{destino:<40} {filas_origen:>8} {filas_raw:>8}{marca}")
                if marca:
                    distintas.append(destino)

    if distintas:
        print(f"\n{len(distintas)} tablas no coinciden con su origen.")
        return 1
    print(f"\nCorrida {corrida:%Y-%m-%d %H:%M:%S} UTC: todo coincide con el origen.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
