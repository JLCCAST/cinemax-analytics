select
    id_transaction as id_venta,
    id_user as id_usuario,
    id_transaction_status as id_estado_venta,
    id_promotion as id_promocion,
    id_showtime as id_funcion,
    id_venue as id_sede,
    subtotal,
    discount_amount as descuento,
    total_amount as total,
    payment_method as metodo_pago,
    -- La base guarda UTC; el negocio se lee en hora de Lima.
    payment_date as pagado_en_utc,
    (payment_date at time zone 'UTC') at time zone 'America/Lima' as pagado_en_lima,
    created_at as creado_en_utc,
    -- Datos de la función al momento de la compra (V6), ya en hora de Lima.
    -- Nulos en un pedido solo de confitería.
    movie_title as titulo_pelicula,
    show_date as fecha_funcion,
    start_time as hora_funcion,
    room_name as nombre_sala,
    venue_name as nombre_sede
from {{ source('facturacion', 'sale_transaction') }}
