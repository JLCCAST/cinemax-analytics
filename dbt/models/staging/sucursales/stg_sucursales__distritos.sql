select
    id_district as id_distrito,
    id_province as id_provincia,
    name_district as distrito
from {{ source('sucursales', 'district') }}
