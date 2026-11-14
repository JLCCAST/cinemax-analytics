select
    id_role as id_rol,
    role_name as rol
from {{ source('usuarios', 'role') }}
