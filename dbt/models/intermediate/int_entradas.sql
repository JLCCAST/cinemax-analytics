-- Una fila por butaca vendida, con la venta y la función. El precio de lista se
-- recalcula con la tarifa de CineMax (Tarifas.java) para comparar con el cobrado.
select
    e.id_entrada,
    e.id_venta,
    e.id_funcion,
    e.id_butaca,
    e.codigo_butaca,
    e.categoria_tarifa,
    e.precio,
    e.descuento,
    e.importe_neto,
    case e.categoria_tarifa
        when 'ADULTO' then f.precio_base
        when 'NINO' then round(f.precio_base * 0.55 * 2) / 2
        else round(f.precio_base * 0.65 * 2) / 2
    end as precio_tarifa,
    v.fecha_venta,
    v.id_usuario,
    v.id_promocion,
    f.id_pelicula,
    f.id_sala,
    f.id_sede,
    f.fecha_funcion,
    f.hora_inicio,
    f.semana_desde_estreno,
    v.dias_anticipacion
from {{ ref('stg_facturacion__entradas') }} as e
left join {{ ref('int_ventas') }} as v on v.id_venta = e.id_venta
left join {{ ref('int_funciones') }} as f on f.id_funcion = e.id_funcion
