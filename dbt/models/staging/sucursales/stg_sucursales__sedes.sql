select
    id_venue as id_sede,
    id_district as id_distrito,
    name_venue as nombre,
    address as direccion,
    latitude as latitud,
    longitude as longitud,
    initcap(status) as estado,
    created_at as creada_en
from {{ source('sucursales', 'venue') }}
