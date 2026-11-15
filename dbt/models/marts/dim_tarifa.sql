select * from (values
    ('ADULTO', 'Adulto', 1.00),
    ('NINO', 'Niño', 0.55),
    ('ADULTO_MAYOR', 'Adulto mayor', 0.65),
    ('DISCAPACITADO', 'Persona con discapacidad', 0.65),
    ('-1', 'Desconocida', null)
) as t (tarifa_key, tarifa, proporcion_del_precio_base)
