import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from bson import Decimal128, ObjectId

from cinemax_analytics.extraccion import COLUMNAS_EXCLUIDAS
from cinemax_analytics.extraccion.mongo import documento_json
from cinemax_analytics.extraccion.relacional import tipo_postgres, valor_mysql


@pytest.mark.parametrize(
    ("tipo", "precision", "escala", "columna", "esperado"),
    [
        ("int", 10, 0, "int", "integer"),
        ("int", 10, 0, "int unsigned", "bigint"),
        ("bigint", 19, 0, "bigint unsigned", "numeric(20,0)"),
        ("tinyint", 3, 0, "tinyint(1)", "smallint"),
        ("decimal", 10, 2, "decimal(10,2)", "numeric(10,2)"),
        ("varchar", None, None, "varchar(100)", "text"),
        ("datetime", None, None, "datetime", "timestamp without time zone"),
        ("time", None, None, "time", "time without time zone"),
        ("double", 22, None, "double", "double precision"),
    ],
)
def test_tipo_postgres(tipo, precision, escala, columna, esperado):
    assert tipo_postgres(tipo, precision, escala, columna) == esperado


def test_tipo_desconocido_falla():
    with pytest.raises(ValueError):
        tipo_postgres("geometry", None, None, "geometry")


def test_valor_mysql_convierte_time_y_bit():
    assert valor_mysql(timedelta(hours=14, minutes=30)) == "14:30:00"
    assert valor_mysql(b"\x01") == 1
    assert valor_mysql(Decimal("18.00")) == Decimal("18.00")


def test_no_se_extraen_datos_personales():
    excluidas = COLUMNAS_EXCLUIDAS[("usuarios", "user_account")]
    for columna in ("password", "email", "first_name", "last_name", "document_number", "phone"):
        assert columna in excluidas


def test_documento_json_conserva_tipos_de_mongo():
    documento = {
        "_id": ObjectId("6af8cf4a07c0aabdb1c9dc71"),
        "baseTicketPrice": Decimal128("18.00"),
        "startTime": datetime(2026, 11, 14, 14, 30, tzinfo=UTC),
        "availableSeats": 80,
    }
    resultado = json.loads(documento_json(documento))
    assert resultado["baseTicketPrice"] == {"$numberDecimal": "18.00"}
    assert resultado["startTime"] == {"$date": "2026-11-14T14:30:00Z"}
    assert resultado["availableSeats"] == 80
