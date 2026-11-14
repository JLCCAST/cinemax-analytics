select
    id_seat_type as id_tipo_butaca,
    name_seat_type as tipo_butaca
from {{ source('sucursales', 'seat_type') }}
