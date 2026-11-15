"""uv run python -m cinemax_analytics.generador.defectos [--semilla 7]

Mete defectos con tasas conocidas en las bases ya generadas y anota en el warehouse
(raw._defectos_inyectados) cuántas filas tocó cada uno. calidad_deteccion compara eso
con lo que encuentran los chequeos. Cada defecto cae en filas distintas, para que
cada uno lo detecte un solo chequeo.
"""

import argparse
import sys

import numpy as np
from pymongo import UpdateOne

from cinemax_analytics.fuentes import (
    FUENTES,
    conectar_dwh,
    conectar_mongo,
    conectar_mysql,
    conectar_postgres,
)

TASAS = {
    "desfase_butacas_disponibles": 0.01,  # de las funciones con ventas
    "venta_con_cliente_inexistente": 0.001,  # de las ventas
    "venta_que_no_cuadra": 0.002,  # de las ventas
    "entrada_con_butaca_inexistente": 0.0005,  # de las entradas
    "precio_fuera_de_tarifa": 0.001,  # de las entradas
}
PRODUCTOS_MAL_CODIFICADOS = 2

CREAR_REGISTRO = """
    CREATE TABLE IF NOT EXISTS raw._defectos_inyectados (
        chequeo     text        PRIMARY KEY,
        filas       bigint      NOT NULL,
        semilla     integer     NOT NULL,
        inyectado_en timestamptz NOT NULL DEFAULT now()
    )
"""


def _cuantos(total: int, tasa: float) -> int:
    return max(1, round(total * tasa))


