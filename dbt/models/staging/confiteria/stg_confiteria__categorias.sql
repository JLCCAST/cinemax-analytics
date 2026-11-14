select
    id_snack_category as id_categoria,
    name_category as categoria
from {{ source('confiteria', 'snack_category') }}
