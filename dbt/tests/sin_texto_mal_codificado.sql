-- Texto UTF-8 leído como latin1: "María" termina como "MarÃ­a".
-- Pasaba con el init-script de MySQL; con Flyway ya no debería volver.
{% set columnas = {
    'stg_sucursales__departamentos': ['departamento'],
    'stg_sucursales__provincias': ['provincia'],
    'stg_sucursales__distritos': ['distrito'],
    'stg_sucursales__sedes': ['nombre', 'direccion'],
    'stg_sucursales__salas': ['nombre'],
    'stg_confiteria__categorias': ['categoria'],
    'stg_confiteria__productos': ['nombre', 'descripcion'],
    'stg_cartelera__peliculas': ['titulo', 'director'],
    'stg_cartelera__generos': ['genero'],
    'stg_facturacion__promociones': ['nombre', 'descripcion'],
} %}

{% set consultas = [] %}
{% for modelo, lista in columnas.items() %}
    {% for columna in lista %}
        {% do consultas.append(
            "select '" ~ modelo ~ "' as modelo, '" ~ columna ~ "' as columna, "
            ~ columna ~ "::text as valor from " ~ ref(modelo)
            ~ " where " ~ columna ~ " like '%Ã%'"
        ) %}
    {% endfor %}
{% endfor %}

{{ consultas | join('\nunion all\n') }}
