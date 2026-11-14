select
    id_promotion_type as id_tipo_promocion,
    name_promotion_type as tipo_promocion
from {{ source('facturacion', 'promotion_type') }}
