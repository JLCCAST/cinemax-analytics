from decimal import Decimal

from cinemax_analytics.agente.comparar import coinciden


def test_columnas_y_filas_en_otro_orden():
    referencia = [("Miraflores", Decimal("1.50")), ("Surco", Decimal("2.00"))]
    agente = [(2.0, "surco"), (1.5, "MIRAFLORES")]
    assert coinciden(referencia, agente)


def test_el_agente_puede_traer_columnas_de_mas():
    assert coinciden([("Comedia",)], [("Comedia", 1_010_000.5)])


def test_porcentaje_como_fraccion_o_por_cien():
    assert coinciden([(Decimal("57.87"),)], [(0.5787,)])
    assert coinciden([(0.5787,)], [(57.9,)])


def test_redondeo_dentro_de_la_tolerancia():
    assert coinciden([(41.831150,)], [(41.83,)])
    assert not coinciden([(41.83,)], [(43.0,)])


def test_un_ranking_mas_largo_vale_si_el_primero_coincide():
    assert coinciden([("A",)], [("A", 10), ("B", 5)])
    assert not coinciden([("B",)], [("A", 10), ("B", 5)])


def test_faltan_filas():
    assert not coinciden([("A",), ("B",)], [("A",)])


def test_texto_sin_tildes_ni_mayusculas():
    assert coinciden([("Sábado",)], [("sabado",)])
    assert not coinciden([("Martes",)], [("Sábado",)])
