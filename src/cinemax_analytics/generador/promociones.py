"""Motor de promociones de facturacion-service (PromotionEngine.java), en Python.

Decide qué promoción aplica a una compra y cuánto descuenta en cada línea. Se
aplica una sola, la de mayor descuento; en un empate gana la que no limita usos
por cliente, luego la de mayor prioridad y luego la de menor id. Las condiciones
se evalúan con la fecha y la hora de la función, no con las de la compra.
"""

import calendar
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime, time
from decimal import ROUND_HALF_UP, Decimal

ENTRADAS = "ENTRADAS"
CONFITERIA = "CONFITERIA"
DIAS_DE_ESTRENO = 7
CENTIMO = Decimal("0.01")
CERO = Decimal("0.00")


@dataclass(frozen=True)
class Promocion:
    id: int
    nombre: str
    tipo: str  # PORCENTAJE, MONTO_FIJO, DOS_POR_UNO o ENTRADA_GRATIS
    vigente_desde: date
    vigente_hasta: date
    alcance: str = "TODO"  # ENTRADAS, CONFITERIA o TODO
    estado: str = "Activo"
    codigo: str | None = None
    porcentaje: Decimal | None = None
    monto_fijo: Decimal | None = None
    tope: Decimal | None = None
    compra_minima: Decimal | None = None
    entradas_minimas: int | None = None
    dias_semana: str | None = None  # ISO, separados por coma: 1 = lunes ... 7 = domingo
    desde_hora: time | None = None
    antes_de_hora: time | None = None
    excluye_estrenos: bool = False
    categoria_requerida: int | None = None
    condicion_cliente: str | None = None  # CUMPLEANOS
    usos_por_cliente: int | None = None  # por año calendario
    prioridad: int = 0


@dataclass(frozen=True)
class Entrada:
    categoria: str
    precio: Decimal


@dataclass(frozen=True)
class Snack:
    id_snack: int
    id_categoria: int
    precio_unitario: Decimal
    cantidad: int

    @property
    def importe(self) -> Decimal:
        return self.precio_unitario * self.cantidad


@dataclass(frozen=True)
class Cliente:
    nacimiento: date | None


@dataclass(frozen=True)
class Venta:
    """En un pedido solo de confitería, la fecha y la hora son las de la compra (Lima)."""

    fecha_funcion: date
    hora_funcion: time
    estreno: date | None
    cliente: Cliente | None
    cupon: str | None
    entradas: tuple[Entrada, ...] = ()
    snacks: tuple[Snack, ...] = ()

    @property
    def total_entradas(self) -> Decimal:
        return sum((e.precio for e in self.entradas), Decimal(0))

    @property
    def total_snacks(self) -> Decimal:
        return sum((s.importe for s in self.snacks), Decimal(0))

    @property
    def subtotal(self) -> Decimal:
        return self.total_entradas + self.total_snacks


@dataclass(frozen=True)
class Resultado:
    promocion: Promocion | None
    descuento: Decimal
    descuentos_entradas: tuple[Decimal, ...]
    descuentos_snacks: tuple[Decimal, ...]

    @property
    def aplico(self) -> bool:
        return self.promocion is not None


def evaluar(
    venta: Venta, promociones: list[Promocion], usos: dict[int, int] | None = None
) -> Resultado:
    """usos: veces que el cliente ya usó cada promoción este año (vacío sin cliente)."""
    usos = usos or {}
    candidatas = []
    for promocion in promociones:
        if not _aplica(promocion, venta, usos):
            continue
        descuento = _descuento(promocion, venta)
        if descuento > 0:
            candidatas.append((promocion, descuento))

    if not candidatas:
        return Resultado(None, CERO, (CERO,) * len(venta.entradas), (CERO,) * len(venta.snacks))

    promocion, descuento = max(
        candidatas,
        key=lambda c: (c[1], c[0].usos_por_cliente is None, c[0].prioridad or 0, -c[0].id),
    )
    return _repartir(promocion, descuento, venta)


# ---- Condiciones ------------------------------------------------------------------------


def _aplica(p: Promocion, venta: Venta, usos: dict[int, int]) -> bool:
    fecha = venta.fecha_funcion
    if p.estado != "Activo" or fecha < p.vigente_desde or fecha > p.vigente_hasta:
        return False
    if _tiene_texto(p.codigo) and p.codigo.lower() != (venta.cupon or "").strip().lower():
        return False
    if _tiene_texto(p.dias_semana) and fecha.isoweekday() not in _dias(p.dias_semana):
        return False
    if p.desde_hora is not None and venta.hora_funcion < p.desde_hora:
        return False
    if p.antes_de_hora is not None and not venta.hora_funcion < p.antes_de_hora:
        return False
    if p.excluye_estrenos and es_estreno(venta):
        return False
    if p.entradas_minimas is not None and len(venta.entradas) < p.entradas_minimas:
        return False
    if p.compra_minima is not None and venta.subtotal < p.compra_minima:
        return False
    if p.categoria_requerida is not None and not any(
        s.id_categoria == p.categoria_requerida for s in venta.snacks
    ):
        return False
    if p.condicion_cliente == "CUMPLEANOS" and not es_cumpleanos(venta):
        return False
    agotada = p.usos_por_cliente is not None and (
        venta.cliente is None or usos.get(p.id, 0) >= p.usos_por_cliente
    )
    return not agotada


def es_estreno(venta: Venta) -> bool:
    """La función es dentro de los 7 días siguientes al estreno (o antes, en preventa)."""
    return (
        venta.estreno is not None and (venta.fecha_funcion - venta.estreno).days < DIAS_DE_ESTRENO
    )


