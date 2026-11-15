-- Entradas por función según el día: martes (2x1) y miércoles (50 %) frente al resto
-- de días de semana. Solo encuentra el efecto que se programó en el generador.
select
    f.nombre_dia,
    f.dia_semana,
    count(*) as funciones,
    round(avg(o.vendidas), 2) as entradas_por_funcion,
    round(sum(o.ingreso_entradas) / nullif(sum(o.vendidas), 0), 2) as ingreso_por_entrada
from {{ ref('fact_ocupacion_funcion') }} as o
join {{ ref('dim_fecha') }} as f on f.fecha_key = o.fecha_funcion_key
where o.estado = 'Programada'
group by f.nombre_dia, f.dia_semana
order by f.dia_semana
