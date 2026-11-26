import pytest

from cinemax_analytics.agente.seguridad import ConsultaRechazada, validar

VISTAS = {"vw_ventas", "vw_entradas"}


@pytest.mark.parametrize(
    "consulta",
    [
        "SELECT count(*) FROM semantic.vw_ventas",
        "select sede, sum(total) from vw_ventas group by sede;",
        "WITH x AS (SELECT * FROM semantic.vw_entradas) SELECT count(*) FROM x",
        "SELECT a.sede FROM semantic.vw_ventas a JOIN semantic.vw_entradas b USING (id_venta)",
        "SELECT 1 FROM semantic.vw_ventas UNION SELECT 2 FROM semantic.vw_entradas",
    ],
)
def test_lecturas_permitidas(consulta):
    assert validar(consulta, VISTAS)


@pytest.mark.parametrize(
    "consulta",
    [
        "DELETE FROM semantic.vw_ventas",
        "UPDATE semantic.vw_ventas SET total = 0",
        "DROP VIEW semantic.vw_ventas",
        "SELECT 1; DROP TABLE x",
        "SELECT * INTO copia FROM semantic.vw_ventas",
        "SELECT * FROM marts.fact_venta",
        "SELECT * FROM raw.usuarios__user_account",
        "SELECT * FROM pg_catalog.pg_user",
        "SELECT * FROM fact_venta",
        "SELECT pg_sleep(30) FROM semantic.vw_ventas",
        "COPY semantic.vw_ventas TO '/tmp/x'",
        "",
        "esto no es sql",
    ],
)
def test_todo_lo_demas_se_rechaza(consulta):
    with pytest.raises(ConsultaRechazada):
        validar(consulta, VISTAS)
