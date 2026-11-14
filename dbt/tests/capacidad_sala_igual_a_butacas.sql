{{ config(severity='warn') }}

-- room.capacity se escribe a mano; la capacidad real son las butacas activas.
select
    s.id_sala,
    s.capacidad,
    count(b.id_butaca) filter (where b.estado = 'Activo') as butacas_activas
from {{ ref('stg_sucursales__salas') }} as s
left join {{ ref('stg_sucursales__butacas') }} as b on b.id_sala = s.id_sala
group by s.id_sala, s.capacidad
having s.capacidad <> count(b.id_butaca) filter (where b.estado = 'Activo')
