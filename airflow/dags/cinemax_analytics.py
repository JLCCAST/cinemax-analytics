"""Pipeline diario: extraer las 5 bases de CineMax, construir el warehouse con dbt y revisar
la calidad. Con Cosmos, cada modelo de dbt es una tarea y sus pruebas corren justo después."""

import pendulum
from airflow.providers.standard.operators.bash import BashOperator
from airflow.sdk import DAG
from cosmos import DbtTaskGroup, ExecutionConfig, ProfileConfig, ProjectConfig, RenderConfig
from cosmos.constants import InvocationMode, LoadMode, TestBehavior

PROYECTO = "/opt/cinemax-analytics"
ENTORNO = "/opt/airflow/proyecto/bin"
DBT = f"{ENTORNO}/dbt"
# El código se monta, no se instala: así un cambio no obliga a reconstruir la imagen.
VARIABLES = {"PYTHONPATH": f"{PROYECTO}/src", "PYTHONUTF8": "1"}

with DAG(
    dag_id="cinemax_analytics",
    description="Extracción, dbt y calidad del warehouse de CineMax",
    schedule="0 3 * * *",
    start_date=pendulum.datetime(2026, 11, 1, tz="America/Lima"),
    catchup=False,
    max_active_runs=1,
    tags=["cinemax", "dbt"],
):
    extraer = BashOperator(
        task_id="extraer_fuentes",
        bash_command=f"{ENTORNO}/python -m cinemax_analytics.extraccion",
        env=VARIABLES,
        append_env=True,
    )

    transformar = DbtTaskGroup(
        group_id="dbt",
        project_config=ProjectConfig(dbt_project_path=f"{PROYECTO}/dbt", install_dbt_deps=False),
        profile_config=ProfileConfig(
            profile_name="cinemax_analytics",
            target_name="local",
            profiles_yml_filepath=f"{PROYECTO}/dbt/profiles.yml",
        ),
        # dbt corre en su propio entorno (ver airflow/Dockerfile), no dentro de Airflow.
        execution_config=ExecutionConfig(
            dbt_executable_path=DBT, invocation_mode=InvocationMode.SUBPROCESS
        ),
        render_config=RenderConfig(
            load_method=LoadMode.DBT_LS,
            test_behavior=TestBehavior.AFTER_EACH,
            dbt_executable_path=DBT,
            invocation_mode=InvocationMode.SUBPROCESS,
        ),
    )

    reporte = BashOperator(
        task_id="reporte_de_calidad",
        bash_command=f"{ENTORNO}/python {PROYECTO}/scripts/reporte_calidad.py",
        env=VARIABLES,
        append_env=True,
    )

    extraer >> transformar >> reporte
