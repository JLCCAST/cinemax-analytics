select
    _id as id_clasificacion,
    doc ->> 'nameClassification' as clasificacion,
    doc ->> 'descriptionText' as descripcion
from {{ source('cartelera', 'classifications') }}
