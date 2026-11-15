-- Un chequeo por fila: cuántas filas revisó y cuántas fallaron. "error" no debería
-- pasar nunca con datos limpios; "informativo" describe rarezas conocidas del origen.
{% set chequeos = [
    ('raw_igual_al_origen', 'error', 'raw',
     "select count(*) filter (where filas_origen <> filas_raw), count(*) from (select distinct on (tabla_raw) * from " ~ source('extraccion', 'cargas') ~ " order by tabla_raw, corrida desc) c"),
    ('texto_mal_codificado', 'error', 'stg_confiteria__productos, stg_sucursales__sedes',
     "select (select count(*) from " ~ ref('stg_confiteria__productos') ~ " where nombre like '%Ã%' or descripcion like '%Ã%') + (select count(*) from " ~ ref('stg_sucursales__sedes') ~ " where nombre like '%Ã%' or direccion like '%Ã%'), (select count(*) from " ~ ref('stg_confiteria__productos') ~ ") + (select count(*) from " ~ ref('stg_sucursales__sedes') ~ ")"),
    ('funciones_con_forma_del_seed', 'informativo', 'stg_cartelera__funciones',
     "select count(*) filter (where tipo_precio_origen = 'decimal128'), count(*) from " ~ ref('stg_cartelera__funciones')),
    ('desfase_butacas_disponibles', 'error', 'int_funciones',
     "select count(*) filter (where desfase_disponibles <> 0 or desfase_vendidas <> 0), count(*) from " ~ ref('int_funciones') ~ " where tipo_precio_origen <> 'decimal128'"),
    ('sobreventa', 'error', 'int_funciones',
     "select count(*) filter (where vendidas > capacidad), count(*) from " ~ ref('int_funciones')),
    ('capacidad_distinta_a_butacas', 'error', 'int_salas',
     "select count(*) filter (where capacidad <> capacidad_origen), count(*) from " ~ ref('int_salas')),
    ('funcion_en_otra_sede', 'error', 'int_funciones',
     "select count(*) filter (where sede_distinta_a_la_sala), count(*) from " ~ ref('int_funciones')),
    ('entrada_con_butaca_inexistente', 'error', 'stg_facturacion__entradas',
     "select count(*) filter (where b.id_butaca is null), count(*) from " ~ ref('stg_facturacion__entradas') ~ " e left join " ~ ref('stg_sucursales__butacas') ~ " b on b.id_butaca = e.id_butaca"),
    ('entrada_con_funcion_inexistente', 'error', 'stg_facturacion__entradas',
     "select count(*) filter (where f.id_funcion is null), count(*) from " ~ ref('stg_facturacion__entradas') ~ " e left join " ~ ref('stg_cartelera__funciones') ~ " f on f.id_funcion = e.id_funcion"),
    ('venta_con_cliente_inexistente', 'error', 'stg_facturacion__ventas',
     "select count(*) filter (where u.id_usuario is null), count(*) from " ~ ref('stg_facturacion__ventas') ~ " v left join " ~ ref('stg_usuarios__usuarios') ~ " u on u.id_usuario = v.id_usuario"),
    ('venta_que_no_cuadra', 'error', 'int_ventas',
     "select count(*) filter (where subtotal <> subtotal_lineas or descuento <> descuento_lineas or total <> subtotal - descuento), count(*) from " ~ ref('int_ventas')),
    ('venta_sin_lineas', 'error', 'int_ventas',
     "select count(*) filter (where n_entradas = 0 and n_productos = 0), count(*) from " ~ ref('int_ventas')),
    ('venta_despues_de_la_funcion', 'error', 'int_ventas',
     "select count(*) filter (where pagado_en_lima > inicio_funcion), count(*) from " ~ ref('int_ventas')),
    ('precio_fuera_de_tarifa', 'error', 'int_entradas',
     "select count(*) filter (where precio <> precio_tarifa), count(*) from " ~ ref('int_entradas')),
] %}

{% for nombre, tipo, tabla, consulta in chequeos %}
select
    '{{ nombre }}'::text as chequeo,
    '{{ tipo }}'::text as tipo,
    '{{ tabla }}'::text as tabla,
    r.fallas::bigint as filas_afectadas,
    r.revisadas::bigint as filas_revisadas
from ({{ consulta }}) as r (fallas, revisadas)
{% if not loop.last %}union all{% endif %}
{% endfor %}