def inyectar(semilla: int) -> dict[str, int]:
    rng = np.random.default_rng(semilla)
    resultado: dict[str, int] = {}

    with conectar_postgres(FUENTES["facturacion"]) as conexion:
        ventas = [
            f[0] for f in conexion.execute("SELECT id_transaction FROM sale_transaction ORDER BY 1")
        ]
        entradas = conexion.execute(
            "SELECT id_ticket, id_transaction FROM sale_ticket_detail ORDER BY 1"
        ).fetchall()
        if not ventas:
            raise RuntimeError("No hay ventas: corre el generador primero")

        orden = rng.permutation(len(ventas))
        n_cliente = _cuantos(len(ventas), TASAS["venta_con_cliente_inexistente"])
        n_cuadra = _cuantos(len(ventas), TASAS["venta_que_no_cuadra"])
        con_cliente = [ventas[i] for i in orden[:n_cliente]]
        sin_cuadrar = [ventas[i] for i in orden[n_cliente : n_cliente + n_cuadra]]
        tocadas = set(con_cliente) | set(sin_cuadrar)

        libres = [e for e in entradas if e[1] not in tocadas]
        orden_e = rng.permutation(len(libres))
        n_butaca = _cuantos(len(entradas), TASAS["entrada_con_butaca_inexistente"])
        n_precio = _cuantos(len(entradas), TASAS["precio_fuera_de_tarifa"])
        con_butaca = [libres[i][0] for i in orden_e[:n_butaca]]
        con_precio = [libres[i] for i in orden_e[n_butaca : n_butaca + n_precio]]

        with conexion.transaction():
            for k, id_venta in enumerate(con_cliente):
                conexion.execute(
                    "UPDATE sale_transaction SET id_user = %s WHERE id_transaction = %s",
                    (9_000_000 + k, id_venta),
                )
            for id_venta in sin_cuadrar:
                conexion.execute(
                    "UPDATE sale_transaction SET total_amount = total_amount + 1 "
                    "WHERE id_transaction = %s",
                    (id_venta,),
                )
            for k, id_entrada in enumerate(con_butaca):
                conexion.execute(
                    "UPDATE sale_ticket_detail SET id_seat = %s WHERE id_ticket = %s",
                    (900_000 + k, id_entrada),
                )
            # El precio sube S/ 0,50 y la venta también, así que solo lo ve la tarifa.
            for id_entrada, id_venta in con_precio:
                conexion.execute(
                    "UPDATE sale_ticket_detail SET ticket_price = ticket_price + 0.50 "
                    "WHERE id_ticket = %s",
                    (id_entrada,),
                )
                conexion.execute(
                    "UPDATE sale_transaction SET subtotal = subtotal + 0.50, "
                    "total_amount = total_amount + 0.50 WHERE id_transaction = %s",
                    (id_venta,),
                )
    resultado["venta_con_cliente_inexistente"] = len(con_cliente)
    resultado["venta_que_no_cuadra"] = len(sin_cuadrar)
    resultado["entrada_con_butaca_inexistente"] = len(con_butaca)
    resultado["precio_fuera_de_tarifa"] = len(con_precio)

    db = conectar_mongo()
    funciones = [
        (d["_id"], d["availableSeats"])
        for d in db.showtimes.find(
            {"_class": {"$exists": True}, "soldSeats": {"$gt": 0}}, {"availableSeats": 1}
        ).sort("_id", 1)
    ]
    n_desfase = _cuantos(len(funciones), TASAS["desfase_butacas_disponibles"])
    elegidas = [funciones[i] for i in rng.permutation(len(funciones))[:n_desfase]]
    saltos = rng.choice([-3, -2, -1, 1, 2, 3], size=len(elegidas))
    db.showtimes.bulk_write(
        [
            UpdateOne({"_id": oid}, {"$set": {"availableSeats": max(0, int(disp + salto))}})
            for (oid, disp), salto in zip(elegidas, saltos, strict=True)
            if max(0, int(disp + salto)) != disp
        ]
    )
    resultado["desfase_butacas_disponibles"] = sum(
        1
        for (_, disp), salto in zip(elegidas, saltos, strict=True)
        if max(0, int(disp + salto)) != disp
    )

    # "María" leído como latin1: "MarÃ­a". Solo productos con tilde o eñe.
    conexion_mysql = conectar_mysql(FUENTES["confiteria"])
    try:
        with conexion_mysql.cursor() as cursor:
            cursor.execute("SELECT id_snack, name_snack FROM snack ORDER BY id_snack")
            con_tilde = [
                (i, n)
                for i, n in cursor.fetchall()
                if n.encode("utf-8") != n.encode("ascii", "ignore")
            ]
            elegidos = [
                con_tilde[i] for i in rng.permutation(len(con_tilde))[:PRODUCTOS_MAL_CODIFICADOS]
            ]
            for id_snack, nombre in elegidos:
                cursor.execute(
                    "UPDATE snack SET name_snack = %s WHERE id_snack = %s",
                    (nombre.encode("utf-8").decode("latin-1"), id_snack),
                )
        conexion_mysql.commit()
    finally:
        conexion_mysql.close()
    resultado["texto_mal_codificado"] = len(elegidos)

    with conectar_dwh() as dwh:
        dwh.execute(CREAR_REGISTRO)
        dwh.execute("TRUNCATE raw._defectos_inyectados")
        for chequeo, filas in resultado.items():
            dwh.execute(
                "INSERT INTO raw._defectos_inyectados (chequeo, filas, semilla) VALUES (%s, %s, %s)",
                (chequeo, filas, semilla),
            )
    return resultado


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m cinemax_analytics.generador.defectos")
    parser.add_argument("--semilla", type=int, default=7)
    args = parser.parse_args(argv)

    with conectar_dwh() as dwh:
        dwh.execute(CREAR_REGISTRO)
        ya = dwh.execute("SELECT count(*) FROM raw._defectos_inyectados").fetchone()[0]
    if ya:
        print(
            "Ya hay defectos inyectados: recrea el entorno (docker compose down -v).",
            file=sys.stderr,
        )
        return 1

    for chequeo, filas in inyectar(args.semilla).items():
        print(f"{chequeo:<34} {filas:>6}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
