"""Los casos de PromotionEngineTest.java, con las 6 promociones de V5."""

from dataclasses import replace
from datetime import date, datetime, time, timedelta
from decimal import Decimal

import pytest

from cinemax_analytics.generador.promociones import (
    Cliente,
    ContadorDeUsos,
    Entrada,
    Promocion,
    Snack,
    Venta,
    evaluar,
)

MARTES = date(2026, 11, 17)
MIERCOLES = date(2026, 11, 18)
JUEVES = date(2026, 11, 19)
VIERNES = date(2026, 11, 20)

ADULTO = Entrada("ADULTO", Decimal("20.00"))
NINO = Entrada("NINO", Decimal("9.00"))

BEBIDAS = 1
COMBOS = 2


def promo(id, nombre, tipo, alcance, **ajustes) -> Promocion:
    base = {
        "vigente_desde": date(2025, 7, 1),
        "vigente_hasta": date(2026, 12, 31),
        "alcance": alcance,
        "compra_minima": Decimal(0),
        "entradas_minimas": 1,
        "excluye_estrenos": False,
        "estado": "Activo",
        "prioridad": 0,
    }
    base.update(ajustes)
    return Promocion(id=id, nombre=nombre, tipo=tipo, **base)


SEMILLA = [
    promo(1, "Miércoles de cine", "PORCENTAJE", "ENTRADAS",
          porcentaje=Decimal("50.00"), dias_semana="3", excluye_estrenos=True),
    promo(2, "Martes 2x1", "DOS_POR_UNO", "ENTRADAS", dias_semana="2", entradas_minimas=2),
    promo(3, "Matiné", "PORCENTAJE", "ENTRADAS",
          porcentaje=Decimal("20.00"), antes_de_hora=time(15, 0)),
    promo(4, "Combo + película", "MONTO_FIJO", "CONFITERIA",
          monto_fijo=Decimal("5.00"), entradas_minimas=2, categoria_requerida=COMBOS),
    promo(5, "Cumpleañero", "ENTRADA_GRATIS", "ENTRADAS",
          tope=Decimal("25.00"), condicion_cliente="CUMPLEANOS", usos_por_cliente=1),
    promo(6, "Cupón de la app", "PORCENTAJE", "TODO", codigo="APP10",
          porcentaje=Decimal("10.00"), tope=Decimal("15.00"), compra_minima=Decimal("40.00")),
]  # fmt: skip


def venta(fecha, hora, dias_desde_estreno, entradas=(), snacks=(), nacimiento=None, cupon=None):
    return Venta(
        fecha_funcion=fecha,
        hora_funcion=time.fromisoformat(hora),
        estreno=fecha - timedelta(days=dias_desde_estreno),
        cliente=Cliente(nacimiento) if nacimiento else None,
        cupon=cupon,
        entradas=tuple(entradas),
        snacks=tuple(Snack(i + 1, cat, Decimal(p), n) for i, (cat, p, n) in enumerate(snacks)),
    )


def aplica(resultado, nombre, descuento):
    assert resultado.aplico, f"Se esperaba {nombre}"
    assert resultado.promocion.nombre == nombre
    assert resultado.descuento == Decimal(descuento)


def no_aplica(resultado):
    assert not resultado.aplico, (
        f"No se esperaba {resultado.promocion and resultado.promocion.nombre}"
    )
    assert resultado.descuento == Decimal("0.00")


def test_miercoles_sin_estreno_aplica_miercoles_de_cine():
    aplica(
        evaluar(venta(MIERCOLES, "19:00", 30, [ADULTO, ADULTO]), SEMILLA),
        "Miércoles de cine",
        "20.00",
    )


def test_miercoles_con_estreno_no_aplica():
    no_aplica(evaluar(venta(MIERCOLES, "19:00", 3, [ADULTO, ADULTO]), SEMILLA))


def test_martes_dos_adultos_aplica_dos_por_uno():
    aplica(evaluar(venta(MARTES, "20:00", 30, [ADULTO, ADULTO]), SEMILLA), "Martes 2x1", "20.00")


