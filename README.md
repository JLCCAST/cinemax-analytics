# CineMax Analytics

Warehouse, dashboard y agente de consultas sobre los datos de [CineMax](https://github.com/JLCCAST/CineMax), un sistema de venta de entradas de cine hecho con microservicios en Spring Boot. CineMax fue un proyecto de grupo en la universidad; este repo usa mi fork.

CineMax reparte sus datos en cinco bases de tres motores: usuarios y facturación en PostgreSQL, sucursales y confitería en MySQL, y cartelera en MongoDB. Este proyecto las integra en un warehouse para analizar ventas, ocupación de salas y promociones.

Las ventas son sintéticas. El generador escribe directo en las bases de CineMax con sus mismas reglas de tarifas, promociones y butacas, y el dashboard tiene que recuperar los patrones que se configuran en el generador. Es una prueba del pipeline completo, no un estudio de mercado.

## Cómo está armado

```
5 bases de CineMax (Docker) -> extracción (Python) -> raw -> dbt: staging -> marts -> Power BI
                                                                             -> agente text-to-SQL
```

- `docker-compose.yml`: las 5 bases, creadas con las migraciones de Flyway de CineMax (submódulo `cinemax/`), y el warehouse en PostgreSQL 16.
- `src/cinemax_analytics/extraccion`: copia las fuentes al esquema `raw`. MongoDB entra como JSONB y de los usuarios no se copian datos personales.
- `dbt/`: staging de cada fuente, `dim_fecha` con los feriados de Perú y pruebas de calidad (claves, relaciones entre bases distintas y que cada venta cuadre con sus líneas).
- `src/cinemax_analytics/generador`: un año de ventas sintéticas (unas 150 000) con 3 sedes nuevas, 52 películas inventadas y 20 000 clientes. Usa las tarifas y el motor de promociones de CineMax pasados a Python, comprobados contra compras reales del sistema. Con la misma semilla da exactamente los mismos datos. Los parámetros de demanda están en `generador/parametros.py`.

## Calidad de datos

`dbt/models/calidad` revisa 14 problemas posibles: copias incompletas, texto mal codificado, contadores de butacas que no cuadran, ids huérfanos entre bases, ventas que no cuadran con sus líneas o pagadas después de la función, y precios fuera de tarifa. Para probarlo, `python -m cinemax_analytics.generador.defectos` mete esos defectos con tasas conocidas, y `scripts/reporte_calidad.py` compara lo inyectado con lo detectado. Hoy cada chequeo encuentra exactamente lo inyectado.

## Dashboard

Modelo estrella en `dbt/models/marts`: cuatro hechos (`fact_ticket`, `fact_venta`, `fact_confiteria` y `fact_ocupacion_funcion`) y sus dimensiones. Power BI lo importa desde el warehouse; las medidas están en `powerbi/medidas.dax`, y `dbt/analyses` tiene las consultas SQL que sirven para comprobar las cifras del dashboard. Datos de noviembre de 2025 a octubre de 2026.

**Resumen.** S/ 6,21 millones en 148 562 compras, con un gasto promedio de S/ 41,83 y una ocupación media de 20,4 %. El 58 % paga con Yape. Santiago de Surco es la sede que más vende (S/ 1,8 mill.); Wanchaq vende menos porque abrió en mayo. Los altibajos de cada mes siguen a la cartelera, más que a la temporada.

![Resumen](powerbi/capturas/1-resumen.png)

**Ocupación.** Las noches se llenan casi el doble que las matinés (29 % frente a 16 %), y el sábado en la noche es el pico (39 %). El verano es la temporada con más público por función (14,7 entradas). Fin de año queda por debajo de una semana normal aunque el generador le da más demanda: en diciembre la cartelera fue más débil, y ese efecto se come al de la temporada.

![Ocupación](powerbi/capturas/2-ocupacion.png)

**Películas y estrenos.** Una película pierde cerca de 40 % de su público por función cada semana desde el estreno (22,0, 13,6, 8,1 y 5,4 entradas por función en las semanas 0 a 3). Es la retención de 0,60 que tiene el generador. Comedia es el género que más ingresa (S/ 1,01 mill.), repartiendo cada película entre sus géneros.

![Películas](powerbi/capturas/3-peliculas.png)

**Confitería y promociones.** El 47 % de las compras con entradas lleva confitería, y los combos son el 57 % de ese ingreso. El combo depende del tamaño del grupo: lo lleva el 5 % de las compras de una entrada, el 22 % de las de dos y cerca del 40 % de las de tres o más. El 56 % de las compras usa alguna promoción. La Matiné se aplica en 3 de cada 10 y es la que más descuenta (S/ 278 mil de S/ 760 mil). Martes y miércoles cobran S/ 10 a 12 por entrada, frente a S/ 16 el fin de semana, y venden más que lunes y jueves.

![Confitería y promociones](powerbi/capturas/4-confiteria-y-promociones.png)

## Agente de consultas

Responde en español preguntas sobre el warehouse escribiendo y ejecutando SQL. Es un ciclo ReAct en LangGraph con Gemini (`gemini-3.1-flash-lite`): el modelo decide qué herramienta usar, mira el resultado y repite hasta responder.

```bash
uv run python -m cinemax_analytics.agente "¿qué película vendió más entradas en julio?"
```

- Solo ve el esquema `semantic` (`dbt/models/semantic`): seis vistas ya unidas, con nombres en español y una descripción por columna que el agente lee.
- Tiene cuatro herramientas: listar vistas, describir una vista con ejemplos de valores, buscar cómo está escrito un nombre (con `pg_trgm` y `unaccent`) y ejecutar SQL.
- Seguridad en dos capas. La base: un rol de solo lectura, sin acceso a otros esquemas y con 5 s como máximo por consulta. Antes de ejecutar: un validador con `sqlglot` que acepta una sola consulta SELECT sobre esas vistas.
- Un glosario (`agente/glosario.yaml`) fija sinónimos, cómo se calculan las métricas y qué datos no existen, para que el agente diga que no sabe en vez de inventar.

### Evaluación

25 preguntas (`agente/preguntas.yaml`): 10 fáciles, 8 medias, 4 difíciles y 3 que no se pueden responder con estos datos (stock, correos de clientes, ganancias). Se compara el resultado de la consulta del agente con el de una consulta de referencia, no el texto del SQL.

| Grupo | Resultado |
|---|---|
| Fáciles | 10 de 10 |
| Medias | 8 de 8 |
| Difíciles | 3 de 4 |
| Sin datos (debe decir que no hay datos) | 3 de 3 |
| Dijo "no hay datos" cuando sí había | 0 |

Tiempo por pregunta: mediana de 23 s, con unos 6 300 tokens. El tiempo lo pone casi todo la cola del plan gratuito de Gemini; las consultas tardan menos de 1 s.

El fallo: para "entradas por función en la semana de estreno" contó solo las funciones que vendieron algo, y le dio 22,4 en vez de 22,0. Es la diferencia entre promediar sobre las funciones con ventas y sobre todas las programadas.

En la corrida del 25 de noviembre de 2026, seis preguntas recibieron un error 503 de Gemini (modelo saturado) y se repitieron; el evaluador ahora reintenta solo ese tipo de error.

## Cómo correrlo

Hace falta Docker y [uv](https://docs.astral.sh/uv/).

```bash
git clone --recurse-submodules https://github.com/JLCCAST/cinemax-analytics.git
cd cinemax-analytics
cp .env.example .env    # cambia las contraseñas
docker compose up -d
uv run python scripts/smoke_fuentes.py
uv run python -m cinemax_analytics.generador --semilla 42 --desde 2025-11-01 --hasta 2026-10-31
uv run python scripts/smoke_fuentes.py --generado
uv run python -m cinemax_analytics.extraccion
uv run --env-file .env dbt build
uv run python scripts/reporte_calidad.py
uv run python -m cinemax_analytics.agente.preparar      # rol de solo lectura del agente
uv run pytest
```

Para el agente hace falta una clave de Gemini en `.env` (`GEMINI_API_KEY`). La evaluación se corre con `uv run python -m cinemax_analytics.agente.evaluar`.

## Avance

- [x] Entorno, extracción y staging en dbt
- [x] Generador de ventas sintéticas
- [x] Calidad de datos y conciliación
- [x] Modelo estrella y dashboard en Power BI
- [x] Agente de text-to-SQL con LangGraph y su evaluación
- [ ] Orquestación con Airflow
