"""Generación determinista de la demanda, selección de butacas y evaluación de promociones."""

import csv
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from decimal import Decimal

import numpy as np

from cinemax_analytics.fuentes import RAIZ
from cinemax_analytics.generador import tarifas
from cinemax_analytics.generador.modelo import (
    ButacaPlan,
    CatalogoPlan,
    ClientePlan,
    EntradaVentaPlan,
    FuncionPlan,
    PeliculaPlan,
    ProductoPlan,
    SalaPlan,
    SnackVentaPlan,
    TransaccionPlan,
    codigo_qr,
)
from cinemax_analytics.generador.parametros import Parametros
from cinemax_analytics.generador.promociones import (
    Cliente,
    ContadorDeUsos,
    Entrada,
    Snack,
    Venta,
    evaluar,
)

ORDEN_TARIFAS = {cat: idx for idx, cat in enumerate(tarifas.CATEGORIAS)}


def cargar_feriados() -> set[date]:
    ruta = RAIZ / "dbt" / "seeds" / "feriados_peru.csv"
    feriados: set[date] = set()
    with ruta.open(encoding="utf-8") as archivo:
        for fila in csv.DictReader(archivo):
            feriados.add(date.fromisoformat(fila["fecha"].strip()))
    return feriados


def cargar_temporadas() -> list[tuple[str, str, str]]:
    ruta = RAIZ / "dbt" / "seeds" / "temporadas.csv"
    temporadas: list[tuple[str, str, str]] = []
    with ruta.open(encoding="utf-8") as archivo:
        for fila in csv.DictReader(archivo):
            temporadas.append(
                (fila["temporada"].strip(), fila["desde"].strip(), fila["hasta"].strip())
            )
    return temporadas


def _temporada_de(fecha: date, temporadas: list[tuple[str, str, str]]) -> str:
    mm_dd = f"{fecha.month:02d}-{fecha.day:02d}"
    for nombre, desde_md, hasta_md in temporadas:
        if desde_md <= mm_dd <= hasta_md:
            return nombre
    return "Regular"


def _organizar_butacas_sala(
    butacas: list[ButacaPlan], num_filas: int
) -> tuple[list[list[ButacaPlan]], list[ButacaPlan]]:
    por_fila: dict[str, list[ButacaPlan]] = defaultdict(list)
    wheelchair: list[ButacaPlan] = []
    for b in sorted(butacas, key=lambda x: (x.row_name, x.column_number)):
        if b.status != "ACTIVO":
            continue
        if b.id_seat_type == 2:
            wheelchair.append(b)
        else:
            por_fila[b.row_name].append(b)

    letras = sorted(por_fila.keys())
    centro = (max(1, num_filas) - 1) / 2.0
    letras_centrales = sorted(letras, key=lambda letra: (abs((ord(letra) - 65) - centro), letra))
    filas_ordenadas = [por_fila[letra] for letra in letras_centrales]
    return filas_ordenadas, wheelchair


