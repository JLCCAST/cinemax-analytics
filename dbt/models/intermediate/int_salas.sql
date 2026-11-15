-- Una fila por sala, con su sede y la ubicación. La capacidad que vale es la de las
-- butacas activas; room.capacity se escribe a mano y queda como capacidad_origen.
with butacas as (
    select
        b.id_sala,
        count(*) filter (where b.estado = 'Activo') as butacas_activas,
        count(*) filter (where b.estado = 'Activo' and t.tipo_butaca = 'WHEELCHAIR')
            as butacas_silla_de_ruedas
    from {{ ref('stg_sucursales__butacas') }} as b
    left join {{ ref('stg_sucursales__tipos_butaca') }} as t on t.id_tipo_butaca = b.id_tipo_butaca
    group by b.id_sala
)

select
    s.id_sala,
    s.nombre as sala,
    s.nombre ilike '%vip%' as es_vip,
    s.estado,
    s.capacidad as capacidad_origen,
    coalesce(b.butacas_activas, 0) as capacidad,
    coalesce(b.butacas_silla_de_ruedas, 0) as butacas_silla_de_ruedas,
    se.id_sede,
    se.nombre as sede,
    se.creada_en::date as sede_abierta_desde,
    d.distrito,
    p.provincia,
    de.departamento
from {{ ref('stg_sucursales__salas') }} as s
join {{ ref('stg_sucursales__sedes') }} as se on se.id_sede = s.id_sede
join {{ ref('stg_sucursales__distritos') }} as d on d.id_distrito = se.id_distrito
join {{ ref('stg_sucursales__provincias') }} as p on p.id_provincia = d.id_provincia
join {{ ref('stg_sucursales__departamentos') }} as de on de.id_departamento = p.id_departamento
left join butacas as b on b.id_sala = s.id_sala
