"""Precio de cada tipo de entrada, igual que Tarifas.java de cartelera-service."""

from decimal import ROUND_HALF_UP, Decimal

NINO = Decimal("0.55")
REDUCIDA = Decimal("0.65")  # adulto mayor y discapacitado

CATEGORIAS = ("ADULTO", "NINO", "ADULTO_MAYOR", "DISCAPACITADO")

_PORCENTAJES = {"NINO": NINO, "ADULTO_MAYOR": REDUCIDA, "DISCAPACITADO": REDUCIDA}
CENTIMO = Decimal("0.01")


def aplicar(base: Decimal, porcentaje: Decimal) -> Decimal:
    """Porcentaje del precio base, redondeado a S/ 0,50."""
    medios_soles = (base * porcentaje * 2).quantize(Decimal(1), rounding=ROUND_HALF_UP)
    return (medios_soles / 2).quantize(CENTIMO)


def precio(base: Decimal, categoria: str) -> Decimal:
    """Precio de una entrada de esa categoría para una función con ese precio base."""
    if categoria == "ADULTO":
        return Decimal(base).quantize(CENTIMO)
    if categoria not in _PORCENTAJES:
        raise ValueError(f"Categoría de entrada desconocida: {categoria}")
    return aplicar(Decimal(base), _PORCENTAJES[categoria])