def _elegir_butacas_grupo(
    categorias: list[str],
    filas_regulares: list[list[ButacaPlan]],
    wheelchair: list[ButacaPlan],
    ocupadas: set[int],
) -> list[ButacaPlan]:
    n_disc = sum(1 for c in categorias if c == "DISCAPACITADO")
    n_resto = len(categorias) - n_disc

    elegidas_disc: list[ButacaPlan] = []
    for b in wheelchair:
        if len(elegidas_disc) >= n_disc:
            break
        if b.id_seat not in ocupadas:
            elegidas_disc.append(b)
            ocupadas.add(b.id_seat)

    faltan_disc = n_disc - len(elegidas_disc)
    necesarias_reg = n_resto + faltan_disc
    elegidas_reg: list[ButacaPlan] = []

    if necesarias_reg > 0:
        # Intentamos sentar al grupo junto en la misma fila central
        for fila in filas_regulares:
            libres = [b for b in fila if b.id_seat not in ocupadas]
            if len(libres) < necesarias_reg:
                continue
            # Buscamos subsecuencia contigua más cercana al centro de la fila
            mejor_bloque: list[ButacaPlan] | None = None
            centro_col = (len(fila) + 1) / 2.0
            mejor_dist = 1e9
            for idx in range(len(libres) - necesarias_reg + 1):
                bloque = libres[idx : idx + necesarias_reg]
                if bloque[-1].column_number - bloque[0].column_number == necesarias_reg - 1:
                    col_media = (bloque[0].column_number + bloque[-1].column_number) / 2.0
                    dist = abs(col_media - centro_col)
                    if dist < mejor_dist:
                        mejor_dist = dist
                        mejor_bloque = bloque
            if mejor_bloque is not None:
                elegidas_reg = mejor_bloque
                break

        # Si no hubo bloque contiguo exacto, tomamos las libres en orden de filas centrales
        if not elegidas_reg:
            for fila in filas_regulares:
                for b in fila:
                    if b.id_seat not in ocupadas:
                        elegidas_reg.append(b)
                        if len(elegidas_reg) == necesarias_reg:
                            break
                if len(elegidas_reg) == necesarias_reg:
                    break

        # Y si aún faltan, completamos con butacas wheelchair libres
        if len(elegidas_reg) < necesarias_reg:
            for b in wheelchair:
                if b.id_seat not in ocupadas:
                    elegidas_reg.append(b)
                    if len(elegidas_reg) == necesarias_reg:
                        break

        for b in elegidas_reg:
            ocupadas.add(b.id_seat)

    # las primeras n_resto son para las categorías regulares y las últimas para DISCAPACITADO
    return elegidas_reg[:n_resto] + elegidas_disc + elegidas_reg[n_resto:]


def _sortear_categorias(
    tamano: int, es_animacion: bool, parametros: Parametros, rng: np.random.Generator
) -> list[str]:
    p_nino = parametros.nino_animacion if es_animacion else parametros.nino_resto
    p_mayor = parametros.adulto_mayor
    p_disc = parametros.discapacitado
    p_adulto = max(0.0, 1.0 - p_nino - p_mayor - p_disc)
    probs = (p_adulto, p_nino, p_mayor, p_disc)

    cats = [
        tarifas.CATEGORIAS[int(i)]
        for i in rng.choice(len(tarifas.CATEGORIAS), size=tamano, p=probs)
    ]
    # En grupos de 2 o más entradas con niños, aseguramos al menos un adulto o adulto mayor
    if tamano >= 2 and all(c == "NINO" for c in cats):
        cats[0] = "ADULTO"
    cats.sort(key=ORDEN_TARIFAS.__getitem__)
    return cats


def _sortear_snacks(
    n_entradas: int,
    fecha_compra: date,
    combos: list[ProductoPlan],
    otros_snacks: list[ProductoPlan],
    parametros: Parametros,
    rng: np.random.Generator,
) -> list[tuple[ProductoPlan, int, Decimal]]:
    if n_entradas == 0:
        # Pedido solo de confitería: de 1 a 3 líneas
        n_lineas = int(rng.choice((1, 2, 3), p=(0.50, 0.35, 0.15)))
        todos = combos + otros_snacks
        indices = rng.choice(len(todos), size=min(n_lineas, len(todos)), replace=False)
        lineas = []
        for idx in indices:
            prod = todos[int(idx)]
            cant = 1 if float(rng.random()) < 0.78 else 2
            lineas.append((prod, cant, prod.precio_en(fecha_compra)))
        return lineas

    if n_entradas == 1:
        prob_snack = parametros.prob_snack_1_entrada
        prob_combo = parametros.prob_combo_1_entrada
    elif n_entradas == 2:
        prob_snack = parametros.prob_snack_2_entradas
        prob_combo = parametros.prob_combo_2_entradas
    else:
        prob_snack = parametros.prob_snack_3_o_mas
        prob_combo = parametros.prob_combo_3_o_mas

    if float(rng.random()) >= prob_snack:
        return []

    seleccionados: list[ProductoPlan] = []
    if float(rng.random()) < prob_combo and combos:
        seleccionados.append(combos[int(rng.integers(0, len(combos)))])
        if float(rng.random()) < 0.30 and otros_snacks:
            seleccionados.append(otros_snacks[int(rng.integers(0, len(otros_snacks)))])
    else:
        n_otros = 1 if float(rng.random()) < 0.65 else 2
        indices = rng.choice(len(otros_snacks), size=min(n_otros, len(otros_snacks)), replace=False)
        for idx in indices:
            seleccionados.append(otros_snacks[int(idx)])

    lineas = []
    for prod in seleccionados:
        cant = 1 if (prod.id_snack_category == 2 or float(rng.random()) < 0.75) else 2
        lineas.append((prod, cant, prod.precio_en(fecha_compra)))
    return lineas


