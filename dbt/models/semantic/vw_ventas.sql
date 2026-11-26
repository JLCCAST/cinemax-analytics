select
    v.id_venta,
    v.cliente_key as id_cliente,
    f.fecha as fecha_venta,
    f.anio_mes as mes_venta,
    f.nombre_dia as dia_venta,
    f.temporada as temporada_venta,
    v.hora_venta,
    s.sede,
    s.departamento,
    case when v.solo_confiteria then null else p.titulo end as pelicula,
    case when v.solo_confiteria then null else p.genero_principal end as genero_principal,
    pr.promocion,
    v.metodo_pago,
    v.solo_confiteria,
    v.n_entradas,
    v.n_productos,
    v.con_confiteria,
    v.con_combo,
    v.dias_anticipacion,
    v.subtotal,
    v.descuento,
    v.total,
    c.rango_edad,
    c.cohorte
from {{ ref('fact_venta') }} as v
join {{ ref('dim_fecha') }} as f on f.fecha_key = v.fecha_venta_key
join {{ ref('dim_sede') }} as s on s.sede_key = v.sede_key
join {{ ref('dim_pelicula') }} as p on p.pelicula_key = v.pelicula_key
join {{ ref('dim_promocion') }} as pr on pr.promocion_key = v.promocion_key
join {{ ref('dim_cliente') }} as c on c.cliente_key = v.cliente_key
