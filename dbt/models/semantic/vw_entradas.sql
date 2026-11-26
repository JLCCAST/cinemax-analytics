select
    t.id_entrada,
    t.id_venta,
    t.id_funcion,
    ff.fecha as fecha_funcion,
    ff.anio_mes as mes_funcion,
    ff.nombre_dia as dia_funcion,
    t.hora_funcion,
    h.franja,
    fv.fecha as fecha_venta,
    fv.anio_mes as mes_venta,
    s.sede,
    sa.sala,
    sa.es_vip,
    p.titulo as pelicula,
    p.genero_principal,
    p.es_animacion,
    ta.tarifa,
    pr.promocion,
    t.precio_lista,
    t.precio_cobrado,
    t.descuento,
    t.ingreso_neto,
    t.dias_anticipacion,
    t.semana_desde_estreno
from {{ ref('fact_ticket') }} as t
join {{ ref('dim_fecha') }} as ff on ff.fecha_key = t.fecha_funcion_key
join {{ ref('dim_fecha') }} as fv on fv.fecha_key = t.fecha_venta_key
join {{ ref('dim_franja_horaria') }} as h on h.hora = t.hora_funcion
join {{ ref('dim_sede') }} as s on s.sede_key = t.sede_key
join {{ ref('dim_sala') }} as sa on sa.sala_key = t.sala_key
join {{ ref('dim_pelicula') }} as p on p.pelicula_key = t.pelicula_key
join {{ ref('dim_tarifa') }} as ta on ta.tarifa_key = t.tarifa_key
join {{ ref('dim_promocion') }} as pr on pr.promocion_key = t.promocion_key
