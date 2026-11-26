"""uv run python -m cinemax_analytics.agente.evaluar [--ids 1,5,23] [--pausa 4]

Corre el agente sobre preguntas.yaml y compara su resultado con el de la referencia.
Guarda el detalle en agente_resultados/<fecha>.json (fuera de git).
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from statistics import mean, median

import psycopg
import yaml

from cinemax_analytics.agente.comparar import coinciden
from cinemax_analytics.agente.grafo import construir_agente, preguntar
from cinemax_analytics.agente.herramientas import correr
from cinemax_analytics.agente.seguridad import ConsultaRechazada
from cinemax_analytics.fuentes import RAIZ


def cargar_preguntas() -> list[dict]:
    ruta = Path(__file__).with_name("preguntas.yaml")
    return yaml.safe_load(ruta.read_text(encoding="utf-8"))


def calificar(pregunta: dict, respuesta) -> str:
    """ok, fallo, abstencion_correcta o abstencion_incorrecta."""
    if not pregunta.get("respondible", True):
        return "abstencion_correcta" if respuesta.se_abstuvo else "fallo"
    if respuesta.se_abstuvo:
        return "abstencion_incorrecta"
    if not respuesta.sql_final:
        return "fallo"
    try:
        _, esperado, _ = correr(pregunta["sql"], limite=None)
        _, obtenido, _ = correr(respuesta.sql_final, limite=None)
    except (ConsultaRechazada, psycopg.Error):
        return "fallo"
    return "ok" if coinciden(esperado, obtenido) else "fallo"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m cinemax_analytics.agente.evaluar")
    parser.add_argument("--ids", help="Solo estas preguntas, separadas por coma")
    parser.add_argument(
        "--pausa",
        type=float,
        default=4.0,
        help="Segundos entre preguntas, por el límite de la API gratuita",
    )
    args = parser.parse_args(argv)

    if not os.getenv("GEMINI_API_KEY"):
        print("Falta GEMINI_API_KEY en .env", file=sys.stderr)
        return 1

    preguntas = cargar_preguntas()
    if args.ids:
        elegidas = {int(i) for i in args.ids.split(",")}
        preguntas = [p for p in preguntas if p["id"] in elegidas]

    agente = construir_agente()
    detalle = []
    for n, pregunta in enumerate(preguntas):
        if n:
            time.sleep(args.pausa)
        respuesta = preguntar(agente, pregunta["pregunta"])
        nota = calificar(pregunta, respuesta)
        detalle.append(
            {
                "id": pregunta["id"],
                "dificultad": pregunta["dificultad"],
                "pregunta": pregunta["pregunta"],
                "resultado": nota,
                "respuesta": respuesta.texto,
                "sql": respuesta.sql_final,
                "segundos": round(respuesta.segundos, 2),
                "tokens": respuesta.tokens,
                "herramientas": respuesta.llamadas,
            }
        )
        print(
            f"{pregunta['id']:>3} {pregunta['dificultad']:<9} {nota:<22} "
            f"{respuesta.segundos:6.1f} s {respuesta.tokens:>7} tokens"
        )

    respondibles = [d for d in detalle if d["dificultad"] != "sin_datos"]
    sin_datos = [d for d in detalle if d["dificultad"] == "sin_datos"]
    resumen = {
        "modelo": os.getenv("AGENTE_MODELO", "gemini-2.5-flash"),
        "exactitud": sum(d["resultado"] == "ok" for d in respondibles) / max(1, len(respondibles)),
        "abstencion_correcta": sum(d["resultado"] == "abstencion_correcta" for d in sin_datos)
        / max(1, len(sin_datos)),
        "abstenciones_de_mas": sum(d["resultado"] == "abstencion_incorrecta" for d in respondibles),
        "segundos_mediana": median(d["segundos"] for d in detalle),
        "segundos_promedio": mean(d["segundos"] for d in detalle),
        "tokens_promedio": mean(d["tokens"] for d in detalle),
    }
    for dificultad in ("facil", "media", "dificil"):
        grupo = [d for d in respondibles if d["dificultad"] == dificultad]
        if grupo:
            resumen[f"exactitud_{dificultad}"] = sum(d["resultado"] == "ok" for d in grupo) / len(
                grupo
            )

    print(
        "\n"
        + "\n".join(
            f"{clave}: {valor:.3f}" if isinstance(valor, float) else f"{clave}: {valor}"
            for clave, valor in resumen.items()
        )
    )
    carpeta = RAIZ / "agente_resultados"
    carpeta.mkdir(exist_ok=True)
    salida = carpeta / f"{datetime.now():%Y-%m-%d_%H%M}.json"
    salida.write_text(
        json.dumps(
            {"resumen": resumen, "detalle": detalle}, ensure_ascii=False, indent=2, default=str
        ),
        encoding="utf-8",
    )
    print(f"\nDetalle en {salida.relative_to(RAIZ)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
