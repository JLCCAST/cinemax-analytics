-- CineMax no vende una función que ya empezó. Las dos horas se comparan en hora de Lima.
select id_venta, pagado_en_lima, fecha_funcion, hora_funcion
from {{ ref('stg_facturacion__ventas') }}
where id_funcion is not null
  and pagado_en_lima > fecha_funcion + hora_funcion
