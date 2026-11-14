select
    id_user as id_usuario,
    id_role as id_rol,
    id_doc_type as id_tipo_documento,
    id_venue as id_sede,
    datebirth as fecha_nacimiento,
    status as estado
from {{ source('usuarios', 'user_account') }}
