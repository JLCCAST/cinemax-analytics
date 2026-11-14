"""Cada venta tiene que verse como una que registró facturacion-service."""

from datetime import datetime, timedelta

from apoyo import decimal_mongo, en_lima, fecha_mongo, hora_mongo, primeros

from cinemax_analytics.generador import tarifas
from cinemax_analytics.generador.promociones import (
    Cliente,
    ContadorDeUsos,
    Entrada,
    Snack,
    Venta,
    evaluar,
)

ANTICIPACION_MAXIMA = timedelta(days=30)


def test_solo_ventas_completadas(datos):
    # CineMax no tiene anulaciones: solo escribe COMPLETADO.
    assert {v["estado"] for v in datos.ventas} == {"COMPLETADO"}


def test_metodo_de_pago(datos):
    assert {v["payment_method"] for v in datos.ventas} <= {"TARJETA", "YAPE"}


def test_creada_y_pagada_en_el_mismo_instante(datos):
    malas = [
        v["id_transaction"]
        for v in datos.ventas
        if v["payment_date"] is None
        or abs((v["created_at"] - v["payment_date"]).total_seconds()) > 1
    ]
    assert not malas, primeros(malas)


def test_totales_cuadran_con_las_lineas(datos):
    malas = []
    for v in datos.ventas:
        entradas = datos.entradas.get(v["id_transaction"], [])
        lineas = datos.lineas.get(v["id_transaction"], [])
        bruto = sum(e["ticket_price"] for e in entradas) + sum(
            ln["unit_price"] * ln["quantity"] for ln in lineas
        )
        descuento = sum(e["discount_amount"] for e in entradas) + sum(
            ln["discount_amount"] for ln in lineas
        )
        if (
            v["subtotal"] != bruto
            or v["discount_amount"] != descuento
            or v["total_amount"] != v["subtotal"] - v["discount_amount"]
            or v["total_amount"] < 0
        ):
            malas.append(v["id_transaction"])
    assert not malas, primeros(malas)


def test_toda_venta_tiene_lineas(datos):
    vacias = [
        v["id_transaction"]
        for v in datos.ventas
        if not datos.entradas.get(v["id_transaction"]) and not datos.lineas.get(v["id_transaction"])
    ]
    assert not vacias, primeros(vacias)


def test_precio_de_cada_entrada_sale_de_la_tarifa(datos):
    malas = []
    for lista in datos.entradas.values():
        for e in lista:
            funcion = datos.funciones[e["id_showtime"]]
            base = funcion["baseTicketPrice"]
            esperado = tarifas.precio(decimal_mongo(base), e["fare_category"])
            if e["ticket_price"] != esperado:
                malas.append((e["id_ticket"], e["fare_category"], str(base), e["ticket_price"]))
    assert not malas, primeros(malas)


def test_promocion_y_descuentos_iguales_al_motor_de_cinemax(datos):
    """Recalcula cada venta con el motor y compara promoción, descuento y reparto.

    La venta no guarda el cupón: si ganó una promoción con código, el cliente lo
    escribió; si no, da igual, porque un cupón que no gana no cambia el resultado.
    """
    promociones = {p.id: p for p in datos.promociones}
    contador = ContadorDeUsos()
    malas = []
    for v in datos.ventas:
        aplicada = promociones.get(v["id_promotion"])
        venta = _venta_para_el_motor(datos, v, aplicada.codigo if aplicada else None)
        usos = contador.usos(v["id_user"], en_lima(v["created_at"]), datos.promociones)
        resultado = evaluar(venta, datos.promociones, usos)

        entradas = datos.entradas.get(v["id_transaction"], [])
        lineas = datos.lineas.get(v["id_transaction"], [])
        esperado = (
            resultado.promocion.id if resultado.promocion else None,
            resultado.descuento,
            resultado.descuentos_entradas,
            resultado.descuentos_snacks,
        )
        guardado = (
            v["id_promotion"],
            v["discount_amount"],
            tuple(e["discount_amount"] for e in entradas),
            tuple(ln["discount_amount"] for ln in lineas),
        )
        if esperado != guardado:
            malas.append((v["id_transaction"], "esperado", esperado[:2], "guardado", guardado[:2]))
        contador.registrar(v["id_user"], v["id_promotion"], v["created_at"])
    assert not malas, primeros(malas)


def test_pagada_antes_de_la_funcion(datos):
    malas = []
    for v in datos.ventas:
        if v["id_showtime"] is None:
            continue
        funcion = datos.funciones[v["id_showtime"]]
        inicio = datetime.combine(
            fecha_mongo(funcion["showDate"]), hora_mongo(funcion["startTime"])
        )
        pagada = en_lima(v["payment_date"])
        if not (inicio - ANTICIPACION_MAXIMA <= pagada < inicio):
            malas.append((v["id_transaction"], pagada, inicio))
    assert not malas, primeros(malas)


