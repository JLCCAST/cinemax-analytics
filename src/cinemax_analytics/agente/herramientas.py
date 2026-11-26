"""Las cuatro herramientas del agente. Todas usan el rol de solo lectura."""

from decimal import Decimal

import psycopg
from langchain_core.tools import tool
from psycopg import sql

from cinemax_analytics.agente.conexion import conectar_agente
from cinemax_analytics.agente.seguridad import ESQUEMA, ConsultaRechazada, validar

LIMITE_FILAS = 100
MUESTRA = 2000
VALORES_CATEGORICOS = 12


def vistas_disponibles() -> dict[str, str]:
    """Nombre de cada vista de semantic y su descripción."""
    with conectar_agente() as conexion:
        filas = conexion.execute(
            """
            SELECT c.relname, coalesce(obj_description(c.oid, 'pg_class'), '')
            FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE n.nspname = %s AND c.relkind IN ('v', 'm', 'r')
            ORDER BY c.relname
            """,
            (ESQUEMA,),
        ).fetchall()
    return dict(filas)


def _texto(valor) -> str:
    if valor is None:
        return "nulo"
    if isinstance(valor, Decimal):
        return f"{valor:.4f}".rstrip("0").rstrip(".")
    if isinstance(valor, float):
        return f"{valor:.4f}".rstrip("0").rstrip(".")
    return str(valor)


def formatear(columnas: list[str], filas: list[tuple], recortado: bool = False) -> str:
    lineas = [" | ".join(columnas)]
    lineas += [" | ".join(_texto(v) for v in fila) for fila in filas]
    if not filas:
        lineas.append("(sin filas)")
    if recortado:
        lineas.append(f"(se muestran las primeras {LIMITE_FILAS} filas)")
    return "\n".join(lineas)


def _columnas(conexion, vista: str) -> list[tuple[str, str, str]]:
    return conexion.execute(
        """
        SELECT a.attname, format_type(a.atttypid, a.atttypmod),
               coalesce(col_description(a.attrelid, a.attnum), '')
        FROM pg_attribute a
        WHERE a.attrelid = to_regclass(%s) AND a.attnum > 0 AND NOT a.attisdropped
        ORDER BY a.attnum
        """,
        (f"{ESQUEMA}.{vista}",),
    ).fetchall()


@tool
def listar_vistas() -> str:
    """Lista las vistas del warehouse que puedes consultar, con lo que contiene cada una."""
    return "\n".join(f"{ESQUEMA}.{nombre}: {desc}" for nombre, desc in vistas_disponibles().items())


@tool
def describir_vista(vista: str) -> str:
    """Muestra las columnas de una vista (tipo y descripción), ejemplos de valores y, para las
    columnas con pocas categorías, todos sus valores posibles. vista: por ejemplo 'vw_ventas'."""
    vista = vista.removeprefix(f"{ESQUEMA}.")
    if vista not in vistas_disponibles():
        return f"No existe la vista {vista}. Usa listar_vistas."
    with conectar_agente() as conexion:
        columnas = _columnas(conexion, vista)
        # Muestra al azar: las primeras filas caen todas en los mismos meses.
        muestra = conexion.execute(
            sql.SQL("SELECT * FROM {} ORDER BY random() LIMIT {}").format(
                sql.Identifier(ESQUEMA, vista), sql.Literal(MUESTRA)
            )
        ).fetchall()

    lineas = [f"{ESQUEMA}.{vista}:"]
    for i, (nombre, tipo, descripcion) in enumerate(columnas):
        valores = [fila[i] for fila in muestra if fila[i] is not None]
        distintos = list(dict.fromkeys(_texto(v) for v in valores))
        if 0 < len(distintos) <= VALORES_CATEGORICOS and tipo in ("text", "boolean"):
            ejemplos = "valores: " + ", ".join(sorted(distintos))
        else:
            ejemplos = "ej.: " + ", ".join(distintos[:3])
        lineas.append(f"- {nombre} ({tipo}): {descripcion} [{ejemplos}]")
    return "\n".join(lineas)


@tool
def buscar_valor(vista: str, columna: str, texto: str) -> str:
    """Busca cómo está escrito un valor de texto (película, sede, producto, promoción...) cuando
    el usuario lo escribe distinto. Devuelve los 5 valores más parecidos de esa columna."""
    vista = vista.removeprefix(f"{ESQUEMA}.")
    if vista not in vistas_disponibles():
        return f"No existe la vista {vista}. Usa listar_vistas."
    with conectar_agente() as conexion:
        if columna not in {c[0] for c in _columnas(conexion, vista)}:
            return f"La vista {vista} no tiene la columna {columna}. Usa describir_vista."
        consulta = sql.SQL(
            """
            WITH valores AS (SELECT DISTINCT {col}::text AS valor FROM {vista} WHERE {col} IS NOT NULL)
            SELECT valor, similarity(unaccent(lower(valor)), unaccent(lower(%(t)s))) AS parecido
            FROM valores
            WHERE unaccent(lower(valor)) %% unaccent(lower(%(t)s))
               OR unaccent(lower(valor)) LIKE '%%' || unaccent(lower(%(t)s)) || '%%'
            ORDER BY parecido DESC, valor
            LIMIT 5
            """
        ).format(col=sql.Identifier(columna), vista=sql.Identifier(ESQUEMA, vista))
        filas = conexion.execute(consulta, {"t": texto}).fetchall()
    if not filas:
        return f"No hay valores parecidos a '{texto}' en {vista}.{columna}."
    return "\n".join(f"{valor} (parecido {parecido:.2f})" for valor, parecido in filas)


def correr(consulta: str, limite: int | None = LIMITE_FILAS) -> tuple[list[str], list[tuple], bool]:
    """Valida y ejecuta. Devuelve columnas, filas y si se recortó. Lanza ConsultaRechazada o
    psycopg.Error."""
    texto = validar(consulta, set(vistas_disponibles()))
    with conectar_agente() as conexion:
        cursor = conexion.execute(texto)
        columnas = [d.name for d in cursor.description or []]
        if limite is None:
            return columnas, cursor.fetchall(), False
        filas = cursor.fetchmany(limite + 1)
    return columnas, filas[:limite], len(filas) > limite


@tool
def ejecutar_sql(consulta: str) -> str:
    """Ejecuta una consulta SELECT de PostgreSQL sobre las vistas de semantic y devuelve el
    resultado como tabla (máximo 100 filas). Si falla, devuelve el error para que lo corrijas."""
    try:
        columnas, filas, recortado = correr(consulta)
    except ConsultaRechazada as error:
        return f"Consulta rechazada: {error}"
    except psycopg.Error as error:
        return f"Error de PostgreSQL: {str(error).strip()}"
    return formatear(columnas, filas, recortado)


HERRAMIENTAS = [listar_vistas, describir_vista, buscar_valor, ejecutar_sql]