def es_cumpleanos(venta: Venta) -> bool:
    """El 29 de febrero se celebra el 28 en los años no bisiestos."""
    if venta.cliente is None or venta.cliente.nacimiento is None:
        return False
    nacimiento = venta.cliente.nacimiento
    fecha = venta.fecha_funcion
    if nacimiento.month == 2 and nacimiento.day == 29 and not calendar.isleap(fecha.year):
        return fecha.month == 2 and fecha.day == 28
    return (nacimiento.month, nacimiento.day) == (fecha.month, fecha.day)


def _dias(dias_iso: str) -> set[int]:
    return {int(d.strip()) for d in dias_iso.split(",") if d.strip()}


def _tiene_texto(valor: str | None) -> bool:
    return valor is not None and valor.strip() != ""


# ---- Beneficio --------------------------------------------------------------------------


def _a_entradas(p: Promocion) -> bool:
    return p.alcance != CONFITERIA


def _a_confiteria(p: Promocion) -> bool:
    return p.alcance != ENTRADAS


def _total_en_alcance(p: Promocion, venta: Venta) -> Decimal:
    total = Decimal(0)
    if _a_entradas(p):
        total += venta.total_entradas
    if _a_confiteria(p):
        total += venta.total_snacks
    return total


def _descuento(p: Promocion, venta: Venta) -> Decimal:
    alcance = _total_en_alcance(p, venta)
    if p.tipo == "PORCENTAJE":
        descuento = alcance * (p.porcentaje or Decimal(0)) / 100
    elif p.tipo == "MONTO_FIJO":
        descuento = p.monto_fijo or Decimal(0)
    elif p.tipo == "DOS_POR_UNO":
        descuento = _dos_por_uno(venta.entradas) if _a_entradas(p) else Decimal(0)
    elif p.tipo == "ENTRADA_GRATIS":
        precios = [e.precio for e in venta.entradas]
        descuento = max(precios, default=Decimal(0)) if _a_entradas(p) else Decimal(0)
    else:
        descuento = Decimal(0)

    if p.tope is not None:
        descuento = min(descuento, p.tope)
    return min(descuento, alcance).quantize(CENTIMO, rounding=ROUND_HALF_UP)


def _dos_por_uno(entradas: tuple[Entrada, ...]) -> Decimal:
    """En cada par de entradas, la más barata es gratis."""
    precios = sorted((e.precio for e in entradas), reverse=True)
    return sum(precios[1::2], Decimal(0))


# ---- Reparto por línea ------------------------------------------------------------------


def _centimos(valor: Decimal) -> int:
    return int((valor * 100).to_integral_exact())


def _repartir(p: Promocion, descuento: Decimal, venta: Venta) -> Resultado:
    """Proporcional al importe de cada línea del alcance, truncado al céntimo. El residuo
    va a la primera línea de mayor importe, para que la suma sea exacta."""
    importes = [_centimos(e.precio) if _a_entradas(p) else 0 for e in venta.entradas]
    importes += [_centimos(s.importe) if _a_confiteria(p) else 0 for s in venta.snacks]

    total = sum(importes)
    objetivo = _centimos(descuento)
    partes = [objetivo * importe // total for importe in importes]
    mayor = max(range(len(importes)), key=importes.__getitem__)
    partes[mayor] += objetivo - sum(partes)

    soles = tuple((Decimal(c) / 100).quantize(CENTIMO) for c in partes)
    n = len(venta.entradas)
    return Resultado(p, descuento, soles[:n], soles[n:])


# ---- Usos por cliente -------------------------------------------------------------------


@dataclass
class ContadorDeUsos:
    """Usos de las promociones con límite, como los cuenta CotizacionService.

    CineMax cuenta las ventas COMPLETADO cuyo created_at (guardado en UTC) cae entre
    el 1 de enero y el 31 de diciembre del año de la compra en hora de Lima. Compara
    esas fechas sin convertir la zona, y aquí se replica tal cual.
    """

    _ventas: dict[tuple[int, int], list[datetime]] = field(
        default_factory=lambda: defaultdict(list)
    )

    def usos(
        self, id_usuario: int, compra_en_lima: datetime, promociones: list[Promocion]
    ) -> dict[int, int]:
        desde = datetime(compra_en_lima.year, 1, 1)
        hasta = datetime(compra_en_lima.year + 1, 1, 1)
        return {
            p.id: sum(1 for creada in self._ventas[(id_usuario, p.id)] if desde <= creada < hasta)
            for p in promociones
            if p.usos_por_cliente is not None
        }

    def registrar(self, id_usuario: int, id_promocion: int | None, creada_en_utc: datetime):
        if id_promocion is not None:
            self._ventas[(id_usuario, id_promocion)].append(creada_en_utc.replace(tzinfo=None))


# ---- Lectura desde sales_db -------------------------------------------------------------

CONSULTA_PROMOCIONES = """
    SELECT p.id_promotion, p.name_promotion, t.name_promotion_type, p.start_date, p.end_date,
           p.applies_to, p.status, p.promotion_code, p.discount_percentage,
           p.discount_fixed_amount, p.max_discount_amount, p.minimum_purchase_amount,
           p.minimum_ticket_quantity, p.day_of_week, p.start_time_from, p.start_time_to,
           coalesce(p.exclude_premiere_movies, false), p.required_snack_category_id,
           p.customer_condition, p.max_uses_per_user, p.priority
    FROM promotion p
    JOIN promotion_type t ON t.id_promotion_type = p.id_promotion_type
    ORDER BY p.id_promotion
"""


def cargar_promociones(conexion) -> list[Promocion]:
    """Las promociones de sales_db (conexión de psycopg a facturación)."""
    return [Promocion(*fila) for fila in conexion.execute(CONSULTA_PROMOCIONES).fetchall()]
