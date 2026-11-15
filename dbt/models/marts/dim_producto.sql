select
    p.id_producto as producto_key,
    p.nombre as producto,
    c.categoria,
    c.categoria = 'Combos' as es_combo,
    p.precio as precio_actual
from {{ ref('stg_confiteria__productos') }} as p
left join {{ ref('stg_confiteria__categorias') }} as c on c.id_categoria = p.id_categoria
union all
select -1, 'Desconocido', 'Desconocida', false, null
