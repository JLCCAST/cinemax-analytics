"""Lectura del estado semilla de las 5 bases de origen."""

from dataclasses import dataclass
from datetime import UTC, date, datetime, time
from decimal import Decimal

import pymysql
from psycopg.rows import dict_row

from cinemax_analytics.fuentes import FUENTES, conectar_mongo, conectar_mysql, conectar_postgres
from cinemax_analytics.generador.modelo import ButacaPlan, ProductoPlan, SalaPlan, SedePlan
from cinemax_analytics.generador.promociones import Promocion, cargar_promociones


@dataclass(frozen=True)
class FuncionSemilla:
    id_hex: str
    id_room: int
    id_venue: int
    fecha: date
    hora_inicio: time
    hora_fin: time


@dataclass
class EstadoSemilla:
    sedes: list[SedePlan]
    salas: list[SalaPlan]
    butacas: list[ButacaPlan]
    productos: list[ProductoPlan]
    stock_existente: set[tuple[int, int]]
    generos: dict[str, str]  # nombre -> id hex
    clasificaciones: dict[str, str]  # nombre -> id hex
    titulos_peliculas_seed: set[str]
    funciones_seed: list[FuncionSemilla]
    id_rol_cliente: int
    tipos_documento: dict[str, int]  # DNI, CE, PASAPORTE -> id_doc_type
    max_id_user: int
    id_estado_completado: int
    promociones: list[Promocion]
    max_id_transaction: int
    max_id_ticket: int
    max_id_detail: int
    ventas_existentes: int
    peliculas_generadas_existentes: int


