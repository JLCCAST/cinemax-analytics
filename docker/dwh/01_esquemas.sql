-- raw: copia de las fuentes, la escribe la extracción.
-- staging y marts: los escribe dbt.
-- semantic: vistas para el agente (fase 4).
CREATE SCHEMA IF NOT EXISTS raw;
CREATE SCHEMA IF NOT EXISTS staging;
CREATE SCHEMA IF NOT EXISTS marts;
CREATE SCHEMA IF NOT EXISTS semantic;
