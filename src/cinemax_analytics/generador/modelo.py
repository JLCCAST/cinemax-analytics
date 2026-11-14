"""Estructuras de datos del plan, identificadores deterministas y cálculo de huella."""

import hashlib
import json
from dataclasses import dataclass, field
from datetime import date, datetime, time
from decimal import Decimal

import numpy as np
from bson import ObjectId

from cinemax_analytics.generador.promociones import Promocion


def object_id_determinista(instante_utc: datetime, rng: np.random.Generator) -> ObjectId:
    segundos = int(instante_utc.timestamp()) & 0xFFFFFFFF
    prefijo = segundos.to_bytes(4, byteorder="big")
    sufijo = bytes(rng.integers(0, 256, size=8, dtype=np.uint8))
    return ObjectId(prefijo + sufijo)


def codigo_qr(rng: np.random.Generator) -> str:
    aleatorio = bytes(rng.integers(0, 256, size=6, dtype=np.uint8)).hex().upper()
    return f"TXN-{aleatorio}"


@dataclass(frozen=True)
class SedePlan:
    id_venue: int
    name_venue: str
    address: str
    phone_number: str
    status: str
    created_at: datetime
    id_district: int
    latitude: float
    longitude: float
    es_nueva: bool = True


@dataclass(frozen=True)
class SalaPlan:
    id_room: int
    name_room: str
    capacity: int
    num_rows: int
    seats_per_row: int
    status: str
    id_venue: int
    es_vip: bool
    es_nueva: bool = True


@dataclass(frozen=True)
class ButacaPlan:
    id_seat: int
    row_name: str
    column_number: int
    status: str
    id_seat_type: int
    id_room: int
    es_nueva: bool = True

    @property
    def codigo(self) -> str:
        return f"{self.row_name}{self.column_number}"


@dataclass(frozen=True)
class ProductoPlan:
    id_snack: int
    id_venue: int
    id_snack_category: int
    name_snack: str
    description_snack: str
    precio_inicial: Decimal
    price: Decimal
    fecha_cambio_precio: date | None
    stock: int
    status: str
    created_at: datetime | None
    es_nuevo: bool = True

    def precio_en(self, fecha: date) -> Decimal:
        if self.fecha_cambio_precio is not None and fecha < self.fecha_cambio_precio:
            return self.precio_inicial
        return self.price


@dataclass(frozen=True)
class StockSedePlan:
    id_snack: int
    id_venue: int
    stock: int
    status: str = "Activo"


@dataclass(frozen=True)
class PeliculaPlan:
    id: ObjectId
    title_movie: str
    synopsis: str
    duration_minutes: int
    poster_url: str
    director: str
    release_date: datetime
    status: str
    created_at: datetime
    is_active: bool
    premiere_week: bool
    genre_ids: tuple[str, ...]
    classification_id: str
    es_animacion: bool
    popularidad: float
    semanas_cartelera: int

    @property
    def id_hex(self) -> str:
        return str(self.id)

    @property
    def fecha_estreno(self) -> date:
        return self.release_date.date()


@dataclass
class FuncionPlan:
    id: ObjectId
    show_date: datetime
    start_time: datetime
    end_time: datetime
    language_format: str
    base_ticket_price: str
    available_seats: int
    status: str
    movie_id: str
    id_room: int
    id_venue: int
    sold_seats: int = 0

    @property
    def id_hex(self) -> str:
        return str(self.id)

    @property
    def fecha(self) -> date:
        return self.show_date.date()

    @property
    def fecha_creacion(self) -> date:
        return self.start_time.date()

    @property
    def hora_inicio(self) -> time:
        return self.start_time.time().replace(tzinfo=None)

    @property
    def hora_fin(self) -> time:
        return self.end_time.time().replace(tzinfo=None)

    @property
    def precio_decimal(self) -> Decimal:
        return Decimal(self.base_ticket_price)


@dataclass(frozen=True)
class ClientePlan:
    id_user: int
    datebirth: date | None
    document_number: str
    email: str
    first_name: str
    last_name: str
    password: str
    phone: str | None
    status: str
    id_doc_type: int
    id_role: int
    fecha_alta: date
    peso: float


@dataclass(frozen=True)
class EntradaVentaPlan:
    id_ticket: int
    id_transaction: int
    id_showtime: str
    id_seat: int
    seat_code: str
    fare_category: str
    ticket_price: Decimal
    discount_amount: Decimal
    is_used: bool = False


