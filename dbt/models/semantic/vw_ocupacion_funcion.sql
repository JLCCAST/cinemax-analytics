select
    o.id_funcion,
    f.fecha as fecha_funcion,
    f.anio_mes as mes_funcion,
    f.nombre_dia as dia_funcion,
    f.es_fin_de_semana,
    f.es_feriado,
    f.temporada,
    o.hora_funcion,
    h.franja,
    s.sede,
    sa.sala,
    sa.es_vip,
    p.titulo as pelicula,
    p.genero_principal,
    o.idioma,
    o.estado,
    o.precio_base,
    o.semana_desde_estreno,
    o.capacidad,
    o.vendidas,
    o.ocupacion,
    o.ingreso_entradas,
    o.ingreso_confiteria
from {{ ref('fact_ocupacion_funcion') }} as o
join {{ ref('dim_fecha') }} as f on f.fecha_key = o.fecha_funcion_key
join {{ ref('dim_franja_horaria') }} as h on h.hora = o.hora_funcion
join {{ ref('dim_sede') }} as s on s.sede_key = o.sede_key
join {{ ref('dim_sala') }} as sa on sa.sala_key = o.sala_key
join {{ ref('dim_pelicula') }} as p on p.pelicula_key = o.pelicula_key
