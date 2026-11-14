-- La última carga de cada tabla copió todas las filas de su origen.
with ultima as (
    select distinct on (tabla_raw) *
    from {{ source('extraccion', 'cargas') }}
    order by tabla_raw, corrida desc
)

select tabla_raw, filas_origen, filas_raw
from ultima
where filas_origen <> filas_raw
