"""El agente: un ciclo ReAct en LangGraph (el modelo piensa, llama una herramienta, mira el
resultado y repite) hasta que responde."""

import os
import time
from dataclasses import dataclass, field
from pathlib import Path

import yaml
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

from cinemax_analytics.agente.herramientas import HERRAMIENTAS, vistas_disponibles

MODELO_POR_DEFECTO = "gemini-3.1-flash-lite"
PASOS_MAXIMOS = 25
FRASE_SIN_DATOS = "No hay datos en el warehouse para responder eso"

# Ejemplos para el prompt. No se repiten en la evaluación (preguntas.yaml).
EJEMPLOS = """\
Pregunta: ¿Cuántas entradas de niño se vendieron en total?
SQL: SELECT count(*) FROM semantic.vw_entradas WHERE tarifa = 'Niño'
Pregunta: ¿Cuál es la ocupación de cada sede?
SQL: SELECT sede, round(100.0 * sum(vendidas) / sum(capacidad), 1) AS ocupacion_pct
     FROM semantic.vw_ocupacion_funcion WHERE estado = 'Programada' GROUP BY sede ORDER BY 2 DESC
Pregunta: ¿Cuánto stock de nachos queda?
Respuesta: No hay datos en el warehouse para responder eso: no se guarda el stock.
"""


def _glosario() -> str:
    ruta = Path(__file__).with_name("glosario.yaml")
    return yaml.safe_dump(
        yaml.safe_load(ruta.read_text(encoding="utf-8")), allow_unicode=True, sort_keys=False
    )


def prompt_del_sistema(vistas: dict[str, str] | None = None) -> str:
    lista = "\n".join(f"- semantic.{nombre}: {desc}" for nombre, desc in (vistas or {}).items())
    return f"""Eres analista de datos de CineMax, una cadena de cines en Perú. Respondes en español
preguntas de negocio consultando un warehouse PostgreSQL. Los datos son sintéticos.

Vistas disponibles (no existen otras):
{lista or "Usa listar_vistas para verlas."}

Cómo trabajar:
1. Antes de escribir SQL sobre una vista, mira sus columnas con describir_vista.
2. Si el usuario nombra una película, sede, producto o promoción, confirma cómo está escrito con buscar_valor.
3. Escribe una consulta SELECT y córrela con ejecutar_sql. Si falla, corrígela. Si corres varias
   consultas, la última que ejecutes debe ser la que respalda tu respuesta.
4. Responde en una o dos frases con la cifra. Dinero en soles (S/), porcentajes con un decimal.
   No muestres el SQL salvo que te lo pidan.

Si el warehouse no tiene esos datos, empieza la respuesta con "{FRASE_SIN_DATOS}" y explica por
qué en una frase. Nunca inventes cifras.

Glosario:
{_glosario()}
Ejemplos:
{EJEMPLOS}"""


def construir_agente(modelo: str | None = None):
    llm = ChatGoogleGenerativeAI(
        model=modelo or os.getenv("AGENTE_MODELO", MODELO_POR_DEFECTO),
        api_key=os.getenv("GEMINI_API_KEY"),
        temperature=0,
        max_retries=6,
    )
    llm_con_herramientas = llm.bind_tools(HERRAMIENTAS)
    sistema = SystemMessage(prompt_del_sistema(vistas_disponibles()))

    def pensar(estado: MessagesState):
        return {"messages": [llm_con_herramientas.invoke([sistema, *estado["messages"]])]}

    grafo = StateGraph(MessagesState)
    grafo.add_node("modelo", pensar)
    grafo.add_node("herramientas", ToolNode(HERRAMIENTAS))
    grafo.add_edge(START, "modelo")
    grafo.add_conditional_edges("modelo", tools_condition, {"tools": "herramientas", END: END})
    grafo.add_edge("herramientas", "modelo")
    return grafo.compile()


@dataclass
class Respuesta:
    texto: str
    sql_final: str | None
    segundos: float
    tokens: int
    llamadas: list[str] = field(default_factory=list)

    @property
    def se_abstuvo(self) -> bool:
        return FRASE_SIN_DATOS.lower() in self.texto.lower()


def _texto(mensaje: AIMessage) -> str:
    if isinstance(mensaje.content, str):
        return mensaje.content
    return "".join(p.get("text", "") for p in mensaje.content if isinstance(p, dict))


def preguntar(agente, pregunta: str) -> Respuesta:
    inicio = time.perf_counter()
    estado = agente.invoke(
        {"messages": [HumanMessage(pregunta)]}, config={"recursion_limit": PASOS_MAXIMOS}
    )
    segundos = time.perf_counter() - inicio

    mensajes = estado["messages"]
    consultas = {}
    llamadas = []
    tokens = 0
    sql_final = None
    for mensaje in mensajes:
        if isinstance(mensaje, AIMessage):
            tokens += (mensaje.usage_metadata or {}).get("total_tokens", 0)
            for llamada in mensaje.tool_calls:
                llamadas.append(llamada["name"])
                if llamada["name"] == "ejecutar_sql":
                    consultas[llamada["id"]] = llamada["args"].get("consulta")
        elif (
            isinstance(mensaje, ToolMessage)
            and mensaje.tool_call_id in consultas
            and not str(mensaje.content).startswith(("Consulta rechazada", "Error de PostgreSQL"))
        ):
            sql_final = consultas[mensaje.tool_call_id]

    final = next((m for m in reversed(mensajes) if isinstance(m, AIMessage)), None)
    return Respuesta(
        texto=_texto(final) if final else "",
        sql_final=sql_final,
        segundos=segundos,
        tokens=tokens,
        llamadas=llamadas,
    )
