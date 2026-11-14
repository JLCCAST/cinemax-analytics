{# Usa el esquema configurado tal cual (staging, marts), sin el prefijo del target. #}
{% macro generate_schema_name(custom_schema_name, node) -%}
    {{ custom_schema_name | trim if custom_schema_name else target.schema }}
{%- endmacro %}
