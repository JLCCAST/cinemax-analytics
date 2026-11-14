-- snack.id_venue queda fuera: vale 1 en todos los productos, aunque se venden en todas las sedes.
select
    id_snack as id_producto,
    id_snack_category as id_categoria,
    name_snack as nombre,
    description_snack as descripcion,
    price as precio,
    initcap(status) as estado,
    created_at as creado_en
from {{ source('confiteria', 'snack') }}
