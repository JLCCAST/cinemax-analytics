-- Una fila por producto vendido. pelicula_key = '-1' en los pedidos solo de confitería.
select
    l.id_linea,
    l.id_venta,
    l.id_funcion,
    to_char(l.fecha_venta, 'YYYYMMDD')::int as fecha_venta_key,
    coalesce(pr.producto_key, -1) as producto_key,
    coalesce(l.id_sede, -1) as sede_key,
    coalesce(p.pelicula_key, '-1') as pelicula_key,
    coalesce(l.id_promocion, -1) as promocion_key,
    coalesce(c.cliente_key, -1) as cliente_key,
    l.solo_confiteria,
    l.cantidad,
    l.precio_unitario,
    l.importe_bruto,
    l.descuento,
    l.importe_neto
from {{ ref('int_lineas_confiteria') }} as l
join {{ ref('int_ventas') }} as v on v.id_venta = l.id_venta and v.pagada
left join {{ ref('dim_producto') }} as pr on pr.producto_key = l.id_producto
left join {{ ref('dim_pelicula') }} as p on p.pelicula_key = l.id_pelicula
left join {{ ref('dim_cliente') }} as c on c.cliente_key = l.id_usuario
