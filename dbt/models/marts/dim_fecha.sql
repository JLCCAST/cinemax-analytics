with dias as (
    select dia::date as fecha
    from generate_series(
        date '{{ var("dim_fecha_desde") }}',
        date '{{ var("dim_fecha_hasta") }}',
        interval '1 day'
    ) as dia
)

select
    to_char(d.fecha, 'YYYYMMDD')::int as fecha_key,
    d.fecha,
    extract(year from d.fecha)::int as anio,
    extract(quarter from d.fecha)::int as trimestre,
    extract(month from d.fecha)::int as mes,
    (array['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 'Julio', 'Agosto',
           'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'])[extract(month from d.fecha)::int]
        as nombre_mes,
    to_char(d.fecha, 'YYYY-MM') as anio_mes,
    extract(week from d.fecha)::int as semana_iso,
    extract(day from d.fecha)::int as dia_mes,
    extract(isodow from d.fecha)::int as dia_semana,
    (array['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo'])
        [extract(isodow from d.fecha)::int] as nombre_dia,
    extract(isodow from d.fecha) in (6, 7) as es_fin_de_semana,
    f.feriado is not null as es_feriado,
    f.feriado,
    extract(isodow from d.fecha) = 4 as es_jueves_de_estreno,
    coalesce(t.temporada, 'Regular') as temporada
from dias as d
left join {{ ref('feriados_peru') }} as f on f.fecha = d.fecha
left join {{ ref('temporadas') }} as t
    on to_char(d.fecha, 'MM-DD') between t.desde and t.hasta
