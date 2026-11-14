"""Parámetros por defecto del generador de ventas sintéticas."""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Parametros:
    ocupacion_base: float = 0.22

    # Lunes (1) a domingo (7)
    factor_dia_semana: dict[int, float] = field(
        default_factory=lambda: {
            1: 0.75,
            2: 0.90,
            3: 1.05,
            4: 0.85,
            5: 1.25,
            6: 1.45,
            7: 1.35,
        }
    )

    # Por tramo horario de inicio de la función
    factor_hora_antes_14: float = 0.60
    factor_hora_14_a_18: float = 0.90
    factor_hora_18_a_21: float = 1.30
    factor_hora_despues_21: float = 1.00

    # Temporadas (dbt/seeds/temporadas.csv) y feriados (dbt/seeds/feriados_peru.csv)
    factor_temporada: dict[str, float] = field(
        default_factory=lambda: {
            "Verano": 1.15,
            "Vacaciones de medio año": 1.20,
            "Fin de año": 1.10,
            "Regular": 1.00,
        }
    )
    factor_feriado: float = 1.30

    # Popularidad por película y decaimiento semanal
    popularidad_mu: float = 0.0
    popularidad_sigma: float = 0.60
    retencion_semanal: float = 0.60
    dispersion_binomial_negativa: float = 4.0

    # Distribución de tamaños de grupo (1, 2, 3, 4, 5, 6 entradas)
    tamanos_grupo: tuple[int, ...] = (1, 2, 3, 4, 5, 6)
    pesos_grupo: tuple[float, ...] = (0.30, 0.40, 0.12, 0.12, 0.04, 0.02)

    # Proporción de tarifas según si la película es de animación o no
    nino_animacion: float = 0.35
    nino_resto: float = 0.08
    adulto_mayor: float = 0.06
    discapacitado: float = 0.01

    # Confitería
    prob_snack_1_entrada: float = 0.34
    prob_snack_2_entradas: float = 0.48
    prob_snack_3_o_mas: float = 0.62
    prob_combo_1_entrada: float = 0.15
    prob_combo_2_entradas: float = 0.45
    prob_combo_3_o_mas: float = 0.65
    proporcion_solo_confiteria: float = 0.05

    # Pagos, promociones y clientes
    prob_yape: float = 0.58
    prob_cupon_app10: float = 0.08
    factor_cumpleanos: float = 3.0
    tasa_cancelacion_funciones: float = 0.005

    # Tamaños de catálogo
    total_peliculas_nuevas: int = 52
    total_clientes: int = 20000

    def factor_hora(self, hora: int) -> float:
        if hora < 14:
            return self.factor_hora_antes_14
        if hora < 18:
            return self.factor_hora_14_a_18
        if hora < 21:
            return self.factor_hora_18_a_21
        return self.factor_hora_despues_21
