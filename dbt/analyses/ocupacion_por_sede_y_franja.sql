-- ¿Qué tan llenas van las funciones? Por sede y franja, solo funciones programadas.
select
    s.sede,
    h.franja,
    count(*) as funciones,
    round(avg(o.ocupacion) * 100, 1) as ocupacion_pct
from {{ ref('fact_ocupacion_funcion') }} as o
join {{ ref('dim_sede') }} as s on s.sede_key = o.sede_key
join {{ ref('dim_franja_horaria') }} as h on h.hora = o.hora_funcion
where o.estado = 'Programada'
group by s.sede, h.franja, h.orden_franja
order by s.sede, h.orden_franja
