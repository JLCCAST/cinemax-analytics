select
    id_province as id_provincia,
    id_department as id_departamento,
    name_province as provincia
from {{ source('sucursales', 'province') }}
