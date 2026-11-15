-- Una fila por butaca vendida. Solo ventas pagadas.
select
    e.id_entrada,
    e.id_venta,
    e.id_funcion,
    to_char(e.fecha_venta, 'YYYYMMDD')::int as fecha_venta_key,
    to_char(e.fecha_funcion, 'YYYYMMDD')::int as fecha_funcion_key,
    extract(hour from e.hora_inicio)::int as hora_funcion,
    coalesce(p.pelicula_key, '-1') as pelicula_key,
    coalesce(s.sala_key, -1) as sala_key,
    coalesce(s.sede_key, -1) as sede_key,
    coalesce(t.tarifa_key, '-1') as tarifa_key,
    coalesce(e.id_promocion, -1) as promocion_key,
    coalesce(c.cliente_key, -1) as cliente_key,
    e.precio_tarifa as precio_lista,
    e.precio as precio_cobrado,
    e.descuento,
    e.importe_neto as ingreso_neto,
    e.dias_anticipacion,
    e.semana_desde_estreno
from {{ ref('int_entradas') }} as e
join {{ ref('int_ventas') }} as v on v.id_venta = e.id_venta and v.pagada
left join {{ ref('dim_pelicula') }} as p on p.pelicula_key = e.id_pelicula
left join {{ ref('dim_sala') }} as s on s.sala_key = e.id_sala
left join {{ ref('dim_tarifa') }} as t on t.tarifa_key = e.categoria_tarifa
left join {{ ref('dim_cliente') }} as c on c.cliente_key = e.id_usuario
