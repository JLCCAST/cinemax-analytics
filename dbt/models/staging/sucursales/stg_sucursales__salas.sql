select
    id_room as id_sala,
    id_venue as id_sede,
    name_room as nombre,
    capacity as capacidad,
    num_rows as filas,
    seats_per_row as butacas_por_fila,
    initcap(status) as estado
from {{ source('sucursales', 'room') }}
