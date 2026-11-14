"""Las pruebas de esta carpeta revisan lo que dejó el generador en las 5 bases.

Se saltan si las bases están apagadas o todavía no tienen ventas.
Solo ellas: uv run pytest -m aceptacion
"""

import psycopg
import pymysql
import pytest
from apoyo import Datos, cargar
from pymongo.errors import PyMongoError


@pytest.fixture(scope="session")
def datos() -> Datos:
    try:
        cargados = cargar()
    except (psycopg.Error, pymysql.Error, PyMongoError, RuntimeError) as error:
        pytest.skip(f"Las bases no responden: {error}")
    if not cargados.ventas:
        pytest.skip("Todavía no hay ventas: corre el generador primero")
    return cargados


def pytest_collection_modifyitems(items):
    for item in items:
        if "aceptacion" in item.path.parts:
            item.add_marker(pytest.mark.aceptacion)
