-- Una fila por transacción pagada: ticket promedio, medio de pago, confitería y promociones
-- sin duplicar filas al cruzar entradas con productos.
select
    v.id_venta,
    v.id_funcion,
    to_char(v.fecha_venta, 'YYYYMMDD')::int as fecha_venta_key,
    v.hora_venta,
    coalesce(c.cliente_key, -1) as cliente_key,
    coalesce(v.id_sede, -1) as sede_key,
    coalesce(p.pelicula_key, '-1') as pelicula_key,
    coalesce(v.id_promocion, -1) as promocion_key,
    v.metodo_pago,
    v.solo_confiteria,
    v.n_entradas,
    v.n_productos,
    v.con_confiteria,
    v.con_combo,
    v.dias_anticipacion,
    v.subtotal,
    v.descuento,
    v.total
from {{ ref('int_ventas') }} as v
left join {{ ref('dim_pelicula') }} as p on p.pelicula_key = v.id_pelicula
left join {{ ref('dim_cliente') }} as c on c.cliente_key = v.id_usuario
where v.pagada
