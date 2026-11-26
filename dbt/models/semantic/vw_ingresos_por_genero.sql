-- Una película con varios géneros reparte sus entradas e ingresos entre ellos (peso 1/n),
-- así la suma por género no cuenta dos veces la misma entrada.
select
    g.genero,
    f.anio_mes as mes_funcion,
    sum(g.peso) as entradas,
    sum(t.ingreso_neto * g.peso) as ingreso_neto
from {{ ref('fact_ticket') }} as t
join {{ ref('puente_pelicula_genero') }} as g on g.pelicula_key = t.pelicula_key
join {{ ref('dim_fecha') }} as f on f.fecha_key = t.fecha_funcion_key
group by g.genero, f.anio_mes
