"""Escritura por lotes en las 5 bases de origen de CineMax."""

from cinemax_analytics.fuentes import FUENTES, conectar_mongo, conectar_mysql, conectar_postgres
from cinemax_analytics.generador.modelo import PlanGeneracion

CLASE_PELICULA = "com.cinemax.cartelera.entity.Movie"
CLASE_FUNCION = "com.cinemax.cartelera.entity.Showtime"


def _actualizar_secuencia(cursor, tabla: str, columna: str) -> None:
    cursor.execute(
        f"SELECT setval(pg_get_serial_sequence('{tabla}', '{columna}'), "
        f"coalesce(max({columna}), 1), max({columna}) IS NOT NULL) FROM {tabla}"
    )


def escribir_sucursales(plan: PlanGeneracion) -> None:
    sedes = [s for s in plan.catalogo.sedes if s.es_nueva]
    salas = [r for r in plan.catalogo.salas if r.es_nueva]
    butacas = [b for b in plan.catalogo.butacas if b.es_nueva]

    conn = conectar_mysql(FUENTES["sucursales"], autocommit=False)
    try:
        with conn.cursor() as cur:
            if sedes:
                cur.executemany(
                    "INSERT INTO venue (id_venue, name_venue, address, phone_number, status, "
                    "created_at, image_url, id_district, latitude, longitude) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                    [
                        (
                            s.id_venue,
                            s.name_venue,
                            s.address,
                            s.phone_number,
                            s.status,
                            s.created_at,
                            None,
                            s.id_district,
                            s.latitude,
                            s.longitude,
                        )
                        for s in sedes
                    ],
                )
            if salas:
                cur.executemany(
                    "INSERT INTO room (id_room, name_room, capacity, num_rows, seats_per_row, "
                    "status, id_venue) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                    [
                        (
                            r.id_room,
                            r.name_room,
                            r.capacity,
                            r.num_rows,
                            r.seats_per_row,
                            r.status,
                            r.id_venue,
                        )
                        for r in salas
                    ],
                )
            if butacas:
                cur.executemany(
                    "INSERT INTO seat (id_seat, row_name, column_number, status, id_seat_type, "
                    "id_room) VALUES (%s, %s, %s, %s, %s, %s)",
                    [
                        (
                            b.id_seat,
                            b.row_name,
                            b.column_number,
                            b.status,
                            b.id_seat_type,
                            b.id_room,
                        )
                        for b in butacas
                    ],
                )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def escribir_confiteria(plan: PlanGeneracion) -> None:
    productos = [p for p in plan.catalogo.productos if p.es_nuevo]
    stocks = plan.catalogo.stocks_nuevos

    conn = conectar_mysql(FUENTES["confiteria"], autocommit=False)
    try:
        with conn.cursor() as cur:
            if productos:
                cur.executemany(
                    "INSERT INTO snack (id_snack, id_venue, id_snack_category, name_snack, "
                    "description_snack, price, stock, image_url_snack, status, created_at) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                    [
                        (
                            p.id_snack,
                            p.id_venue,
                            p.id_snack_category,
                            p.name_snack,
                            p.description_snack,
                            p.price,
                            p.stock,
                            None,
                            p.status,
                            p.created_at,
                        )
                        for p in productos
                    ],
                )
            if stocks:
                cur.executemany(
                    "INSERT INTO snack_venue_stock (id_snack, id_venue, stock, status) "
                    "VALUES (%s, %s, %s, %s)",
                    [(s.id_snack, s.id_venue, s.stock, s.status) for s in stocks],
                )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def escribir_cartelera(plan: PlanGeneracion) -> None:
    db = conectar_mongo(FUENTES["cartelera"])
    if plan.catalogo.peliculas:
        docs_peliculas = [
            {
                "_id": m.id,
                "titleMovie": m.title_movie,
                "synopsis": m.synopsis,
                "durationMinutes": m.duration_minutes,
                "posterUrl": m.poster_url,
                "director": m.director,
                "releaseDate": m.release_date,
                "status": m.status,
                "createdAt": m.created_at,
                "isActive": m.is_active,
                "premiereWeek": m.premiere_week,
                "genreIds": list(m.genre_ids),
                "classificationId": m.classification_id,
                "_class": CLASE_PELICULA,
            }
            for m in plan.catalogo.peliculas
        ]
        db.movies.insert_many(docs_peliculas, ordered=True)

    if plan.funciones:
        docs_funciones = []
        for f in plan.funciones:
            doc = {
                "_id": f.id,
                "showDate": f.show_date,
                "startTime": f.start_time,
                "endTime": f.end_time,
                "languageFormat": f.language_format,
                "baseTicketPrice": f.base_ticket_price,
                "availableSeats": f.available_seats,
                "status": f.status,
                "movieId": f.movie_id,
                "idRoom": f.id_room,
                "idVenue": f.id_venue,
                "_class": CLASE_FUNCION,
            }
            if f.sold_seats > 0:
                doc["soldSeats"] = f.sold_seats
            docs_funciones.append(doc)
        db.showtimes.insert_many(docs_funciones, ordered=True)