@dataclass
class _VentaPreliminar:
    instante_utc: datetime
    momento_lima: datetime
    orden: int
    cliente: ClientePlan
    funcion: FuncionPlan | None
    pelicula: PeliculaPlan | None
    sala: SalaPlan | None
    id_venue: int
    venue_name: str
    entradas_info: list[tuple[ButacaPlan, str, Decimal]]
    snacks_info: list[tuple[ProductoPlan, int, Decimal]]
    metodo_pago: str
    intento_cupon: bool
    qr: str


class _SelectorClientes:
    def __init__(self, clientes: list[ClientePlan], factor_cumpleanos: float):
        self.clientes = clientes
        self.factor_cumpleanos = factor_cumpleanos
        self.pesos = np.array([c.peso for c in clientes], dtype=np.float64)
        self.altas = np.array([c.fecha_alta.toordinal() for c in clientes], dtype=np.int32)
        self.por_cumple: dict[tuple[int, int], list[int]] = defaultdict(list)
        for idx, c in enumerate(clientes):
            if c.datebirth is not None:
                self.por_cumple[(c.datebirth.month, c.datebirth.day)].append(idx)
                if c.datebirth.month == 2 and c.datebirth.day == 29:
                    self.por_cumple[(2, 28)].append(idx)

        # Precalculamos la distribución acumulada base para cuando todos están activos
        self._cache_dia: dict[int, tuple[np.ndarray, np.ndarray, float]] = {}

    def _distribucion_fecha(self, ordinal_compra: int) -> tuple[np.ndarray, np.ndarray, float]:
        if ordinal_compra not in self._cache_dia:
            mask = self.altas <= ordinal_compra
            indices = np.nonzero(mask)[0]
            pesos_activos = self.pesos[indices]
            acum = np.cumsum(pesos_activos)
            total = float(acum[-1])
            self._cache_dia[ordinal_compra] = (indices, acum, total)
        return self._cache_dia[ordinal_compra]

    def elegir(
        self, fecha_compra: date, fecha_referencia_cumple: date, rng: np.random.Generator
    ) -> ClientePlan:
        ord_compra = fecha_compra.toordinal()
        indices, acum, total = self._distribucion_fecha(ord_compra)

        # Con probabilidad proporcional al refuerzo de cumpleaños, miramos a los cumpleañeros del día
        cumpleaneros = [
            idx
            for idx in self.por_cumple.get(
                (fecha_referencia_cumple.month, fecha_referencia_cumple.day), ()
            )
            if self.altas[idx] <= ord_compra
        ]
        if cumpleaneros:
            peso_extra = (self.factor_cumpleanos - 1.0) * float(self.pesos[cumpleaneros].sum())
            u = float(rng.random()) * (total + peso_extra)
            if u >= total:
                pesos_c = self.pesos[cumpleaneros]
                probs_c = pesos_c / pesos_c.sum()
                elegido_c = int(rng.choice(cumpleaneros, p=probs_c))
                return self.clientes[elegido_c]
        else:
            u = float(rng.random()) * total

        pos = int(np.searchsorted(acum, u, side="right"))
        pos = min(pos, len(indices) - 1)
        return self.clientes[int(indices[pos])]


