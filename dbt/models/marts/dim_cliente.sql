-- Sin nombre, correo, documento ni teléfono. La cohorte es el mes de la primera compra,
-- porque user_account no guarda fecha de alta.
with compras as (
    select id_usuario, min(fecha_venta) as primera_compra, count(*) as compras
    from {{ ref('int_ventas') }}
    group by id_usuario
)

select
    u.id_usuario as cliente_key,
    td.tipo_documento,
    u.estado,
    date_part('year', age(date '{{ var("dim_fecha_hasta") }}', u.fecha_nacimiento))::int as edad,
    case
        when u.fecha_nacimiento is null then 'Sin dato'
        when age(date '{{ var("dim_fecha_hasta") }}', u.fecha_nacimiento) < interval '18 years' then 'Menor de 18'
        when age(date '{{ var("dim_fecha_hasta") }}', u.fecha_nacimiento) < interval '26 years' then '18 a 25'
        when age(date '{{ var("dim_fecha_hasta") }}', u.fecha_nacimiento) < interval '36 years' then '26 a 35'
        when age(date '{{ var("dim_fecha_hasta") }}', u.fecha_nacimiento) < interval '51 years' then '36 a 50'
        else '51 o más'
    end as rango_edad,
    c.primera_compra,
    to_char(c.primera_compra, 'YYYY-MM') as cohorte,
    coalesce(c.compras, 0) as compras
from {{ ref('stg_usuarios__usuarios') }} as u
left join {{ ref('stg_usuarios__tipos_documento') }} as td on td.id_tipo_documento = u.id_tipo_documento
left join compras as c on c.id_usuario = u.id_usuario
where u.id_rol = (select id_rol from {{ ref('stg_usuarios__roles') }} where rol = 'CLIENTE')
union all
select -1, null, 'Desconocido', null, 'Sin dato', null, null, 0
