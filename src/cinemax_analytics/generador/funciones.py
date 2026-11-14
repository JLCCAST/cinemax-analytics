"""Programación determinista de funciones por sala y día."""

from collections import defaultdict
from datetime import UTC, date, datetime, time, timedelta

import numpy as np

from cinemax_analytics.generador.lectura import EstadoSemilla
from cinemax_analytics.generador.modelo import (
    CatalogoPlan,
    FuncionPlan,
    PeliculaPlan,
    SalaPlan,
    object_id_determinista,
)
from cinemax_analytics.generador.parametros import Parametros

PRECIOS_BASE = {
    # (id_venue, es_vip): (matiné, tarde, noche_fds)
    (1, False): (12, 14, 16),
    (2, False): (16, 20, 22),
    (2, True): (24, 28, 30),
    (3, False): (16, 19, 22),
    (3, True): (24, 27, 30),
    (4, False): (13, 16, 18),
    (5, False): (13, 15, 18),
    (5, True): (22, 25, 28),
}


def _a_minutos(h: time) -> int:
    return h.hour * 60 + h.minute


def _de_minutos(m: int) -> time:
    return time(m // 60, m % 60)


def _se_cruza(inicio: int, fin: int, ocupados: list[tuple[int, int]]) -> bool:
    return any(not (fin <= o_ini or inicio >= o_fin) for o_ini, o_fin in ocupados)


def _precio_funcion(sala: SalaPlan, dia: date, min_inicio: int, rng: np.random.Generator) -> str:
    matine, tarde, noche = PRECIOS_BASE.get((sala.id_venue, sala.es_vip), (15, 18, 20))
    es_fds = dia.isoweekday() >= 5
    if min_inicio < 15 * 60:
        valor = matine + (2 if es_fds else 0)
    elif min_inicio >= 18 * 60 or es_fds:
        valor = noche
    else:
        valor = tarde

    # En ~20 % de los casos se formatea sin decimales ("20"), y el resto con ".00" o ".50"
    u = float(rng.random())
    if u < 0.20:
        return str(valor)
    if u < 0.30 and valor < 30:
        return f"{valor}.50"
    return f"{valor}.00"


def _peliculas_en_cartelera(
    peliculas: list[PeliculaPlan], dia: date
) -> tuple[list[PeliculaPlan], np.ndarray]:
    activas: list[PeliculaPlan] = []
    pesos: list[float] = []
    for p in peliculas:
        dias_estreno = (dia - p.fecha_estreno).days
        if 0 <= dias_estreno < p.semanas_cartelera * 7:
            semana = dias_estreno // 7
            # Peso suavizado para que toda película tenga suficientes funciones en semanas 0..3
            peso = (p.popularidad**0.55) * (0.82**semana)
            activas.append(p)
            pesos.append(peso)

    if not activas:
        previas = [p for p in peliculas if p.fecha_estreno <= dia]
        candidatas = previas[-6:] if previas else peliculas[:6]
        activas = list(candidatas)
        pesos = [1.0] * len(activas)

    arr = np.array(pesos, dtype=np.float64)
    return activas, arr / arr.sum()


def generar_funciones(
    semilla: EstadoSemilla,
    catalogo: CatalogoPlan,
    parametros: Parametros,
    desde: date,
    hasta: date,
    rng: np.random.Generator,
) -> list[FuncionPlan]:
    sedes_por_id = {s.id_venue: s for s in catalogo.sedes}
    salas_ordenadas = sorted(catalogo.salas, key=lambda r: r.id_room)

    # Intervalos ya ocupados por las 8 funciones del seed (con 15 min de margen)
    ocupados_seed: dict[tuple[int, date], list[tuple[int, int]]] = defaultdict(list)
    for fs in semilla.funciones_seed:
        ini = _a_minutos(fs.hora_inicio)
        fin = _a_minutos(fs.hora_fin) + 15
        ocupados_seed[(fs.id_room, fs.fecha)].append((ini, fin))

    # Programamos funciones hasta 10 días después de --hasta (dentro del tope de 21 días)
    fin_programacion = hasta + timedelta(days=10)
    total_dias = (fin_programacion - desde).days + 1

    funciones: list[FuncionPlan] = []

    for offset_dia in range(total_dias):
        dia = desde + timedelta(days=offset_dia)
        activas, probs_peliculas = _peliculas_en_cartelera(catalogo.peliculas, dia)
        n_activas = len(activas)
        show_date_utc = datetime.combine(dia, time(0, 0), tzinfo=UTC)

        for sala in salas_ordenadas:
            sede = sedes_por_id[sala.id_venue]
            if sede.es_nueva and dia < sede.created_at.date():
                continue

            ocupados = list(ocupados_seed.get((sala.id_room, dia), []))
            objetivo = int(rng.choice((4, 5, 6), p=(0.50, 0.35, 0.15)))

            # Primer inicio entre 10:00 y 11:00 (en múltiplos de 5 min)
            cursor_min = 10 * 60 + int(rng.integers(0, 13)) * 5
            creadas_en_sala = 0

            while creadas_en_sala < objetivo and cursor_min <= 22 * 60:
                idx_peli = int(rng.choice(n_activas, p=probs_peliculas))
                pelicula = activas[idx_peli]

                avances = int(rng.integers(0, 3)) * 5  # 0, 5 o 10 min
                duracion_total = pelicula.duration_minutes + avances
                fin_min = cursor_min + duracion_total

                # Si se pasa de las 23:55, probamos con una película activa más corta
                if fin_min > 23 * 60 + 55:
                    cortas = [p for p in activas if cursor_min + p.duration_minutes <= 23 * 60 + 55]
                    if not cortas:
                        break
                    pelicula = cortas[int(rng.integers(0, len(cortas)))]
                    avances = 0
                    duracion_total = pelicula.duration_minutes
                    fin_min = cursor_min + duracion_total

                limpieza = int(rng.integers(3, 5)) * 5  # 15 o 20 min
                if _se_cruza(cursor_min, fin_min + limpieza, ocupados):
                    cursor_min += 20
                    continue

                dias_antes = int(rng.integers(7, 22))
                fecha_creacion = dia - timedelta(days=dias_antes)
                hora_ini = _de_minutos(cursor_min)
                hora_fin = _de_minutos(fin_min)

                start_dt = datetime.combine(fecha_creacion, hora_ini, tzinfo=UTC)
                end_dt = datetime.combine(fecha_creacion, hora_fin, tzinfo=UTC)
                oid_instante = datetime.combine(
                    fecha_creacion,
                    time(int(rng.integers(8, 22)), int(rng.integers(0, 60))),
                    tzinfo=UTC,
                )
                oid = object_id_determinista(oid_instante, rng)

                if pelicula.es_animacion:
                    idioma = "Doblada" if float(rng.random()) < 0.92 else "Subtitulada"
                elif cursor_min < 17 * 60 or sala.id_venue in (1, 4, 5):
                    idioma = "Doblada" if float(rng.random()) < 0.72 else "Subtitulada"
                else:
                    idioma = "Subtitulada" if float(rng.random()) < 0.60 else "Doblada"

                precio_str = _precio_funcion(sala, dia, cursor_min, rng)
                cancelada = float(rng.random()) < parametros.tasa_cancelacion_funciones
                estado = "Cancelada" if cancelada else "Programada"

                funciones.append(
                    FuncionPlan(
                        id=oid,
                        show_date=show_date_utc,
                        start_time=start_dt,
                        end_time=end_dt,
                        language_format=idioma,
                        base_ticket_price=precio_str,
                        available_seats=sala.capacity,
                        status=estado,
                        movie_id=pelicula.id_hex,
                        id_room=sala.id_room,
                        id_venue=sala.id_venue,
                        sold_seats=0,
                    )
                )

                ocupados.append((cursor_min, fin_min + limpieza))
                holgura = int(rng.integers(0, 3)) * 5 if objetivo <= 5 else 0
                cursor_min = fin_min + limpieza + holgura
                creadas_en_sala += 1

    return funciones
