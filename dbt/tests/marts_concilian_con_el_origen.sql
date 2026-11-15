-- Los hechos suman lo mismo que las fuentes: nada se pierde ni se duplica en el modelo.
with esperado as (
    select
        count(*) as ventas,
        sum(subtotal_lineas - descuento_lineas) as neto_lineas,
        sum(total) as total,
        sum(n_entradas) as entradas
    from {{ ref('int_ventas') }}
    where pagada
),

modelo as (
    select
        (select count(*) from {{ ref('fact_venta') }}) as ventas,
        (select sum(ingreso_neto) from {{ ref('fact_ticket') }})
            + (select coalesce(sum(importe_neto), 0) from {{ ref('fact_confiteria') }}) as neto_lineas,
        (select sum(total) from {{ ref('fact_venta') }}) as total,
        (select count(*) from {{ ref('fact_ticket') }}) as entradas
)

select *
from esperado, modelo
where esperado.ventas <> modelo.ventas
   or esperado.neto_lineas <> modelo.neto_lineas
   or esperado.total <> modelo.total
   or esperado.entradas <> modelo.entradas
