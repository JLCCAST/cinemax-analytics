from decimal import Decimal

import pytest

from cinemax_analytics.generador.tarifas import NINO, REDUCIDA, aplicar, precio


# Los mismos casos de TarifasTest.java en cartelera-service.
@pytest.mark.parametrize(
    ("base", "nino", "reducida"),
    [
        ("25.00", "14.00", "16.50"),
        ("20.00", "11.00", "13.00"),
        ("15.00", "8.50", "10.00"),
        ("30.00", "16.50", "19.50"),
        ("18.00", "10.00", "11.50"),
        ("10.00", "5.50", "6.50"),
        ("0.00", "0.00", "0.00"),
    ],
)
def test_cada_entrada_es_un_porcentaje_del_precio_base(base, nino, reducida):
    assert aplicar(Decimal(base), NINO) == Decimal(nino)
    assert aplicar(Decimal(base), REDUCIDA) == Decimal(reducida)


def test_precio_por_categoria():
    assert precio(Decimal(20), "ADULTO") == Decimal("20.00")
    assert precio(Decimal("20.00"), "NINO") == Decimal("11.00")
    assert precio(Decimal("20.00"), "ADULTO_MAYOR") == Decimal("13.00")
    assert precio(Decimal("20.00"), "DISCAPACITADO") == Decimal("13.00")


def test_categoria_desconocida():
    with pytest.raises(ValueError):
        precio(Decimal("20.00"), "ESTUDIANTE")
