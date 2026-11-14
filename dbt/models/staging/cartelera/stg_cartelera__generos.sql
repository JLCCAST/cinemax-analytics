select
    _id as id_genero,
    doc ->> 'nameGenre' as genero
from {{ source('cartelera', 'genres') }}
