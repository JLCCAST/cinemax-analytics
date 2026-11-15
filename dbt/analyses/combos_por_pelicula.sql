-- Tasa de adjunción de combos por película: % de ventas con entradas que llevan combo.
select
    p.titulo,
    p.genero_principal,
    count(*) as ventas,
    round(avg(v.con_combo::int) * 100, 1) as con_combo_pct
from {{ ref('fact_venta') }} as v
join {{ ref('dim_pelicula') }} as p on p.pelicula_key = v.pelicula_key
where not v.solo_confiteria
group by p.titulo, p.genero_principal
having count(*) >= 500
order by con_combo_pct desc
limit 15
