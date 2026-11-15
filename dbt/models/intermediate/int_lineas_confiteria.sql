-- Una fila por producto vendido, con la película de la venta (para "combos por
-- película"). En un pedido solo de confitería la película es nula.
select
    l.id_linea,
    l.id_venta,
    l.id_producto,
    l.nombre_producto,
    c.categoria,
    c.categoria = 'Combos' as es_combo,
    l.cantidad,
    l.precio_unitario,
    l.importe_bruto,
    l.descuento,
    l.importe_neto,
    v.fecha_venta,
    v.id_usuario,
    v.id_sede,
    v.id_funcion,
    v.id_pelicula,
    v.id_promocion,
    v.solo_confiteria
from {{ ref('stg_facturacion__lineas_confiteria') }} as l
left join {{ ref('stg_confiteria__productos') }} as pr on pr.id_producto = l.id_producto
left join {{ ref('stg_confiteria__categorias') }} as c on c.id_categoria = pr.id_categoria
left join {{ ref('int_ventas') }} as v on v.id_venta = l.id_venta
