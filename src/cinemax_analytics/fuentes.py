"""Conexiones a las 5 bases de CineMax y al warehouse, con los datos de .env."""

import os
import time
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote_plus

import psycopg
import pymysql
from dotenv import load_dotenv
from pymongo import MongoClient

RAIZ = Path(__file__).resolve().parents[2]
load_dotenv(RAIZ / ".env")

HOST = os.getenv("FUENTES_HOST", "127.0.0.1")


def _env(nombre: str) -> str:
    valor = os.getenv(nombre)
    if not valor:
        raise RuntimeError(f"Falta {nombre} en .env (copia .env.example)")
    return valor


@dataclass(frozen=True)
class Fuente:
    nombre: str
    motor: str  # postgres, mysql o mongo
    base: str
    variable_puerto: str
    puerto_defecto: int

    @property
    def puerto(self) -> int:
        return int(os.getenv(self.variable_puerto, self.puerto_defecto))

    @property
    def host(self) -> str:
        """Desde el PC, todas en 127.0.0.1; dentro de Docker (Airflow), cada una con su nombre."""
        return os.getenv(f"HOST_{self.nombre.upper()}", HOST)


FUENTES = {
    f.nombre: f
    for f in (
        Fuente("usuarios", "postgres", "usuarios_db", "PUERTO_USUARIOS", 15433),
        Fuente("facturacion", "postgres", "sales_db", "PUERTO_FACTURACION", 15434),
        Fuente("sucursales", "mysql", "sucursales_db", "PUERTO_SUCURSALES", 13307),
        Fuente("confiteria", "mysql", "confiteria_db", "PUERTO_CONFITERIA", 13308),
        Fuente("cartelera", "mongo", "cartelera_db", "PUERTO_CARTELERA", 27018),
    )
}


def conectar_postgres(fuente: Fuente) -> psycopg.Connection:
    return psycopg.connect(
        host=fuente.host,
        port=fuente.puerto,
        dbname=fuente.base,
        user=_env("FUENTES_USER"),
        password=_env("FUENTES_PASSWORD"),
    )


def conectar_mysql(fuente: Fuente, **opciones) -> pymysql.Connection:
    return pymysql.connect(
        host=fuente.host,
        port=fuente.puerto,
        database=fuente.base,
        user=_env("FUENTES_USER"),
        password=_env("FUENTES_PASSWORD"),
        charset="utf8mb4",
        **opciones,
    )


def conectar_mongo(fuente: Fuente = FUENTES["cartelera"]):
    usuario = quote_plus(_env("FUENTES_USER"))
    clave = quote_plus(_env("FUENTES_PASSWORD"))
    cliente = MongoClient(
        f"mongodb://{usuario}:{clave}@{fuente.host}:{fuente.puerto}/?authSource=admin",
        tz_aware=True,
    )
    return cliente[fuente.base]


def conectar_dwh() -> psycopg.Connection:
    return psycopg.connect(
        host=os.getenv("DWH_HOST", "127.0.0.1"),
        port=int(os.getenv("PUERTO_DWH", "5440")),
        dbname=os.getenv("DWH_DB", "cinemax_dwh"),
        user=_env("DWH_USER"),
        password=_env("DWH_PASSWORD"),
    )


def esperar(conectar, segundos: int = 120):
    """Reintenta la conexión mientras los contenedores terminan de arrancar."""
    limite = time.monotonic() + segundos
    while True:
        try:
            return conectar()
        except Exception:
            if time.monotonic() > limite:
                raise
            time.sleep(3)
