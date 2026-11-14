select
    id_doc_type as id_tipo_documento,
    doc_name as tipo_documento
from {{ source('usuarios', 'document_type') }}
