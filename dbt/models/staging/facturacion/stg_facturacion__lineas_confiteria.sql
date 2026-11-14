select
    id_detail as id_linea,
    id_transaction as id_venta,
    id_snack as id_producto,
    snack_name as nombre_producto,
    quantity as cantidad,
    unit_price as precio_unitario,
    quantity * unit_price as importe_bruto,
    discount_amount as descuento,
    quantity * unit_price - discount_amount as importe_neto,
    is_delivered as entregada
from {{ source('facturacion', 'sale_snack_detail') }}
