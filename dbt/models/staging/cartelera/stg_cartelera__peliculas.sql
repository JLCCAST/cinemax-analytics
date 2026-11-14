-- status y premiereWeek guardan solo el valor de hoy: la antigüedad de una
-- película se calcula desde fecha_estreno.
select
    _id as id_pelicula,
    doc ->> 'titleMovie' as titulo,
    doc ->> 'director' as director,
    (doc ->> 'durationMinutes')::int as duracion_min,
    ({{ mongo_instante("doc -> 'releaseDate'") }} at time zone 'UTC')::date as fecha_estreno,
    doc ->> 'classificationId' as id_clasificacion,
    doc ->> 'status' as estado,
    coalesce((doc ->> 'isActive')::boolean, true) as activa,
    nullif(doc ->> 'posterUrl', '') as url_poster,
    {{ mongo_instante("doc -> 'createdAt'") }} as creada_en
from {{ source('cartelera', 'movies') }}