def leer_semilla() -> EstadoSemilla:
    # 1. Sucursales (MySQL)
    conn_suc = conectar_mysql(FUENTES["sucursales"], cursorclass=pymysql.cursors.DictCursor)
    try:
        with conn_suc.cursor() as cur:
            # Solo leemos las 2 sedes y 6 salas del seed para que --simular sea idéntico
            # antes y después de haber corrido el generador.
            cur.execute("SELECT * FROM venue WHERE id_venue <= 2 ORDER BY id_venue")
            sedes = [
                SedePlan(
                    id_venue=f["id_venue"],
                    name_venue=f["name_venue"],
                    address=f["address"],
                    phone_number=f["phone_number"] or "",
                    status=f["status"],
                    created_at=f["created_at"] or datetime(2025, 1, 1, 0, 0),
                    id_district=f["id_district"],
                    latitude=float(f["latitude"] or 0.0),
                    longitude=float(f["longitude"] or 0.0),
                    es_nueva=False,
                )
                for f in cur.fetchall()
            ]
            cur.execute("SELECT * FROM room WHERE id_room <= 6 ORDER BY id_room")
            salas = [
                SalaPlan(
                    id_room=f["id_room"],
                    name_room=f["name_room"],
                    capacity=f["capacity"],
                    num_rows=f["num_rows"],
                    seats_per_row=f["seats_per_row"],
                    status=f["status"],
                    id_venue=f["id_venue"],
                    es_vip="VIP" in f["name_room"].upper(),
                    es_nueva=False,
                )
                for f in cur.fetchall()
            ]
            cur.execute("SELECT * FROM seat WHERE id_room <= 6 ORDER BY id_seat")
            butacas = [
                ButacaPlan(
                    id_seat=f["id_seat"],
                    row_name=f["row_name"],
                    column_number=f["column_number"],
                    status=f["status"],
                    id_seat_type=f["id_seat_type"],
                    id_room=f["id_room"],
                    es_nueva=False,
                )
                for f in cur.fetchall()
            ]
    finally:
        conn_suc.close()

    # 2. Confitería (MySQL)
    conn_conf = conectar_mysql(FUENTES["confiteria"], cursorclass=pymysql.cursors.DictCursor)
    try:
        with conn_conf.cursor() as cur:
            cur.execute("SELECT * FROM snack WHERE id_snack <= 7 ORDER BY id_snack")
            productos = [
                ProductoPlan(
                    id_snack=f["id_snack"],
                    id_venue=f["id_venue"] or 1,
                    id_snack_category=f["id_snack_category"],
                    name_snack=f["name_snack"],
                    description_snack=f["description_snack"] or "",
                    precio_inicial=Decimal(str(f["price"])),
                    price=Decimal(str(f["price"])),
                    fecha_cambio_precio=None,
                    stock=f["stock"],
                    status=f["status"],
                    created_at=f["created_at"],
                    es_nuevo=False,
                )
                for f in cur.fetchall()
            ]
            cur.execute(
                "SELECT id_snack, id_venue FROM snack_venue_stock "
                "WHERE id_snack <= 7 AND id_venue <= 2"
            )
            stock_existente = {(f["id_snack"], f["id_venue"]) for f in cur.fetchall()}
    finally:
        conn_conf.close()

    # 3. Cartelera (MongoDB)
    db = conectar_mongo(FUENTES["cartelera"])
    generos = {
        d["nameGenre"]: str(d["_id"])
        for d in sorted(db.genres.find(), key=lambda x: x["nameGenre"])
    }
    clasificaciones = {
        d["nameClassification"]: str(d["_id"])
        for d in sorted(db.classifications.find(), key=lambda x: x["nameClassification"])
    }
    peliculas_seed = list(db.movies.find({"_class": {"$exists": False}}))
    titulos_peliculas_seed = {d["titleMovie"] for d in peliculas_seed}
    peliculas_generadas_existentes = db.movies.count_documents({"_class": {"$exists": True}})

    funciones_seed = []
    for f in sorted(db.showtimes.find({"_class": {"$exists": False}}), key=lambda x: str(x["_id"])):
        fecha = f["showDate"].astimezone(UTC).date()
        inicio = f["startTime"].astimezone(UTC).time().replace(tzinfo=None)
        fin = f["endTime"].astimezone(UTC).time().replace(tzinfo=None)
        funciones_seed.append(
            FuncionSemilla(
                id_hex=str(f["_id"]),
                id_room=int(f.get("idRoom") or f.get("roomId")),
                id_venue=int(f.get("idVenue") or f.get("venueId")),
                fecha=fecha,
                hora_inicio=inicio,
                hora_fin=fin,
            )
        )

    # 4. Usuarios (PostgreSQL)
    with conectar_postgres(FUENTES["usuarios"]) as conn_usr:
        cur = conn_usr.cursor(row_factory=dict_row)
        fila_rol = cur.execute("SELECT id_role FROM role WHERE role_name = 'CLIENTE'").fetchone()
        id_rol_cliente = int(fila_rol["id_role"])
        tipos_documento = {
            f["doc_name"]: int(f["id_doc_type"])
            for f in cur.execute("SELECT id_doc_type, doc_name FROM document_type")
        }
        fila_max_usr = cur.execute(
            "SELECT coalesce(max(id_user), 0) AS m FROM user_account WHERE email NOT LIKE '%.test'"
        ).fetchone()
        max_id_user = int(fila_max_usr["m"])

    # 5. Facturación (PostgreSQL)
    with conectar_postgres(FUENTES["facturacion"]) as conn_fac:
        promociones = cargar_promociones(conn_fac)
        cur = conn_fac.cursor(row_factory=dict_row)
        fila_est = cur.execute(
            "SELECT id_transaction_status FROM transaction_status WHERE name_status = 'COMPLETADO'"
        ).fetchone()
        id_estado_completado = int(fila_est["id_transaction_status"])
        ventas_existentes = int(
            cur.execute("SELECT count(*) AS n FROM sale_transaction").fetchone()["n"]
        )

    return EstadoSemilla(
        sedes=sedes,
        salas=salas,
        butacas=butacas,
        productos=productos,
        stock_existente=stock_existente,
        generos=generos,
        clasificaciones=clasificaciones,
        titulos_peliculas_seed=titulos_peliculas_seed,
        funciones_seed=funciones_seed,
        id_rol_cliente=id_rol_cliente,
        tipos_documento=tipos_documento,
        max_id_user=max_id_user,
        id_estado_completado=id_estado_completado,
        promociones=promociones,
        max_id_transaction=0,
        max_id_ticket=0,
        max_id_detail=0,
        ventas_existentes=ventas_existentes,
        peliculas_generadas_existentes=peliculas_generadas_existentes,
    )
