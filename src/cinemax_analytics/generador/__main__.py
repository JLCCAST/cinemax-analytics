"""Línea de comandos para el generador de ventas sintéticas de CineMax."""

import argparse
import sys
from datetime import date

import numpy as np
import psycopg
import pymysql
from pymongo.errors import PyMongoError

from cinemax_analytics.generador.catalogo import generar_catalogo
from cinemax_analytics.generador.demanda import generar_demanda
from cinemax_analytics.generador.escritura import escribir_todo
from cinemax_analytics.generador.funciones import generar_funciones
from cinemax_analytics.generador.lectura import EstadoSemilla, leer_semilla
from cinemax_analytics.generador.modelo import PlanGeneracion, calcular_huella
from cinemax_analytics.generador.parametros import Parametros

ERRORES_CONOCIDOS = (
    psycopg.Error,
    pymysql.Error,
    PyMongoError,
    RuntimeError,
    ValueError,
    OSError,
)


def planificar(
    semilla_db: EstadoSemilla,
    semilla: int,
    desde: date,
    hasta: date,
    escala: float = 1.0,
    parametros: Parametros | None = None,
) -> PlanGeneracion:
    params = parametros or Parametros()
    rng_raiz = np.random.default_rng(semilla)
    rng_cat, rng_func, rng_dem = rng_raiz.spawn(3)

    catalogo = generar_catalogo(semilla_db, params, desde, hasta, semilla, rng_cat)
    funciones = generar_funciones(semilla_db, catalogo, params, desde, hasta, rng_func)
    ventas, n_entradas, n_snacks = generar_demanda(
        catalogo, funciones, params, desde, hasta, escala, rng_dem
    )
    return PlanGeneracion(
        semilla=semilla,
        desde=desde,
        hasta=hasta,
        escala=escala,
        catalogo=catalogo,
        funciones=funciones,
        ventas=ventas,
        total_entradas=n_entradas,
        total_lineas_snack=n_snacks,
    )


def _imprimir_resumen(plan: PlanGeneracion, huella: str) -> None:
    sedes_nuevas = sum(1 for s in plan.catalogo.sedes if s.es_nueva)
    salas_nuevas = sum(1 for r in plan.catalogo.salas if r.es_nueva)
    butacas_nuevas = sum(1 for b in plan.catalogo.butacas if b.es_nueva)
    productos_nuevos = sum(1 for p in plan.catalogo.productos if p.es_nuevo)

    print(f"venue (nuevas):          {sedes_nuevas:>9}")
    print(f"room (nuevas):           {salas_nuevas:>9}")
    print(f"seat (nuevas):           {butacas_nuevas:>9}")
    print(f"snack (nuevos):          {productos_nuevos:>9}")
    print(f"snack_venue_stock:       {len(plan.catalogo.stocks_nuevos):>9}")
    print(f"movies (nuevas):         {len(plan.catalogo.peliculas):>9}")
    print(f"showtimes (nuevas):      {len(plan.funciones):>9}")
    print(f"user_account (clientes): {len(plan.catalogo.clientes):>9}")
    print(f"sale_transaction:        {len(plan.ventas):>9}")
    print(f"sale_ticket_detail:      {plan.total_entradas:>9}")
    print(f"sale_snack_detail:       {plan.total_lineas_snack:>9}")
    print(f"huella: {huella}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m cinemax_analytics.generador",
        description="Genera un historial sintético en las 5 bases de origen de CineMax.",
    )
    parser.add_argument("--semilla", type=int, required=True, help="Semilla del generador.")
    parser.add_argument(
        "--desde", type=date.fromisoformat, required=True, help="Fecha inicial YYYY-MM-DD."
    )
    parser.add_argument(
        "--hasta", type=date.fromisoformat, required=True, help="Fecha final YYYY-MM-DD."
    )
    parser.add_argument(
        "--escala", type=float, default=1.0, help="Factor multiplicador de la demanda."
    )
    parser.add_argument(
        "--simular",
        action="store_true",
        help="Planifica e imprime la huella sin escribir en las bases.",
    )
    args = parser.parse_args(argv)

    if args.hasta < args.desde:
        print("Error: --hasta no puede ser anterior a --desde.", file=sys.stderr)
        return 1
    if args.escala <= 0:
        print("Error: --escala debe ser mayor que 0.", file=sys.stderr)
        return 1

    try:
        semilla_db = leer_semilla()
    except ERRORES_CONOCIDOS as exc:
        print(f"Error al leer las bases de origen: {exc}", file=sys.stderr)
        return 1

    if not args.simular and (
        semilla_db.ventas_existentes > 0 or semilla_db.peliculas_generadas_existentes > 0
    ):
        print(
            "Error: el entorno no está limpio (ya existen ventas o películas generadas). "
            "Recrea los volúmenes antes de volver a generar.",
            file=sys.stderr,
        )
        return 1

    try:
        plan = planificar(semilla_db, args.semilla, args.desde, args.hasta, args.escala)
        huella = calcular_huella(plan)
        if not args.simular:
            escribir_todo(plan)
    except ERRORES_CONOCIDOS as exc:
        print(f"Error durante la generación: {exc}", file=sys.stderr)
        return 1

    _imprimir_resumen(plan, huella)
    return 0


if __name__ == "__main__":
    sys.exit(main())
