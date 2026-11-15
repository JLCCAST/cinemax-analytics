"""Imprime el reporte de calidad que deja dbt en calidad.calidad_deteccion.

Correr después de: extracción y dbt build. Sale con código 1 si algún chequeo no
coincide con lo inyectado (sin defectos, con lo esperado: cero).
"""

import sys

from cinemax_analytics.fuentes import conectar_dwh


def main() -> int:
    with conectar_dwh() as dwh:
        filas = dwh.execute(
            "SELECT chequeo, tipo, filas_inyectadas, filas_detectadas, filas_revisadas, coincide "
            "FROM calidad.calidad_deteccion ORDER BY tipo, chequeo"
        ).fetchall()

    print(f"{'chequeo':<34} {'tipo':<12} {'inyectadas':>10} {'detectadas':>10} {'revisadas':>10}")
    for chequeo, tipo, inyectadas, detectadas, revisadas, coincide in filas:
        marca = "" if coincide else "  <- no coincide"
        print(f"{chequeo:<34} {tipo:<12} {inyectadas:>10} {detectadas:>10} {revisadas:>10}{marca}")
    fallas = [f[0] for f in filas if not f[5]]
    print(f"\n{len(filas) - len(fallas)} de {len(filas)} chequeos coinciden.")
    return 1 if fallas else 0


if __name__ == "__main__":
    sys.exit(main())
