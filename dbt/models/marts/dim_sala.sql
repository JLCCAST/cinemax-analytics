select
    id_sala as sala_key,
    sala,
    es_vip,
    capacidad,
    butacas_silla_de_ruedas,
    id_sede as sede_key,
    sede,
    distrito,
    provincia,
    departamento
from {{ ref('int_salas') }}
union all
select -1, 'Desconocida', false, 0, 0, -1, 'Desconocida', 'Desconocido', 'Desconocida', 'Desconocido'
