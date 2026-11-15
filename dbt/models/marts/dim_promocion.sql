select
    p.id_promocion as promocion_key,
    p.nombre as promocion,
    t.tipo_promocion,
    p.alcance,
    p.codigo_cupon is not null as es_cupon,
    p.dias_semana_iso,
    p.vigente_desde,
    p.vigente_hasta
from {{ ref('stg_facturacion__promociones') }} as p
left join {{ ref('stg_facturacion__tipos_promocion') }} as t on t.id_tipo_promocion = p.id_tipo_promocion
union all
select -1, 'Sin promoción', null, null, false, null, null, null
