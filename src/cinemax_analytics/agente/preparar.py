"""uv run python -m cinemax_analytics.agente.preparar

Crea el rol de solo lectura del agente y las extensiones que usa buscar_valor.
Se corre una vez por entorno, después de dbt build. Los privilegios por defecto
hacen que las vistas que dbt vuelva a crear sigan siendo legibles para el agente.
"""

import os
import sys

from psycopg import sql

from cinemax_analytics.agente.conexion import ROL, TIEMPO_MAXIMO_MS
from cinemax_analytics.fuentes import conectar_dwh


def preparar() -> None:
    clave = os.getenv("AGENTE_DWH_PASSWORD")
    if not clave:
        raise RuntimeError("Falta AGENTE_DWH_PASSWORD en .env")

    with conectar_dwh() as dwh:
        dwh.autocommit = True
        dueno = dwh.execute("SELECT current_user").fetchone()[0]
        base = dwh.execute("SELECT current_database()").fetchone()[0]
        rol = sql.Identifier(ROL)

        dwh.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
        dwh.execute("CREATE EXTENSION IF NOT EXISTS unaccent")
        existe = dwh.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (ROL,)).fetchone()
        accion = "ALTER" if existe else "CREATE"
        dwh.execute(sql.SQL(accion + " ROLE {} LOGIN PASSWORD {}").format(rol, sql.Literal(clave)))
        dwh.execute(sql.SQL("ALTER ROLE {} SET default_transaction_read_only = on").format(rol))
        dwh.execute(
            sql.SQL("ALTER ROLE {} SET statement_timeout = {}").format(
                rol, sql.Literal(f"{TIEMPO_MAXIMO_MS}ms")
            )
        )
        dwh.execute(sql.SQL("ALTER ROLE {} SET search_path = semantic, public").format(rol))

        dwh.execute(sql.SQL("GRANT CONNECT ON DATABASE {} TO {}").format(sql.Identifier(base), rol))
        for esquema in ("raw", "staging", "intermediate", "calidad", "marts"):
            dwh.execute(
                sql.SQL("REVOKE ALL ON SCHEMA {} FROM {}").format(sql.Identifier(esquema), rol)
            )
        dwh.execute(sql.SQL("GRANT USAGE ON SCHEMA semantic TO {}").format(rol))
        dwh.execute(sql.SQL("GRANT SELECT ON ALL TABLES IN SCHEMA semantic TO {}").format(rol))
        dwh.execute(
            sql.SQL(
                "ALTER DEFAULT PRIVILEGES FOR ROLE {} IN SCHEMA semantic GRANT SELECT ON TABLES TO {}"
            ).format(sql.Identifier(dueno), rol)
        )
    print(f"Rol {ROL} listo: solo lectura sobre el esquema semantic.")


if __name__ == "__main__":
    try:
        preparar()
    except RuntimeError as error:
        print(error, file=sys.stderr)
        sys.exit(1)
