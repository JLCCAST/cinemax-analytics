-- Una fila por función, también las que no vendieron nada. La ocupación se mide contra
-- las butacas activas de la sala, no contra availableSeats.
with confiteria as (
    select v.id_funcion, sum(l.importe_neto) as ingreso
    from {{ ref('int_lineas_confiteria') }} as l
    join {{ ref('int_ventas') }} as v on v.id_venta = l.id_venta and v.pagada
    where v.id_funcion is not null
    group by v.id_funcion
)

select
    f.id_funcion,
    to_char(f.fecha_funcion, 'YYYYMMDD')::int as fecha_funcion_key,
    extract(hour from f.hora_inicio)::int as hora_funcion,
    coalesce(p.pelicula_key, '-1') as pelicula_key,
    coalesce(s.sala_key, -1) as sala_key,
    coalesce(s.sede_key, -1) as sede_key,
    f.estado,
    f.idioma,
    f.precio_base,
    f.semana_desde_estreno,
    f.capacidad,
    f.vendidas,
    f.vendidas::numeric / nullif(f.capacidad, 0) as ocupacion,
    f.ingreso_neto as ingreso_entradas,
    coalesce(c.ingreso, 0) as ingreso_confiteria,
    f.desfase_disponibles
from {{ ref('int_funciones') }} as f
left join {{ ref('dim_pelicula') }} as p on p.pelicula_key = f.id_pelicula
left join {{ ref('dim_sala') }} as s on s.sala_key = f.id_sala
left join confiteria as c on c.id_funcion = f.id_funcion
