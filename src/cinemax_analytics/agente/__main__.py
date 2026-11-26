"""uv run python -m cinemax_analytics.agente "¿qué sede vendió más en julio?"

Sin pregunta, abre una conversación: cada línea es una pregunta nueva; vacío para salir.
"""

import os
import sys

from cinemax_analytics.agente.grafo import construir_agente, preguntar


def main(argv: list[str]) -> int:
    if not os.getenv("GEMINI_API_KEY"):
        print("Falta GEMINI_API_KEY en .env", file=sys.stderr)
        return 1
    agente = construir_agente()
    mostrar_sql = "--sql" in argv
    preguntas = [a for a in argv if a != "--sql"]

    def responder(pregunta: str) -> None:
        respuesta = preguntar(agente, pregunta)
        print(respuesta.texto)
        if mostrar_sql and respuesta.sql_final:
            print(f"\n{respuesta.sql_final}")
        print(f"({respuesta.segundos:.1f} s, {respuesta.tokens} tokens)\n")

    if preguntas:
        responder(" ".join(preguntas))
        return 0
    while pregunta := input("> ").strip():
        responder(pregunta)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