def test_martes_adulto_y_nino_regala_la_mas_barata():
    aplica(evaluar(venta(MARTES, "20:00", 30, [ADULTO, NINO]), SEMILLA), "Martes 2x1", "9.00")


def test_martes_una_entrada_no_aplica():
    no_aplica(evaluar(venta(MARTES, "20:00", 30, [ADULTO]), SEMILLA))


def test_jueves_antes_de_las_15_aplica_matine():
    aplica(evaluar(venta(JUEVES, "13:00", 30, [ADULTO, ADULTO]), SEMILLA), "Matiné", "8.00")


def test_miercoles_de_matine_gana_el_mayor_descuento():
    aplica(
        evaluar(venta(MIERCOLES, "13:00", 30, [ADULTO, ADULTO]), SEMILLA),
        "Miércoles de cine",
        "20.00",
    )


def test_dos_entradas_y_un_combo_descuentan_en_confiteria():
    r = evaluar(venta(VIERNES, "20:00", 30, [ADULTO, ADULTO], [(COMBOS, "25.00", 1)]), SEMILLA)
    aplica(r, "Combo + película", "5.00")
    assert r.descuentos_entradas[0] == Decimal("0.00")
    assert r.descuentos_snacks[0] == Decimal("5.00")


def test_una_entrada_y_un_combo_no_aplica():
    no_aplica(evaluar(venta(VIERNES, "20:00", 30, [ADULTO], [(COMBOS, "25.00", 1)]), SEMILLA))


def test_cumpleanos_regala_la_entrada_mas_cara():
    v = venta(VIERNES, "20:00", 30, [ADULTO, ADULTO], nacimiento=VIERNES.replace(year=2000))
    aplica(evaluar(v, SEMILLA), "Cumpleañero", "20.00")


def test_cumpleanos_ya_usado_este_anio_no_aplica():
    v = venta(VIERNES, "20:00", 30, [ADULTO, ADULTO], nacimiento=VIERNES.replace(year=2000))
    no_aplica(evaluar(v, SEMILLA, {5: 1}))


def test_empate_gana_la_que_no_gasta_un_uso_limitado():
    v = venta(MARTES, "20:00", 30, [ADULTO, ADULTO], nacimiento=MARTES.replace(year=1999))
    aplica(evaluar(v, SEMILLA), "Martes 2x1", "20.00")


def test_cupon_con_subtotal_de_45():
    v = venta(VIERNES, "20:00", 30, [ADULTO], [(BEBIDAS, "12.50", 2)], cupon="APP10")
    aplica(evaluar(v, SEMILLA), "Cupón de la app", "4.50")


def test_cupon_respeta_su_tope():
    v = venta(VIERNES, "20:00", 30, [ADULTO] * 10, cupon="app10")
    aplica(evaluar(v, SEMILLA), "Cupón de la app", "15.00")


def test_cupon_bajo_la_compra_minima_no_aplica():
    v = venta(VIERNES, "20:00", 30, [ADULTO], [(BEBIDAS, "15.00", 1)], cupon="APP10")
    no_aplica(evaluar(v, SEMILLA))


def test_miercoles_gana_al_cupon():
    v = venta(MIERCOLES, "19:00", 30, [ADULTO, ADULTO], [(BEBIDAS, "15.00", 2)], cupon="APP10")
    aplica(evaluar(v, SEMILLA), "Miércoles de cine", "20.00")


def test_la_suma_por_linea_es_igual_al_descuento_total():
    v = venta(VIERNES, "20:00", 30, [ADULTO, NINO], [(BEBIDAS, "8.50", 3)], cupon="APP10")
    r = evaluar(v, SEMILLA)
    assert r.aplico
    assert sum(r.descuentos_entradas) + sum(r.descuentos_snacks) == r.descuento


def test_sin_sesion_no_aplica_el_cumpleanero():
    no_aplica(evaluar(venta(VIERNES, "20:00", 30, [ADULTO, ADULTO]), SEMILLA))


