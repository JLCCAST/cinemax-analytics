select
    h as hora,
    case
        when h < 15 then 'Matiné (antes de las 15)'
        when h < 18 then 'Tarde (15 a 18)'
        when h < 21 then 'Noche (18 a 21)'
        else 'Trasnoche (21 en adelante)'
    end as franja,
    case when h < 15 then 1 when h < 18 then 2 when h < 21 then 3 else 4 end as orden_franja
from generate_series(0, 23) as h