@dataclass(frozen=True)
class SnackVentaPlan:
    id_detail: int
    id_transaction: int
    id_snack: int
    snack_name: str
    quantity: int
    unit_price: Decimal
    discount_amount: Decimal
    is_delivered: bool = False


@dataclass(frozen=True)
class TransaccionPlan:
    id_transaction: int
    id_user: int
    id_transaction_status: int
    subtotal: Decimal
    discount_amount: Decimal
    total_amount: Decimal
    payment_method: str
    created_at: datetime
    payment_date: datetime
    qr_code_data: str
    id_promotion: int | None
    id_showtime: str | None
    id_venue: int
    movie_title: str | None
    show_date: date | None
    start_time: time | None
    room_name: str | None
    venue_name: str
    entradas: tuple[EntradaVentaPlan, ...] = ()
    snacks: tuple[SnackVentaPlan, ...] = ()


@dataclass
class CatalogoPlan:
    sedes: list[SedePlan]
    salas: list[SalaPlan]
    butacas: list[ButacaPlan]
    productos: list[ProductoPlan]
    stocks_nuevos: list[StockSedePlan]
    peliculas: list[PeliculaPlan]
    clientes: list[ClientePlan]
    promociones: list[Promocion]
    id_estado_completado: int


@dataclass
class PlanGeneracion:
    semilla: int
    desde: date
    hasta: date
    escala: float
    catalogo: CatalogoPlan
    funciones: list[FuncionPlan] = field(default_factory=list)
    ventas: list[TransaccionPlan] = field(default_factory=list)
    total_entradas: int = 0
    total_lineas_snack: int = 0


def calcular_huella(plan: PlanGeneracion) -> str:
    digest = hashlib.sha256()

    def agregar(clave: str, obj) -> None:
        linea = json.dumps([clave, obj], sort_keys=True, separators=(",", ":"))
        digest.update(linea.encode("utf-8"))
        digest.update(b"\n")

    agregar(
        "meta",
        {
            "semilla": plan.semilla,
            "desde": plan.desde.isoformat(),
            "hasta": plan.hasta.isoformat(),
            "escala": plan.escala,
        },
    )
    for s in plan.catalogo.sedes:
        if s.es_nueva:
            agregar("sede", [s.id_venue, s.name_venue, s.created_at.isoformat(), s.id_district])
    for r in plan.catalogo.salas:
        if r.es_nueva:
            agregar("sala", [r.id_room, r.id_venue, r.name_room, r.capacity])
    for b in plan.catalogo.butacas:
        if b.es_nueva:
            agregar("butaca", [b.id_seat, b.id_room, b.row_name, b.column_number, b.id_seat_type])
    for p in plan.catalogo.productos:
        if p.es_nuevo:
            agregar("producto", [p.id_snack, p.name_snack, str(p.price), p.id_snack_category])
    for m in plan.catalogo.peliculas:
        agregar(
            "pelicula",
            [
                m.id_hex,
                m.title_movie,
                m.duration_minutes,
                m.release_date.isoformat(),
                m.created_at.isoformat(),
                m.status,
                m.is_active,
                list(m.genre_ids),
                m.classification_id,
            ],
        )
    for c in plan.catalogo.clientes:
        agregar(
            "cliente",
            [
                c.id_user,
                c.email,
                c.document_number,
                c.datebirth.isoformat() if c.datebirth else None,
            ],
        )
    for f in plan.funciones:
        agregar(
            "funcion",
            [
                f.id_hex,
                f.movie_id,
                f.id_room,
                f.id_venue,
                f.show_date.isoformat(),
                f.start_time.isoformat(),
                f.end_time.isoformat(),
                f.language_format,
                f.base_ticket_price,
                f.available_seats,
                f.sold_seats,
                f.status,
            ],
        )
    for v in plan.ventas:
        agregar(
            "venta",
            [
                v.id_transaction,
                v.id_user,
                v.id_showtime,
                v.id_venue,
                str(v.subtotal),
                str(v.discount_amount),
                str(v.total_amount),
                v.payment_method,
                v.created_at.isoformat(),
                v.qr_code_data,
                v.id_promotion,
                [
                    [
                        e.id_ticket,
                        e.id_seat,
                        e.fare_category,
                        str(e.ticket_price),
                        str(e.discount_amount),
                    ]
                    for e in v.entradas
                ],
                [
                    [
                        s.id_detail,
                        s.id_snack,
                        s.quantity,
                        str(s.unit_price),
                        str(s.discount_amount),
                    ]
                    for s in v.snacks
                ],
            ],
        )
    return digest.hexdigest()