def test_la_venta_guarda_los_datos_de_la_funcion(datos):
    malas = []
    for v in datos.ventas:
        if v["id_showtime"] is None:
            continue
        funcion = datos.funciones[v["id_showtime"]]
        pelicula = datos.peliculas[funcion["movieId"]]
        sala = datos.salas[funcion["idRoom"]]
        sede = datos.sedes[funcion["idVenue"]]
        esperado = (
            funcion["idVenue"],
            pelicula["titleMovie"],
            fecha_mongo(funcion["showDate"]),
            hora_mongo(funcion["startTime"]),
            sala["name_room"],
            sede["name_venue"],
        )
        guardado = (
            v["id_venue"],
            v["movie_title"],
            v["show_date"],
            v["start_time"],
            v["room_name"],
            v["venue_name"],
        )
        if esperado != guardado:
            malas.append((v["id_transaction"], esperado, guardado))
        for e in datos.entradas.get(v["id_transaction"], []):
            butaca = datos.butacas[e["id_seat"]]
            if e["id_showtime"] != v["id_showtime"]:
                malas.append((e["id_ticket"], "otra función"))
            if e["seat_code"] != f"{butaca['row_name']}{butaca['column_number']}":
                malas.append((e["id_ticket"], "código de butaca", e["seat_code"]))
    assert not malas, primeros(malas)


def test_pedidos_solo_de_confiteria(datos):
    solo = [v for v in datos.ventas if v["id_showtime"] is None]
    proporcion = len(solo) / len(datos.ventas)
    assert 0.01 <= proporcion <= 0.15, f"{proporcion:.1%} de pedidos solo de confitería"
    malas = []
    for v in solo:
        sede = datos.sedes.get(v["id_venue"])
        if (
            datos.entradas.get(v["id_transaction"])
            or not datos.lineas.get(v["id_transaction"])
            or sede is None
            or v["venue_name"] != sede["name_venue"]
            or any(
                v[c] is not None for c in ("movie_title", "show_date", "start_time", "room_name")
            )
        ):
            malas.append(v["id_transaction"])
    assert not malas, primeros(malas)


def test_lineas_de_confiteria(datos):
    ventas = {v["id_transaction"]: v for v in datos.ventas}
    ultima = max(v["payment_date"] for v in datos.ventas)
    malas = []
    for id_venta, lineas in datos.lineas.items():
        venta = ventas[id_venta]
        for ln in lineas:
            producto = datos.productos.get(ln["id_snack"])
            if producto is None or producto["status"] != "Activo" or ln["quantity"] <= 0:
                malas.append((ln["id_detail"], "producto"))
                continue
            if ln["snack_name"] != producto["name_snack"]:
                malas.append((ln["id_detail"], "nombre", ln["snack_name"]))
            if (ln["id_snack"], venta["id_venue"]) not in datos.stock:
                malas.append((ln["id_detail"], "sin stock en la sede", venta["id_venue"]))
            # El precio de hoy es el último vigente: el último mes se vende a ese precio.
            reciente = ultima - venta["payment_date"] < timedelta(days=30)
            if reciente and ln["unit_price"] != producto["price"]:
                malas.append((ln["id_detail"], "precio", ln["unit_price"], producto["price"]))
    assert not malas, primeros(malas)


def test_compran_solo_clientes(datos):
    malos = [
        v["id_transaction"]
        for v in datos.ventas
        if datos.usuarios.get(v["id_user"], {}).get("role_name") != "CLIENTE"
    ]
    assert not malos, primeros(malos)


def test_secuencias_al_dia(datos):
    # Si el generador inserta ids propios, CineMax tiene que poder seguir insertando.
    atrasadas = [(t, ultimo, maximo) for t, ultimo, maximo in datos.secuencias if ultimo < maximo]
    assert not atrasadas, atrasadas


def _venta_para_el_motor(datos, v, cupon) -> Venta:
    if v["id_showtime"] is not None:
        funcion = datos.funciones[v["id_showtime"]]
        pelicula = datos.peliculas.get(funcion["movieId"], {})
        fecha = fecha_mongo(funcion["showDate"])
        hora = hora_mongo(funcion["startTime"])
        estreno = fecha_mongo(pelicula["releaseDate"]) if pelicula.get("releaseDate") else None
    else:
        # Pedido solo de confitería: CineMax usa la fecha y la hora de la compra.
        momento = en_lima(v["created_at"])
        fecha, hora, estreno = momento.date(), momento.time(), None

    usuario = datos.usuarios.get(v["id_user"])
    return Venta(
        fecha_funcion=fecha,
        hora_funcion=hora,
        estreno=estreno,
        cliente=Cliente(usuario["datebirth"]) if usuario else None,
        cupon=cupon,
        entradas=tuple(
            Entrada(e["fare_category"], e["ticket_price"])
            for e in datos.entradas.get(v["id_transaction"], [])
        ),
        snacks=tuple(
            Snack(
                ln["id_snack"],
                datos.productos[ln["id_snack"]]["id_snack_category"],
                ln["unit_price"],
                ln["quantity"],
            )
            for ln in datos.lineas.get(v["id_transaction"], [])
        ),
    )