def escribir_usuarios(plan: PlanGeneracion) -> None:
    sql_copy = (
        "COPY user_account (id_user, datebirth, document_number, email, first_name, "
        "id_venue, image_url, last_name, password, phone, reset_password_token, "
        "status, token_expiration_date, id_doc_type, id_role) FROM STDIN"
    )
    with (
        conectar_postgres(FUENTES["usuarios"]) as conn,
        conn.transaction(),
        conn.cursor() as cur,
    ):
        with cur.copy(sql_copy) as copy:
            for c in plan.catalogo.clientes:
                copy.write_row(
                    (
                        c.id_user,
                        c.datebirth,
                        c.document_number,
                        c.email,
                        c.first_name,
                        None,
                        None,
                        c.last_name,
                        c.password,
                        c.phone,
                        None,
                        c.status,
                        None,
                        c.id_doc_type,
                        c.id_role,
                    )
                )
        _actualizar_secuencia(cur, "user_account", "id_user")


def escribir_facturacion(plan: PlanGeneracion) -> None:
    sql_tx = (
        "COPY sale_transaction (id_transaction, id_user, id_transaction_status, "
        "subtotal, discount_amount, total_amount, payment_method, created_at, "
        "payment_date, qr_code_data, id_promotion, id_showtime, id_venue, "
        "movie_title, show_date, start_time, room_name, venue_name) FROM STDIN"
    )
    sql_tk = (
        "COPY sale_ticket_detail (id_ticket, id_transaction, id_showtime, id_seat, "
        "seat_code, fare_category, ticket_price, discount_amount, is_used) FROM STDIN"
    )
    sql_sn = (
        "COPY sale_snack_detail (id_detail, id_transaction, id_snack, snack_name, "
        "quantity, unit_price, discount_amount, is_delivered) FROM STDIN"
    )
    with (
        conectar_postgres(FUENTES["facturacion"]) as conn,
        conn.transaction(),
        conn.cursor() as cur,
    ):
        with cur.copy(sql_tx) as copy_tx:
            for v in plan.ventas:
                copy_tx.write_row(
                    (
                        v.id_transaction,
                        v.id_user,
                        v.id_transaction_status,
                        v.subtotal,
                        v.discount_amount,
                        v.total_amount,
                        v.payment_method,
                        v.created_at,
                        v.payment_date,
                        v.qr_code_data,
                        v.id_promotion,
                        v.id_showtime,
                        v.id_venue,
                        v.movie_title,
                        v.show_date,
                        v.start_time,
                        v.room_name,
                        v.venue_name,
                    )
                )

        with cur.copy(sql_tk) as copy_tk:
            for v in plan.ventas:
                for e in v.entradas:
                    copy_tk.write_row(
                        (
                            e.id_ticket,
                            e.id_transaction,
                            e.id_showtime,
                            e.id_seat,
                            e.seat_code,
                            e.fare_category,
                            e.ticket_price,
                            e.discount_amount,
                            e.is_used,
                        )
                    )

        with cur.copy(sql_sn) as copy_sn:
            for v in plan.ventas:
                for s in v.snacks:
                    copy_sn.write_row(
                        (
                            s.id_detail,
                            s.id_transaction,
                            s.id_snack,
                            s.snack_name,
                            s.quantity,
                            s.unit_price,
                            s.discount_amount,
                            s.is_delivered,
                        )
                    )

        _actualizar_secuencia(cur, "sale_transaction", "id_transaction")
        _actualizar_secuencia(cur, "sale_ticket_detail", "id_ticket")
        _actualizar_secuencia(cur, "sale_snack_detail", "id_detail")


def escribir_todo(plan: PlanGeneracion) -> None:
    escribir_sucursales(plan)
    escribir_confiteria(plan)
    escribir_cartelera(plan)
    escribir_usuarios(plan)
    escribir_facturacion(plan)
