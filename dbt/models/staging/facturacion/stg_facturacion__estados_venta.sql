select
    id_transaction_status as id_estado_venta,
    name_status as estado
from {{ source('facturacion', 'transaction_status') }}
