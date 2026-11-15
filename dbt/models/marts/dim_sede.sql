select distinct
    s.id_sede as sede_key,
    s.sede,
    s.distrito,
    s.provincia,
    s.departamento,
    s.sede_abierta_desde,
    count(*) over (partition by s.id_sede) as salas
from {{ ref('int_salas') }} as s
union all
select -1, 'Desconocida', 'Desconocido', 'Desconocida', 'Desconocido', null, 0
