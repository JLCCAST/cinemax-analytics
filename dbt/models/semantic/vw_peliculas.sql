select
    titulo,
    director,
    duracion_min,
    fecha_estreno,
    clasificacion,
    genero_principal,
    generos,
    es_animacion
from {{ ref('dim_pelicula') }}
where pelicula_key <> '-1'
