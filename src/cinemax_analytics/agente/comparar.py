"""Compara el resultado del agente con el de la referencia, sin mirar el texto del SQL.

Cada columna de la referencia tiene que aparecer en el resultado del agente (en cualquier
orden de columnas y de filas), con la misma cantidad de filas. Los números se comparan con
tolerancia y un porcentaje vale igual como 57,9 que como 0,579.
"""

import math
import unicodedata
from datetime import date, datetime
from decimal import Decimal

TOLERANCIA = 0.005  # 0,5 % relativo


def _texto(valor) -> str:
    sin_tildes = unicodedata.normalize("NFKD", str(valor))
    return "".join(c for c in sin_tildes if not unicodedata.combining(c)).strip().lower()


def _numero(valor) -> float | None:
    if isinstance(valor, bool):
        return None
    if isinstance(valor, int | float | Decimal):
        return float(valor)
    return None


def _iguales(a: float, b: float) -> bool:
    return math.isclose(a, b, rel_tol=TOLERANCIA, abs_tol=0.01)


def _columnas_iguales(referencia: list, agente: list) -> bool:
    numeros_ref = [_numero(v) for v in referencia]
    numeros_agente = [_numero(v) for v in agente]
    if all(n is not None for n in numeros_ref) and all(n is not None for n in numeros_agente):
        ref, ag = sorted(numeros_ref), sorted(numeros_agente)
        for escala in (1, 100, 0.01):
            if all(_iguales(r * escala, a) for r, a in zip(ref, ag, strict=True)):
                return True
        return False

    def clave(valor):
        if isinstance(valor, date | datetime):
            return valor.isoformat()[:10]
        return _texto(valor)

    return sorted(map(clave, referencia)) == sorted(map(clave, agente))


def coinciden(referencia: list[tuple], agente: list[tuple]) -> bool:
    if len(referencia) != len(agente):
        return False
    if not referencia:
        return True
    columnas_ref = [list(c) for c in zip(*referencia, strict=True)]
    columnas_agente = [list(c) for c in zip(*agente, strict=True)]
    usadas: set[int] = set()
    for columna in columnas_ref:
        pareja = next(
            (
                i
                for i, candidata in enumerate(columnas_agente)
                if i not in usadas and _columnas_iguales(columna, candidata)
            ),
            None,
        )
        if pareja is None:
            return False
        usadas.add(pareja)
    return True
