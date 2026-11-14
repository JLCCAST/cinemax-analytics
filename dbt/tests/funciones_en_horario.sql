-- Guarda contra un error de zona horaria: si alguien convierte la hora de la
-- función como si fuera UTC, una función de las 14:30 aparece a las 09:30 o antes.
select id_funcion, fecha_funcion, hora_inicio
from {{ ref('stg_cartelera__funciones') }}
where hora_inicio < time '09:00'
