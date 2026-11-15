"""Las pruebas de esta carpeta revisan lo que dejó el generador en las 5 bases.

Se saltan si las bases están apagadas o todavía no tienen ventas.
Solo ellas: uv run pytest -m aceptacion
"""

import psycopg
import pymysql
import pytest
from apoyo import Datos, cargar
from pymongo.errors import PyMongoError

from cinemax_analytics.fuentes import conectar_dwh


@pytest.fixture(scope="session")
def datos() -> Datos:
    try:
        cargados = cargar()
    except (psycopg.Error, pymysql.Error, PyMongoError, RuntimeError) as error:
        pytest.skip(f"Las bases no responden: {error}")
    if not cargados.ventas:
        pytest.skip("Todavía no hay ventas: corre el generador primero")
    if _hay_defectos_inyectados():
        pytest.skip("Hay defectos inyectados a propósito: estas pruebas son para datos limpios")
    return cargados


def _hay_defectos_inyectados() -> bool:
    try:
        with conectar_dwh() as dwh:
            tabla = dwh.execute("SELECT to_regclass('raw._defectos_inyectados')").fetchone()[0]
            return (
                bool(tabla)
                and dwh.execute("SELECT count(*) FROM raw._defectos_inyectados").fetchone()[0] > 0
            )
    except psycopg.Error:
        return False


def pytest_collection_modifyitems(items):
    for item in items:
        if "aceptacion" in item.path.parts:
            item.add_marker(pytest.mark.aceptacion)
