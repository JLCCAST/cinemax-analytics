-- Cada venta cuadra con sus líneas, como la calcula facturacion-service:
-- subtotal = entradas + confitería, descuento = suma de los descuentos por línea
-- y total = subtotal - descuento.
with entradas as (
    select id_venta, sum(precio) as bruto, sum(descuento) as descuento
    from {{ ref('stg_facturacion__entradas') }}
    group by id_venta
),

confiteria as (
    select id_venta, sum(importe_bruto) as bruto, sum(descuento) as descuento
    from {{ ref('stg_facturacion__lineas_confiteria') }}
    group by id_venta
),

comparacion as (
    select
        v.id_venta,
        v.subtotal,
        v.descuento,
        v.total,
        coalesce(e.bruto, 0) + coalesce(c.bruto, 0) as subtotal_lineas,
        coalesce(e.descuento, 0) + coalesce(c.descuento, 0) as descuento_lineas
    from {{ ref('stg_facturacion__ventas') }} as v
    left join entradas as e on e.id_venta = v.id_venta
    left join confiteria as c on c.id_venta = v.id_venta
)

select *
from comparacion
where subtotal <> subtotal_lineas
   or descuento <> descuento_lineas
   or total <> subtotal - descuento
