"""Conexión al warehouse con el rol de solo lectura del agente."""

import os

import psycopg

from cinemax_analytics import fuentes  # noqa: F401  (carga .env)

ROL = "agente"
TIEMPO_MAXIMO_MS = 5000


def conectar_agente() -> psycopg.Connection:
    clave = os.getenv("AGENTE_DWH_PASSWORD")
    if not clave:
        raise RuntimeError("Falta AGENTE_DWH_PASSWORD en .env (copia .env.example)")
    # El rol ya tiene estas opciones por defecto; se repiten por si alguien lo cambia.
    return psycopg.connect(
        host=os.getenv("DWH_HOST", "127.0.0.1"),
        port=int(os.getenv("PUERTO_DWH", "5440")),
        dbname=os.getenv("DWH_DB", "cinemax_dwh"),
        user=ROL,
        password=clave,
        options=(
            f"-c default_transaction_read_only=on -c statement_timeout={TIEMPO_MAXIMO_MS} "
            "-c search_path=semantic,public"
        ),
        autocommit=True,
        connect_timeout=5,
    )
