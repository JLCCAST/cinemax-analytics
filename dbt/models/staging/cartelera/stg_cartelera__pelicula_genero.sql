select
    p._id as id_pelicula,
    g.id_genero
from {{ source('cartelera', 'movies') }} as p
cross join lateral jsonb_array_elements_text(coalesce(p.doc -> 'genreIds', '[]'::jsonb)) as g (id_genero)