def test_el_29_de_febrero_se_celebra_el_28_en_anio_no_bisiesto():
    cumple = replace(SEMILLA[4], vigente_hasta=date(2027, 12, 31))
    v = venta(date(2027, 2, 28), "20:00", 30, [ADULTO], nacimiento=date(2000, 2, 29))
    aplica(evaluar(v, [cumple]), "Cumpleañero", "20.00")


def test_fuera_de_vigencia_no_aplica():
    no_aplica(evaluar(venta(date(2027, 1, 6), "19:00", 30, [ADULTO, ADULTO]), SEMILLA))


# ---- Casos propios del port --------------------------------------------------------------


def test_reparto_truncado_con_residuo_en_la_linea_mayor():
    # 10 % de 9.00 + 8.50 x 3 = 34.50 + 9.00... el cupón exige 40: se usan 3 entradas.
    v = venta(VIERNES, "20:00", 30, [NINO, ADULTO, NINO], [(BEBIDAS, "8.50", 1)], cupon="APP10")
    r = evaluar(v, SEMILLA)
    aplica(r, "Cupón de la app", "4.65")
    # 465 céntimos sobre 900, 2000, 900 y 850 (total 4650): 90, 200, 90, 85 -> suma exacta.
    assert r.descuentos_entradas == (Decimal("0.90"), Decimal("2.00"), Decimal("0.90"))
    assert r.descuentos_snacks == (Decimal("0.85"),)


def test_residuo_va_a_la_primera_linea_de_mayor_importe():
    v = venta(MARTES, "20:00", 30, [ADULTO, ADULTO, ADULTO], cupon="APP10")
    r = evaluar(v, [SEMILLA[5]])
    aplica(r, "Cupón de la app", "6.00")
    assert r.descuentos_entradas == (Decimal("2.00"),) * 3

    v = venta(VIERNES, "20:00", 30, [Entrada("ADULTO", Decimal("13.33"))] * 3, cupon="APP10")
    r = evaluar(v, [replace(SEMILLA[5], compra_minima=Decimal(0))])
    aplica(r, "Cupón de la app", "4.00")
    assert r.descuentos_entradas == (Decimal("1.34"), Decimal("1.33"), Decimal("1.33"))


def test_en_empate_total_gana_el_menor_id():
    a = promo(7, "A", "MONTO_FIJO", "ENTRADAS", monto_fijo=Decimal("3.00"))
    b = promo(8, "B", "MONTO_FIJO", "ENTRADAS", monto_fijo=Decimal("3.00"))
    aplica(evaluar(venta(VIERNES, "20:00", 30, [ADULTO]), [b, a]), "A", "3.00")


def test_mayor_prioridad_gana_el_empate():
    a = promo(7, "A", "MONTO_FIJO", "ENTRADAS", monto_fijo=Decimal("3.00"))
    b = promo(8, "B", "MONTO_FIJO", "ENTRADAS", monto_fijo=Decimal("3.00"), prioridad=5)
    aplica(evaluar(venta(VIERNES, "20:00", 30, [ADULTO]), [a, b]), "B", "3.00")


def test_pedido_solo_de_confiteria_no_tiene_promocion_con_la_semilla():
    # Las de entradas descuentan 0, y el cupón de V5 exige al menos una entrada.
    v = Venta(VIERNES, time(13, 0), None, Cliente(None), "APP10", (),
              (Snack(4, COMBOS, Decimal("45.00"), 1),))  # fmt: skip
    no_aplica(evaluar(v, SEMILLA))
    sin_minimo = replace(SEMILLA[5], entradas_minimas=None)
    aplica(evaluar(v, [sin_minimo]), "Cupón de la app", "4.50")


@pytest.mark.parametrize(
    ("compra_en_lima", "usos"),
    [(datetime(2026, 3, 1, 12, 0), 1), (datetime(2027, 1, 2, 12, 0), 0)],
)
def test_contador_de_usos_por_anio(compra_en_lima, usos):
    contador = ContadorDeUsos()
    contador.registrar(10, 5, datetime(2026, 1, 15, 18, 0))
    assert contador.usos(10, compra_en_lima, SEMILLA) == {5: usos}
    assert contador.usos(11, compra_en_lima, SEMILLA) == {5: 0}
