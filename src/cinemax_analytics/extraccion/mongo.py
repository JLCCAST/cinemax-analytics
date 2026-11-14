"""Extracción de cartelera (MongoDB): cada documento entra completo como JSONB."""

from bson import json_util

from cinemax_analytics.extraccion.raw import Columnas, copiar_a

# Extended JSON relajado: conserva {"$numberDecimal": ...} y {"$date": ...}, así staging
# ve si un precio se guardó como Decimal128 (seed) o como texto (servicio).
OPCIONES_JSON = json_util.RELAXED_JSON_OPTIONS

COLUMNAS: Columnas = [("_id", "text"), ("doc", "jsonb")]


def colecciones(db) -> list[str]:
    return sorted(c for c in db.list_collection_names() if not c.startswith("system."))


def documento_json(documento: dict) -> str:
    return json_util.dumps(documento, json_options=OPCIONES_JSON)


def copiar_coleccion(db, dwh, coleccion: str, destino: str) -> int:
    filas = db[coleccion].count_documents({})
    with copiar_a(dwh, destino, [nombre for nombre, _ in COLUMNAS]) as salida:
        for documento in db[coleccion].find().sort("_id", 1):
            salida.write_row((str(documento["_id"]), documento_json(documento)))
    return filas
