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
uv run pytest
```

## Avance

- [x] Entorno, extracción y staging en dbt
- [x] Generador de ventas sintéticas
- [x] Calidad de datos y conciliación
- [ ] Modelo estrella y dashboard en Power BI
- [ ] Agente de text-to-SQL con LangGraph y su evaluación
- [ ] Orquestación con Airflow
