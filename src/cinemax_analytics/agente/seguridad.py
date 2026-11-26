"""Qué SQL puede correr el agente: una sola consulta de lectura sobre las vistas de semantic.

El rol de la base ya es de solo lectura; esto rechaza antes lo que no corresponde y le
devuelve al modelo un mensaje que le sirva para corregirse.
"""

import sqlglot
from sqlglot import exp

ESQUEMA = "semantic"

PROHIBIDOS = (
    exp.Insert,
    exp.Update,
    exp.Delete,
    exp.Merge,
    exp.Create,
    exp.Drop,
    exp.Alter,
    exp.Command,
    exp.Into,
    exp.TruncateTable,
)

FUNCIONES_PROHIBIDAS = {
    "pg_sleep",
    "pg_read_file",
    "pg_read_binary_file",
    "pg_ls_dir",
    "pg_stat_file",
    "lo_import",
    "lo_export",
    "dblink",
    "set_config",
    "pg_terminate_backend",
    "pg_cancel_backend",
    "query_to_xml",
}


class ConsultaRechazada(ValueError):
    pass


def validar(consulta: str, vistas: set[str]) -> str:
    """Devuelve la consulta lista para ejecutar, o lanza ConsultaRechazada."""
    texto = consulta.strip().rstrip(";").strip()
    if not texto:
        raise ConsultaRechazada("La consulta está vacía.")
    try:
        arboles = [a for a in sqlglot.parse(texto, read="postgres") if a is not None]
    except sqlglot.errors.ParseError as error:
        raise ConsultaRechazada(f"No se pudo leer el SQL: {error}") from error

    if len(arboles) != 1:
        raise ConsultaRechazada("Envía una sola consulta por vez.")
    arbol = arboles[0]
    if not isinstance(arbol, exp.Query):
        raise ConsultaRechazada("Solo se permiten consultas SELECT (o WITH ... SELECT).")
    if arbol.find(*PROHIBIDOS):
        raise ConsultaRechazada("Solo se permite leer: nada de INSERT, UPDATE, DDL ni SELECT INTO.")

    ctes = {cte.alias_or_name for cte in arbol.find_all(exp.CTE)}
    for tabla in arbol.find_all(exp.Table):
        nombre, esquema = tabla.name, tabla.db
        if not esquema and nombre in ctes:
            continue
        if (esquema and esquema != ESQUEMA) or nombre not in vistas:
            raise ConsultaRechazada(
                f"Solo puedes consultar estas vistas de {ESQUEMA}: {', '.join(sorted(vistas))}."
            )

    for funcion in arbol.find_all(exp.Func):
        nombre = funcion.name if isinstance(funcion, exp.Anonymous) else funcion.sql_name()
        if nombre.lower() in FUNCIONES_PROHIBIDAS:
            raise ConsultaRechazada(f"La función {nombre} no está permitida.")
    return texto
