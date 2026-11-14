-- Hay dos formas de documento. El seed de CineMax guarda startTime con fecha y hora,
-- y el precio en Decimal128; cartelera-service guarda LocalTime y BigDecimal.
-- Las horas son de Lima guardadas como si fueran UTC: se toma la hora del día sin convertir.
select
    _id as id_funcion,
    doc ->> 'movieId' as id_pelicula,
    coalesce(doc ->> 'idRoom', doc ->> 'roomId')::int as id_sala,
    coalesce(doc ->> 'idVenue', doc ->> 'venueId')::int as id_sede,
    ({{ mongo_instante("doc -> 'showDate'") }} at time zone 'UTC')::date as fecha_funcion,
    ({{ mongo_instante("doc -> 'startTime'") }} at time zone 'UTC')::time as hora_inicio,
    ({{ mongo_instante("doc -> 'endTime'") }} at time zone 'UTC')::time as hora_fin,
    doc ->> 'languageFormat' as idioma,
    {{ mongo_decimal("doc -> 'baseTicketPrice'") }} as precio_base,
    case jsonb_typeof(doc -> 'baseTicketPrice')
        when 'object' then 'decimal128'
        when 'string' then 'texto'
        when 'number' then 'numero'
    end as tipo_precio_origen,
    (doc ->> 'availableSeats')::int as butacas_disponibles,
    (doc ->> 'soldSeats')::int as butacas_vendidas,
    doc ->> 'status' as estado
from {{ source('cartelera', 'showtimes') }}
