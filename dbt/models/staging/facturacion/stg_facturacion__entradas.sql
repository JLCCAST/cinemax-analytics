select
    id_ticket as id_entrada,
    id_transaction as id_venta,
    id_showtime as id_funcion,
    id_seat as id_butaca,
    seat_code as codigo_butaca,
    fare_category as categoria_tarifa,
    ticket_price as precio,
    discount_amount as descuento,
    ticket_price - discount_amount as importe_neto,
    is_used as usada
from {{ source('facturacion', 'sale_ticket_detail') }}
