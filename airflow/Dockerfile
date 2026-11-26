FROM apache/airflow:3.3.2-python3.12

# Cosmos va en el entorno de Airflow, con sus restricciones de versiones.
RUN pip install --no-cache-dir "astronomer-cosmos==1.16.0" \
    --constraint "https://raw.githubusercontent.com/apache/airflow/constraints-3.3.2/constraints-3.12.txt"

# El proyecto (extracción y dbt) corre en un entorno aparte, con las versiones de uv.lock,
# para que dbt y Airflow no choquen. El código no se copia: se monta en /opt/cinemax-analytics.
COPY --from=ghcr.io/astral-sh/uv:0.13.8 /uv /usr/local/bin/uv
COPY --chown=airflow:root pyproject.toml uv.lock /tmp/proyecto/
RUN cd /tmp/proyecto \
    && uv export --frozen --no-dev --no-hashes --no-emit-project -o /tmp/requisitos.txt \
    && uv venv /opt/airflow/proyecto \
    && uv pip install --python /opt/airflow/proyecto/bin/python -r /tmp/requisitos.txt \
    && rm -rf /tmp/proyecto /tmp/requisitos.txt
