-- Lo que inyectó generador.defectos frente a lo que detectaron los chequeos.
-- Sin defectos inyectados, todo chequeo de tipo error debería dar 0.
select
    c.chequeo,
    c.tipo,
    coalesce(d.filas, 0) as filas_inyectadas,
    c.filas_afectadas as filas_detectadas,
    c.filas_revisadas,
    c.tipo <> 'error' or c.filas_afectadas = coalesce(d.filas, 0) as coincide
from {{ ref('calidad_chequeos') }} as c
left join {{ source('extraccion', 'defectos_inyectados') }} as d on d.chequeo = c.chequeo
