-- genero_principal: el primero de la lista de la película. Para repartir por todos
-- sus géneros sin duplicar, usar puente_pelicula_genero con su peso.
with primero as (
    select distinct on (pg.id_pelicula) pg.id_pelicula, g.genero
    from {{ ref('stg_cartelera__pelicula_genero') }} as pg
    join {{ ref('stg_cartelera__generos') }} as g on g.id_genero = pg.id_genero
    order by pg.id_pelicula, g.genero
),

generos as (
    select pg.id_pelicula, string_agg(g.genero, ', ' order by g.genero) as generos,
           bool_or(g.genero = 'Animación') as es_animacion
    from {{ ref('stg_cartelera__pelicula_genero') }} as pg
    join {{ ref('stg_cartelera__generos') }} as g on g.id_genero = pg.id_genero
    group by pg.id_pelicula
)

select
    p.id_pelicula as pelicula_key,
    p.titulo,
    p.director,
    p.duracion_min,
    p.fecha_estreno,
    to_char(p.fecha_estreno, 'YYYYMMDD')::int as fecha_estreno_key,
    c.clasificacion,
    coalesce(pr.genero, 'Sin género') as genero_principal,
    coalesce(g.generos, 'Sin género') as generos,
    coalesce(g.es_animacion, false) as es_animacion
from {{ ref('stg_cartelera__peliculas') }} as p
left join {{ ref('stg_cartelera__clasificaciones') }} as c on c.id_clasificacion = p.id_clasificacion
left join primero as pr on pr.id_pelicula = p.id_pelicula
left join generos as g on g.id_pelicula = p.id_pelicula
union all
select '-1', 'Desconocida', null, null, null, null, null, 'Sin género', 'Sin género', false
