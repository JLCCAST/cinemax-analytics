select
    c.id_linea,
    c.id_venta,
    f.fecha as fecha_venta,
    f.anio_mes as mes_venta,
    s.sede,
    case when c.solo_confiteria then null else p.titulo end as pelicula,
    pr.producto,
    pr.categoria,
    pr.es_combo,
    c.solo_confiteria,
    c.cantidad,
    c.precio_unitario,
    c.importe_bruto,
    c.descuento,
    c.importe_neto
from {{ ref('fact_confiteria') }} as c
join {{ ref('dim_fecha') }} as f on f.fecha_key = c.fecha_venta_key
join {{ ref('dim_sede') }} as s on s.sede_key = c.sede_key
join {{ ref('dim_pelicula') }} as p on p.pelicula_key = c.pelicula_key
join {{ ref('dim_producto') }} as pr on pr.producto_key = c.producto_key