def _instante_compra_funcion(
    funcion: FuncionPlan,
    es_semana_estreno: bool,
    desde: date,
    hasta: date,
    rng: np.random.Generator,
) -> datetime | None:
    # Días de anticipación (0 = mismo día de la función)
    u = float(rng.random())
    if es_semana_estreno:
        if u < 0.38:
            dias_ant = 0
        elif u < 0.78:
            dias_ant = int(rng.integers(1, 4))
        else:
            dias_ant = int(rng.integers(4, 15))
    else:
        if u < 0.58:
            dias_ant = 0
        elif u < 0.90:
            dias_ant = int(rng.integers(1, 4))
        else:
            dias_ant = int(rng.integers(4, 11))

    fecha_min = max(desde, funcion.fecha_creacion, funcion.fecha - timedelta(days=29))
    fecha_compra = max(fecha_min, funcion.fecha - timedelta(days=dias_ant))

    # Ninguna compra puede ocurrir fuera de [desde, hasta]
    if fecha_compra > hasta or fecha_compra > funcion.fecha:
        return None

    min_inicio_funcion = funcion.hora_inicio.hour * 60 + funcion.hora_inicio.minute
    if fecha_compra == funcion.fecha:
        # Entre las 07:00 y 5 minutos antes del inicio de la función
        max_min = min_inicio_funcion - 5
        min_min = 7 * 60
        if max_min <= min_min:
            min_compra = max(0, max_min)
        else:
            # Más compras en las 3 horas previas a la función
            if float(rng.random()) < 0.65:
                desde_cerca = max(min_min, max_min - 180)
                min_compra = int(rng.integers(desde_cerca, max_min + 1))
            else:
                min_compra = int(rng.integers(min_min, max_min + 1))
    else:
        # Entre las 07:00 y las 23:45 (hora de Lima)
        min_compra = int(rng.integers(7 * 60, 23 * 60 + 46))

    segundo = int(rng.integers(0, 60))
    return datetime.combine(fecha_compra, time(min_compra // 60, min_compra % 60, segundo))


def generar_demanda(
    catalogo: CatalogoPlan,
    funciones: list[FuncionPlan],
    parametros: Parametros,
    desde: date,
    hasta: date,
    escala: float,
    rng: np.random.Generator,
) -> tuple[list[TransaccionPlan], int, int]:
    feriados = cargar_feriados()
    temporadas = cargar_temporadas()

    sedes_por_id = {s.id_venue: s for s in catalogo.sedes}
    salas_por_id = {r.id_room: r for r in catalogo.salas}
    peliculas_por_id = {p.id_hex: p for p in catalogo.peliculas}

    butacas_por_sala: dict[int, list[ButacaPlan]] = defaultdict(list)
    for b in catalogo.butacas:
        butacas_por_sala[b.id_room].append(b)

    estructura_salas = {
        id_room: _organizar_butacas_sala(lista, salas_por_id[id_room].num_rows)
        for id_room, lista in butacas_por_sala.items()
    }

    combos = [p for p in catalogo.productos if p.id_snack_category == 2 and p.status == "Activo"]
    otros_snacks = [
        p for p in catalogo.productos if p.id_snack_category != 2 and p.status == "Activo"
    ]

    selector_clientes = _SelectorClientes(catalogo.clientes, parametros.factor_cumpleanos)

    # Calculamos el atractivo bruto por función para normalizar su media a 1.0
    funciones_programadas = [f for f in funciones if f.status == "Programada"]
    atractivos_brutos: list[float] = []
    for f in funciones_programadas:
        peli = peliculas_por_id[f.movie_id]
        semana = max(0, (f.fecha - peli.fecha_estreno).days // 7)
        atractivos_brutos.append(peli.popularidad * (parametros.retencion_semanal**semana))
    media_atractivo = float(np.mean(atractivos_brutos)) if atractivos_brutos else 1.0

    preliminares: list[_VentaPreliminar] = []
    orden_seq = 0
    r_dispersion = parametros.dispersion_binomial_negativa

    for f, atractivo_b in zip(funciones_programadas, atractivos_brutos, strict=True):
        sala = salas_por_id[f.id_room]
        sede = sedes_por_id[f.id_venue]
        pelicula = peliculas_por_id[f.movie_id]
        capacidad = sala.capacity

        f_dia = parametros.factor_dia_semana[f.fecha.isoweekday()]
        f_hora = parametros.factor_hora(f.hora_inicio.hour)
        nombre_temp = _temporada_de(f.fecha, temporadas)
        f_temp = parametros.factor_temporada.get(nombre_temp, 1.0)
        f_feriado = parametros.factor_feriado if f.fecha in feriados else 1.0
        atractivo = atractivo_b / media_atractivo

        esperadas = (
            capacidad
            * parametros.ocupacion_base
            * f_dia
            * f_hora
            * f_temp
            * f_feriado
            * atractivo
            * escala
        )
        if esperadas <= 0.01:
            continue

        # Binomial negativa con media = esperadas y dispersión = r_dispersion
        p_nb = r_dispersion / (r_dispersion + esperadas)
        lam_gamma = float(rng.gamma(r_dispersion, (1.0 - p_nb) / p_nb))
        objetivo_entradas = min(capacidad, int(rng.poisson(lam_gamma)))
        if objetivo_entradas <= 0:
            continue

        es_semana_estreno = (f.fecha - pelicula.fecha_estreno).days < 7
        filas_reg, wheelchair = estructura_salas[f.id_room]
        ocupadas: set[int] = set()
        vendidas_funcion = 0

        restantes = objetivo_entradas
        while restantes > 0:
            tamano = int(rng.choice(parametros.tamanos_grupo, p=parametros.pesos_grupo))
            tamano = min(tamano, restantes, capacidad - vendidas_funcion)
            if tamano <= 0:
                break
            restantes -= tamano

            momento_lima = _instante_compra_funcion(f, es_semana_estreno, desde, hasta, rng)
            if momento_lima is None:
                continue

            categorias = _sortear_categorias(tamano, pelicula.es_animacion, parametros, rng)
            butacas_grupo = _elegir_butacas_grupo(categorias, filas_reg, wheelchair, ocupadas)
            if len(butacas_grupo) < tamano:
                break

            precio_base = f.precio_decimal
            entradas_info = [
                (butaca, cat, tarifas.precio(precio_base, cat))
                for butaca, cat in zip(butacas_grupo, categorias, strict=True)
            ]
            snacks_info = _sortear_snacks(
                tamano, momento_lima.date(), combos, otros_snacks, parametros, rng
            )
            cliente = selector_clientes.elegir(momento_lima.date(), f.fecha, rng)
            metodo = "YAPE" if float(rng.random()) < parametros.prob_yape else "TARJETA"
            intento_cupon = float(rng.random()) < parametros.prob_cupon_app10
            qr = codigo_qr(rng)
            instante_utc = momento_lima + timedelta(hours=5)

            preliminares.append(
                _VentaPreliminar(
                    instante_utc=instante_utc,
                    momento_lima=momento_lima,
                    orden=orden_seq,
                    cliente=cliente,
                    funcion=f,
                    pelicula=pelicula,
                    sala=sala,
                    id_venue=sede.id_venue,
                    venue_name=sede.name_venue,
                    entradas_info=entradas_info,
                    snacks_info=snacks_info,
                    metodo_pago=metodo,
                    intento_cupon=intento_cupon,
                    qr=qr,
                )
            )
            orden_seq += 1
            vendidas_funcion += tamano

        f.sold_seats = vendidas_funcion
        f.available_seats = capacidad - vendidas_funcion

    # Pedidos solo de confitería (alrededor del 5 % del total de ventas)
    total_con_entradas = len(preliminares)
    objetivo_solo_snacks = max(
        1,
        round(
            total_con_entradas
            * parametros.proporcion_solo_confiteria
            / (1.0 - parametros.proporcion_solo_confiteria)
        ),
    )
    dias_ventana = (hasta - desde).days + 1
    for _ in range(objetivo_solo_snacks):
        dia_compra = desde + timedelta(days=int(rng.integers(0, dias_ventana)))
        sedes_abiertas = [
            s for s in catalogo.sedes if not s.es_nueva or dia_compra >= s.created_at.date()
        ]
        sede = sedes_abiertas[int(rng.integers(0, len(sedes_abiertas)))]
        min_compra = int(rng.integers(10 * 60, 22 * 60 + 30))
        segundo = int(rng.integers(0, 60))
        momento_lima = datetime.combine(
            dia_compra, time(min_compra // 60, min_compra % 60, segundo)
        )
        instante_utc = momento_lima + timedelta(hours=5)

        snacks_info = _sortear_snacks(0, dia_compra, combos, otros_snacks, parametros, rng)
        cliente = selector_clientes.elegir(dia_compra, dia_compra, rng)
        metodo = "YAPE" if float(rng.random()) < parametros.prob_yape else "TARJETA"
        qr = codigo_qr(rng)

        preliminares.append(
            _VentaPreliminar(
                instante_utc=instante_utc,
                momento_lima=momento_lima,
                orden=orden_seq,
                cliente=cliente,
                funcion=None,
                pelicula=None,
                sala=None,
                id_venue=sede.id_venue,
                venue_name=sede.name_venue,
                entradas_info=[],
                snacks_info=snacks_info,
                metodo_pago=metodo,
                intento_cupon=False,
                qr=qr,
            )
        )
        orden_seq += 1

    # Ordenar cronológicamente para evaluar promociones y asignar IDs
    preliminares.sort(key=lambda p: (p.instante_utc, p.orden))

    contador_usos = ContadorDeUsos()
    transacciones: list[TransaccionPlan] = []
    id_tx = 1
    id_ticket = 1
    id_detail = 1

    for pre in preliminares:
        if pre.funcion is not None and pre.pelicula is not None:
            fecha_f = pre.funcion.fecha
            hora_f = pre.funcion.hora_inicio
            estreno_f = pre.pelicula.fecha_estreno
        else:
            fecha_f = pre.momento_lima.date()
            hora_f = pre.momento_lima.time()
            estreno_f = None

        entradas_motor = tuple(Entrada(cat, precio) for _, cat, precio in pre.entradas_info)
        snacks_motor = tuple(
            Snack(prod.id_snack, prod.id_snack_category, precio_u, cant)
            for prod, cant, precio_u in pre.snacks_info
        )
        venta_motor = Venta(
            fecha_funcion=fecha_f,
            hora_funcion=hora_f,
            estreno=estreno_f,
            cliente=Cliente(pre.cliente.datebirth),
            cupon="APP10" if pre.intento_cupon else None,
            entradas=entradas_motor,
            snacks=snacks_motor,
        )

        usos = contador_usos.usos(pre.cliente.id_user, pre.momento_lima, catalogo.promociones)
        resultado = evaluar(venta_motor, catalogo.promociones, usos)
        id_promo = resultado.promocion.id if resultado.promocion is not None else None
        contador_usos.registrar(pre.cliente.id_user, id_promo, pre.instante_utc)

        entradas_plan: list[EntradaVentaPlan] = []
        for (butaca, cat, precio_e), desc_e in zip(
            pre.entradas_info, resultado.descuentos_entradas, strict=True
        ):
            entradas_plan.append(
                EntradaVentaPlan(
                    id_ticket=id_ticket,
                    id_transaction=id_tx,
                    id_showtime=pre.funcion.id_hex,
                    id_seat=butaca.id_seat,
                    seat_code=butaca.codigo,
                    fare_category=cat,
                    ticket_price=precio_e,
                    discount_amount=desc_e,
                    is_used=False,
                )
            )
            id_ticket += 1

        snacks_plan: list[SnackVentaPlan] = []
        for (prod, cant, precio_u), desc_s in zip(
            pre.snacks_info, resultado.descuentos_snacks, strict=True
        ):
            snacks_plan.append(
                SnackVentaPlan(
                    id_detail=id_detail,
                    id_transaction=id_tx,
                    id_snack=prod.id_snack,
                    snack_name=prod.name_snack,
                    quantity=cant,
                    unit_price=precio_u,
                    discount_amount=desc_s,
                    is_delivered=False,
                )
            )
            id_detail += 1

        subtotal = venta_motor.subtotal
        descuento = resultado.descuento
        total = subtotal - descuento

        transacciones.append(
            TransaccionPlan(
                id_transaction=id_tx,
                id_user=pre.cliente.id_user,
                id_transaction_status=catalogo.id_estado_completado,
                subtotal=subtotal,
                discount_amount=descuento,
                total_amount=total,
                payment_method=pre.metodo_pago,
                created_at=pre.instante_utc,
                payment_date=pre.instante_utc,
                qr_code_data=pre.qr,
                id_promotion=id_promo,
                id_showtime=pre.funcion.id_hex if pre.funcion else None,
                id_venue=pre.id_venue,
                movie_title=pre.pelicula.title_movie if pre.pelicula else None,
                show_date=pre.funcion.fecha if pre.funcion else None,
                start_time=pre.funcion.hora_inicio if pre.funcion else None,
                room_name=pre.sala.name_room if pre.sala else None,
                venue_name=pre.venue_name,
                entradas=tuple(entradas_plan),
                snacks=tuple(snacks_plan),
            )
        )
        id_tx += 1

    return transacciones, id_ticket - 1, id_detail - 1
