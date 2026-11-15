-- Una fila por función, incluidas las que no vendieron nada. Las vendidas se
-- recalculan desde las entradas; los contadores de MongoDB quedan para comparar.
with vendidas as (
    select
        id_funcion,
        count(*) as vendidas,
        sum(precio) as ingreso_bruto,
        sum(importe_neto) as ingreso_neto
    from {{ ref('stg_facturacion__entradas') }}
    group by id_funcion
)

select
    f.id_funcion,
    f.id_pelicula,
    f.id_sala,
    f.id_sede,
    f.fecha_funcion,
    f.hora_inicio,
    f.hora_fin,
    f.fecha_funcion + f.hora_inicio as inicio,
    f.idioma,
    f.precio_base,
    f.tipo_precio_origen,
    f.estado,
    (f.fecha_funcion - p.fecha_estreno) / 7 as semana_desde_estreno,
    s.capacidad,
    coalesce(v.vendidas, 0) as vendidas,
    coalesce(v.ingreso_bruto, 0) as ingreso_bruto,
    coalesce(v.ingreso_neto, 0) as ingreso_neto,
    f.butacas_disponibles as disponibles_origen,
    coalesce(f.butacas_vendidas, 0) as vendidas_origen,
    f.butacas_disponibles - (s.capacidad - coalesce(v.vendidas, 0)) as desfase_disponibles,
    coalesce(f.butacas_vendidas, 0) - coalesce(v.vendidas, 0) as desfase_vendidas,
    f.id_sede is distinct from s.id_sede as sede_distinta_a_la_sala
from {{ ref('stg_cartelera__funciones') }} as f
left join {{ ref('stg_cartelera__peliculas') }} as p on p.id_pelicula = f.id_pelicula
left join {{ ref('int_salas') }} as s on s.id_sala = f.id_sala
left join vendidas as v on v.id_funcion = f.id_funcion
