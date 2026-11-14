select
    id_department as id_departamento,
    name_department as departamento
from {{ source('sucursales', 'department') }}
