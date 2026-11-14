"""Prueba de humo de un entorno recién creado (docker compose down -v && up -d).

Comprueba que las 5 bases respondan, que Flyway dejó cada esquema en la versión
esperada, que los catálogos semilla tengan sus conteos y que el texto de MySQL
no tenga doble codificación. Sale con código 1 si algo no coincide.
"""

import sys

import psycopg
import pymysql
from pymongo.errors import PyMongoError

from cinemax_analytics.fuentes import (
    FUENTES,
    conectar_dwh,
    conectar_mongo,
    conectar_mysql,
    conectar_postgres,
    esperar,
)

# Versión de Flyway de cada base en CineMax c513136.
VERSION_FLYWAY = {"usuarios": "3", "facturacion": "8", "sucursales": "2", "confiteria": "2"}

# None: solo se muestra (el generador llena estas tablas).
CONTEOS = {
    "usuarios": {
        "role": 5,
        "permission": 10,
        "role_permission": None,
        "document_type": 3,
        "user_account": None,
    },
    "facturacion": {
        "transaction_status": 4,
        "promotion_type": 4,
        "promotion": 6,
        "sale_transaction": None,
        "sale_ticket_detail": None,
        "sale_snack_detail": None,
    },
    "sucursales": {
        "department": 3,
        "province": 3,
        "district": 8,
        "seat_type": 2,
        "venue": 2,
        "room": 6,
        "seat": 380,
    },
    "confiteria": {"snack_category": 4, "snack": 7, "snack_venue_stock": 14},
    "cartelera": {"genres": 8, "classifications": 3, "movies": 4, "showtimes": 8},
}

fallas: list[str] = []


def revisar(fuente: str, que: str, esperado, real) -> None:
    ok = esperado is None or esperado == real
    marca = "ok" if ok else "FALLA"
    print(f"  {que:<32} {esperado if esperado is not None else '-'!s:>9} {real!s:>9}  {marca}")
    if not ok:
        fallas.append(f"{fuente}.{que}: se esperaba {esperado} y hay {real}")


def version_flyway(cursor) -> str:
    cursor.execute(
        "SELECT version FROM flyway_schema_history WHERE success "
        "ORDER BY installed_rank DESC LIMIT 1"
    )
    return cursor.fetchone()[0]


def migrada(conectar, nombre: str):
    """Conexión lista solo cuando el contenedor de Flyway terminó de migrar esa base."""

    def intento():
        conexion = conectar()
        try:
            version = version_flyway(conexion.cursor())
        except Exception:
            conexion.close()
            raise
        if version != VERSION_FLYWAY[nombre]:
            conexion.close()
            raise RuntimeError(
                f"{nombre}: Flyway está en la versión {version} y se esperaba "
                f"{VERSION_FLYWAY[nombre]}"
            )
        return conexion

    return intento


def postgres(nombre: str) -> None:
    conectar = migrada(lambda: conectar_postgres(FUENTES[nombre]), nombre)
    with esperar(conectar) as conexion:
        cursor = conexion.cursor()
        revisar(nombre, "flyway", VERSION_FLYWAY[nombre], version_flyway(cursor))
        for tabla, esperado in CONTEOS[nombre].items():
            cursor.execute(f'SELECT count(*) FROM "{tabla}"')
            revisar(nombre, tabla, esperado, cursor.fetchone()[0])


def mysql(nombre: str) -> None:
    conexion = esperar(migrada(lambda: conectar_mysql(FUENTES[nombre]), nombre))
    try:
        cursor = conexion.cursor()
        revisar(nombre, "flyway", VERSION_FLYWAY[nombre], version_flyway(cursor))
        for tabla, esperado in CONTEOS[nombre].items():
            cursor.execute(f"SELECT count(*) FROM `{tabla}`")
            revisar(nombre, tabla, esperado, cursor.fetchone()[0])

        # Doble codificación: "María" guardado como "MarÃ­a". La comparación es
        # binaria porque la intercalación por defecto ignora los acentos.
        cursor.execute(
            "SELECT table_name, column_name FROM information_schema.columns "
            "WHERE table_schema = DATABASE() AND data_type IN ('varchar', 'char', 'text') "
            "AND table_name <> 'flyway_schema_history'"
        )
        mal_codificados = 0
        for tabla, columna in cursor.fetchall():
            cursor.execute(
                f"SELECT count(*) FROM `{tabla}` WHERE `{columna}` COLLATE utf8mb4_bin LIKE %s",
                ("%Ã%",),
            )
            mal_codificados += cursor.fetchone()[0]
        revisar(nombre, "textos con doble codificación", 0, mal_codificados)
    finally:
        conexion.close()


def mongo() -> None:
    db = esperar(lambda: _mongo_listo())
    for coleccion, esperado in CONTEOS["cartelera"].items():
        revisar("cartelera", coleccion, esperado, db[coleccion].count_documents({}))


def _mongo_listo():
    db = conectar_mongo()
    db.command("ping")
    return db


def main() -> int:
    for nombre in FUENTES:
        print(f"{nombre}:")
        motor = FUENTES[nombre].motor
        try:
            if motor == "postgres":
                postgres(nombre)
            elif motor == "mysql":
                mysql(nombre)
            else:
                mongo()
        except (psycopg.Error, pymysql.Error, PyMongoError, RuntimeError) as error:
            print(f"  no responde: {error}")
            fallas.append(f"{nombre}: {error}")

    print("dwh:")
    with esperar(conectar_dwh) as conexion:
        esquemas = {
            fila[0]
            for fila in conexion.execute(
                "SELECT schema_name FROM information_schema.schemata "
                "WHERE schema_name IN ('raw', 'staging', 'marts', 'semantic')"
            )
        }
        revisar("dwh", "esquemas", 4, len(esquemas))

    if fallas:
        print("\nFallas:")
        for falla in fallas:
            print(f"  - {falla}")
        return 1
    print("\nTodo coincide.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
