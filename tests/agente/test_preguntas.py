"""Las consultas de referencia corren con el rol del agente y devuelven algo.

Se saltan si el warehouse está apagado o el rol todavía no existe (agente.preparar).
"""

import psycopg
import pytest

from cinemax_analytics.agente.evaluar import cargar_preguntas
from cinemax_analytics.agente.grafo import EJEMPLOS
from cinemax_analytics.agente.herramientas import correr, vistas_disponibles

PREGUNTAS = cargar_preguntas()


@pytest.fixture(scope="module")
def warehouse():
    try:
        vistas_disponibles()
    except (psycopg.OperationalError, RuntimeError) as error:
        pytest.skip(f"Warehouse o rol del agente no disponibles: {error}")


def test_hay_25_preguntas_bien_repartidas():
    assert len(PREGUNTAS) == 25
    assert len({p["id"] for p in PREGUNTAS}) == 25
    por_dificultad = {}
    for p in PREGUNTAS:
        por_dificultad[p["dificultad"]] = por_dificultad.get(p["dificultad"], 0) + 1
    assert por_dificultad == {"facil": 10, "media": 8, "dificil": 4, "sin_datos": 3}


def test_las_preguntas_no_estan_en_los_ejemplos_del_prompt():
    for p in PREGUNTAS:
        assert p["pregunta"] not in EJEMPLOS


@pytest.mark.parametrize(
    "pregunta", [p for p in PREGUNTAS if p.get("respondible", True)], ids=lambda p: str(p["id"])
)
def test_la_referencia_corre_y_devuelve_filas(pregunta, warehouse):
    columnas, filas, _ = correr(pregunta["sql"], limite=None)
    assert columnas
    assert filas
    assert all(v is not None for fila in filas for v in fila)
