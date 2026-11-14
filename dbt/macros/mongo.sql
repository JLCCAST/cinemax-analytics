{# Campos de MongoDB en Extended JSON relajado (ver la extracción de cartelera). #}

{# Fecha: {"$date": "ISO 8601"}, o {"$date": {"$numberLong": "ms"}} fuera de 1970-9999. #}
{% macro mongo_instante(campo) -%}
    case
        when jsonb_typeof({{ campo }} -> '$date') = 'string'
            then ({{ campo }} ->> '$date')::timestamptz
        when {{ campo }} -> '$date' ? '$numberLong'
            then to_timestamp(({{ campo }} -> '$date' ->> '$numberLong')::numeric / 1000)
    end
{%- endmacro %}

{# Decimal: Decimal128 ({"$numberDecimal": "18.00"}), texto ("18.00") o número. #}
{% macro mongo_decimal(campo) -%}
    case jsonb_typeof({{ campo }})
        when 'object' then ({{ campo }} ->> '$numberDecimal')::numeric
        when 'string' then ({{ campo }} #>> '{}')::numeric
        when 'number' then ({{ campo }} #>> '{}')::numeric
    end
{%- endmacro %}
