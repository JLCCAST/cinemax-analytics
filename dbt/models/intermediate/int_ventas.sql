-- Una fila por venta, con lo que suman sus líneas para conciliar y los datos de
-- la función. En un pedido solo de confitería no hay función ni película.
with entradas as (
    select
        id_venta,
        count(*) as n_entradas,
        count(*) filter (where categoria_tarifa = 'NINO') as n_entradas_nino,
        sum(precio) as bruto,
        sum(descuento) as descuento
    from {{ ref('stg_facturacion__entradas') }}
    group by id_venta
),

confiteria as (
    select
        l.id_venta,
        sum(l.cantidad) as n_productos,
        sum(l.importe_bruto) as bruto,
        sum(l.descuento) as descuento,
        bool_or(c.categoria = 'Combos') as con_combo
    from {{ ref('stg_facturacion__lineas_confiteria') }} as l
    left join {{ ref('stg_confiteria__productos') }} as pr on pr.id_producto = l.id_producto
    left join {{ ref('stg_confiteria__categorias') }} as c on c.id_categoria = pr.id_categoria
    group by l.id_venta
)

select
    v.id_venta,
    v.id_usuario,
    v.pagado_en_lima,
    v.pagado_en_lima::date as fecha_venta,
    extract(hour from v.pagado_en_lima)::int as hora_venta,
    v.id_funcion,
    v.id_funcion is null as solo_confiteria,
    coalesce(v.id_sede, f.id_sede) as id_sede,
    f.id_pelicula,
    f.fecha_funcion,
    f.inicio as inicio_funcion,
    f.fecha_funcion - v.pagado_en_lima::date as dias_anticipacion,
    ev.estado,
    ev.estado in ('COMPLETADO', 'PAGADO') as pagada,
    v.metodo_pago,
    v.id_promocion,
    pr.nombre as promocion,
    v.subtotal,
    v.descuento,
    v.total,
    coalesce(e.n_entradas, 0) as n_entradas,
    coalesce(e.n_entradas_nino, 0) as n_entradas_nino,
    coalesce(c.n_productos, 0) as n_productos,
    c.id_venta is not null as con_confiteria,
    coalesce(c.con_combo, false) as con_combo,
    coalesce(e.bruto, 0) + coalesce(c.bruto, 0) as subtotal_lineas,
    coalesce(e.descuento, 0) + coalesce(c.descuento, 0) as descuento_lineas
from {{ ref('stg_facturacion__ventas') }} as v
left join {{ ref('stg_facturacion__estados_venta') }} as ev on ev.id_estado_venta = v.id_estado_venta
left join {{ ref('stg_facturacion__promociones') }} as pr on pr.id_promocion = v.id_promocion
left join {{ ref('int_funciones') }} as f on f.id_funcion = v.id_funcion
left join entradas as e on e.id_venta = v.id_venta
left join confiteria as c on c.id_venta = v.id_venta
