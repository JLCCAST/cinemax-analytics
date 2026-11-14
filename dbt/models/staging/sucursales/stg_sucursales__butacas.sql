select
    id_seat as id_butaca,
    id_room as id_sala,
    id_seat_type as id_tipo_butaca,
    row_name as fila,
    column_number as numero,
    row_name || column_number as codigo,
    -- En el origen es ACTIVO; en sedes y salas, Activo.
    initcap(status) as estado
from {{ source('sucursales', 'seat') }}
