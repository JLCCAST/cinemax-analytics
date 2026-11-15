-- ¿Cuánto caen las películas semana a semana? Normalizado por función, porque el total
-- mezcla menos demanda con menos funciones programadas.
select
    semana_desde_estreno,
    count(*) as funciones,
    round(avg(vendidas), 2) as entradas_por_funcion,
    round(avg(ocupacion) * 100, 1) as ocupacion_pct
from {{ ref('fact_ocupacion_funcion') }}
where estado = 'Programada' and semana_desde_estreno between 0 and 7
group by semana_desde_estreno
order by semana_desde_estreno
