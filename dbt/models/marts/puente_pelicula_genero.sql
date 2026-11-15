-- peso = 1 / número de géneros de la película: sumar medida × peso reparte sin duplicar.
select
    pg.id_pelicula as pelicula_key,
    g.genero,
    1.0 / count(*) over (partition by pg.id_pelicula) as peso
from {{ ref('stg_cartelera__pelicula_genero') }} as pg
join {{ ref('stg_cartelera__generos') }} as g on g.id_genero = pg.id_genero
