"""Con la misma semilla, el generador planifica exactamente lo mismo."""

import importlib.util
import os
import subprocess
import sys

import psycopg
import pytest

from cinemax_analytics.fuentes import FUENTES, conectar_postgres

VENTANA = ["--desde", "2026-01-05", "--hasta", "2026-01-18"]


def _huella(semilla: int) -> str:
    resultado = subprocess.run(
        [sys.executable, "-m", "cinemax_analytics.generador", "--semilla", str(semilla), *VENTANA,
         "--simular"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        env={**os.environ, "PYTHONUTF8": "1"},
        timeout=900,
        check=False,
    )  # fmt: skip
    assert resultado.returncode == 0, resultado.stderr[-2000:]
    lineas = [ln for ln in resultado.stdout.splitlines() if ln.startswith("huella:")]
    assert len(lineas) == 1, resultado.stdout[-2000:]
    return lineas[0].split(":", 1)[1].strip()


def test_misma_semilla_misma_huella():
    if importlib.util.find_spec("cinemax_analytics.generador.__main__") is None:
        pytest.skip("Todavía no existe el generador")
    try:
        conectar_postgres(FUENTES["facturacion"]).close()
    except psycopg.Error as error:
        pytest.skip(f"Las bases no responden: {error}")

    primera, segunda, otra = _huella(42), _huella(42), _huella(43)
    assert primera == segunda
    assert primera != otra
