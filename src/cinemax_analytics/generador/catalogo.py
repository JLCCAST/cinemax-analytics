"""Generación determinista del catálogo: sedes, salas, butacas, snacks, películas y clientes."""

import unicodedata
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal

import bcrypt
import numpy as np
from faker import Faker

from cinemax_analytics.generador.lectura import EstadoSemilla
from cinemax_analytics.generador.modelo import (
    ButacaPlan,
    CatalogoPlan,
    ClientePlan,
    PeliculaPlan,
    ProductoPlan,
    SalaPlan,
    SedePlan,
    StockSedePlan,
    object_id_determinista,
)
from cinemax_analytics.generador.parametros import Parametros

ALFABETO_BCRYPT = "./ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"

PRODUCTOS_NUEVOS = (
    # (categoría, nombre, descripción, precio_inicial, precio_final, stock)
    (2, "Combo Dúo Clásico", "2 canchitas medianas + 2 gaseosas medianas", "28.00", "30.00", 45),
    (
        2,
        "Combo Mega Amigos",
        "2 canchitas grandes + 3 gaseosas grandes + nachos",
        "52.00",
        "55.00",
        30,
    ),
    (
        2,
        "Combo Dulce Pareja",
        "Canchita dulce grande + 2 bebidas + 2 chocolates",
        "34.00",
        "36.00",
        35,
    ),
    (
        2,
        "Combo Individual Plus",
        "Canchita mediana + gaseosa mediana + barra de cereal",
        "19.00",
        "20.00",
        50,
    ),
    (1, "Gaseosa Mediana", "Vaso mediano de gaseosa a elección", "7.00", "7.50", 120),
    (1, "Chicha Morada Grande", "Vaso grande de chicha morada artesanal", "8.50", "9.00", 90),
    (1, "Café Americano", "Vaso térmico de café pasado 12 oz", "6.50", "6.50", 70),
    (1, "Jugo de Durazno", "Botella de néctar de durazno 400ml", "6.00", "6.00", 85),
    (3, "Gomitas Ácidas", "Bolsa de gomitas frutales azucaradas 100g", "7.50", "8.00", 95),
    (
        3,
        "Canchita Acaramelada",
        "Balde mediano de canchita bañada en caramelo",
        "13.00",
        "14.00",
        65,
    ),
    (
        3,
        "Alfajor Artesanal",
        "Alfajor relleno de manjarblanco con azúcar impalpable",
        "6.50",
        "7.00",
        60,
    ),
    (3, "Chocoteja de Pecanas", "Chocoteja rellena de manjar y pecanas", "5.50", "5.50", 75),
    (3, "Barra de Chocolate Bitter", "Tableta de chocolate 60% cacao peruano", "8.50", "9.00", 70),
    (4, "Canchita Mediana", "Canchita salada tamaño mediano", "9.50", "10.00", 110),
    (
        4,
        "Canchita Gigante",
        "Balde familiar de canchita salada con mantequilla",
        "15.00",
        "16.00",
        80,
    ),
    (
        4,
        "Hot Dog Clásico",
        "Pan artesanal con salchicha frankfurter y salsas",
        "11.00",
        "12.00",
        55,
    ),
    (
        4,
        "Tequeños con Guacamole",
        "Porción de 6 tequeños de queso con salsa guacamole",
        "14.00",
        "15.00",
        50,
    ),
)

CATALOGO_PELICULAS = (
    ("El Último Faro del Sur", "Valeria Montesinos", ("Drama", "Aventura"), "PG-13"),
    (
        "Guardianes del Bosque Nublado",
        "Mateo Santisteban",
        ("Animación", "Aventura", "Comedia"),
        "APT",
    ),
    ("Crónicas de Titán", "Alejandro Vera", ("Ciencia Ficción", "Acción"), "PG-13"),
    ("La Sombra en el Espejo", "Lucía Peñaranda", ("Terror", "Drama"), "PG-18"),
    ("Amor en Tiempos de Lluvia", "Camila Orbegoso", ("Romance", "Comedia"), "APT"),
    ("Operación Cordillera", "Ricardo Zambrano", ("Acción", "Aventura"), "PG-13"),
    ("El Misterio de la Huaca Perdida", "Fernando Belaunde", ("Aventura", "Comedia"), "APT"),
    ("Pequeños Inventores", "Sofía Castañeda", ("Animación", "Comedia"), "APT"),
    ("Susurros en la Niebla", "Héctor Villarán", ("Terror",), "PG-18"),
    ("Horizonte Cuántico", "Daniela Aramburú", ("Ciencia Ficción", "Drama"), "PG-13"),
    ("Dos Destinos y un Café", "Mariana Olaechea", ("Romance", "Drama"), "PG-13"),
    ("El Vuelo del Cóndor Dorado", "Sebastián Lizarzaburu", ("Animación", "Aventura"), "APT"),
    ("Fuga a Medianoche", "Gonzalo Seminario", ("Acción", "Drama"), "PG-13"),
    ("Vacaciones en Enredos", "Patricia Rospigliosi", ("Comedia",), "APT"),
    ("La Casa de los Siete Candados", "Esteban Benavides", ("Terror", "Aventura"), "PG-18"),
    ("Estación Artemisa", "Rodrigo Alzamora", ("Ciencia Ficción", "Aventura"), "PG-13"),
    ("Cartas desde el Altiplano", "Jimena Chocano", ("Drama", "Romance"), "APT"),
    ("Aventura en el Arrecife", "Diego Garrido", ("Animación", "Comedia", "Aventura"), "APT"),
    ("Código Fantasma", "Álvaro Diez Canseco", ("Acción", "Ciencia Ficción"), "PG-13"),
    ("Un Vecino Imposible", "Claudia Berckemeyer", ("Comedia",), "APT"),
    ("El Ritual del Eclipse", "Martín Polar", ("Terror",), "PG-18"),
    ("Más Allá de las Dunas", "Adriana Tudela", ("Aventura", "Drama"), "PG-13"),
    ("Robotito y la Estrella Fugaz", "Nicolás Bentín", ("Animación", "Ciencia Ficción"), "APT"),
    ("Promesas de Invierno", "Renata Miró Quesada", ("Romance", "Drama"), "PG-13"),
    ("Impacto Vertical", "Jorge Luis Cáceres", ("Acción",), "PG-13"),
    ("La Banda del Barrio", "Paola Ferrand", ("Comedia", "Romance"), "APT"),
    ("El Huésped del Piso Trece", "César Augusto Ríos", ("Terror", "Drama"), "PG-18"),
    ("Viajeros del Reloj Solar", "Gabriel Wiese", ("Animación", "Aventura"), "APT"),
    ("Memoria Artificial", "Ximena de la Puente", ("Ciencia Ficción", "Drama"), "PG-13"),
    ("Caminos Cruzados", "Andrés Gallagher", ("Drama",), "PG-13"),
    ("Rescate en la Selva Alta", "Julio César Delgado", ("Acción", "Aventura"), "PG-13"),
    ("Boda por Accidente", "Lorena Fernandini", ("Comedia", "Romance"), "APT"),
    ("Los Ojos del Abismo", "Víctor Raúl Tapia", ("Terror", "Ciencia Ficción"), "PG-18"),
    ("El Reino de las Nubes", "Natalia Beingolea", ("Animación", "Comedia"), "APT"),
    ("Sin Retorno", "Mauricio Carrillo", ("Acción", "Drama"), "PG-18"),
    ("El Secreto del Abuelo", "Beatriz Lavalle", ("Comedia", "Drama"), "APT"),
    ("Órbita Lejana", "Arturo Zevallos", ("Ciencia Ficción",), "PG-13"),
    ("Noche de San Juan", "Verónica Cisneros", ("Romance", "Comedia"), "PG-13"),
    ("Patrulla Galáctica", "Joaquín Ugarte", ("Animación", "Acción", "Ciencia Ficción"), "APT"),
    ("Voces en el Sótano", "Hernán Bustamante", ("Terror",), "PG-18"),
    ("La Ruta de la Plata", "Enrique Pardo", ("Aventura", "Acción"), "PG-13"),
    ("Tres Hermanos y un Perro", "Carolina Mujica", ("Comedia",), "APT"),
    ("El Último Tren a Huancayo", "Raúl Porras", ("Drama", "Romance"), "PG-13"),
    ("Dinoaventuras en el Valle", "Mónica Blume", ("Animación", "Aventura", "Comedia"), "APT"),
    ("Protocolo Centinela", "Óscar Avilés", ("Acción", "Ciencia Ficción"), "PG-13"),
    ("El Hechizo de la Laguna", "Silvia Málaga", ("Terror", "Drama"), "PG-13"),
    ("Verano en Paracas", "Javier Prado", ("Romance", "Comedia"), "APT"),
    ("Cazadores de Tormentas", "Luis Alberto Sánchez", ("Acción", "Aventura"), "PG-13"),
    ("La Escuela de Magia Andina", "Inés Temple", ("Animación", "Aventura"), "APT"),
    ("Despertar en Marte", "Pedro Pablo Cornejo", ("Ciencia Ficción", "Aventura"), "PG-13"),
    ("Culpables de Nada", "Elena Kcomt", ("Comedia", "Acción"), "PG-13"),
    ("El Silencio de las Montañas", "Gustavo Mohme", ("Drama",), "PG-13"),
    (
        "El Tesoro del Pirata Pacífico",
        "Alfonso Grados",
        ("Animación", "Aventura", "Comedia"),
        "APT",
    ),
    ("Reflejos Nocturnos", "Cecilia Barraza", ("Terror", "Drama"), "PG-18"),
    ("Un Segundo Para Siempre", "Federico Salazar", ("Romance", "Drama"), "PG-13"),
    ("Asalto al Convoy", "Humberto Martínez", ("Acción",), "PG-18"),
)

SINOPSIS_PLANTILLAS = (
    "Un hallazgo inesperado obliga a los protagonistas a emprender una travesía decisiva.",
    "Cuando el pasado regresa, un grupo de desconocidos debe unir fuerzas para sobrevivir.",
    "Una carrera contra el tiempo pondrá a prueba la lealtad y el valor de toda la misión.",
    "En medio de un cambio inesperado, dos vidas opuestas descubren un propósito común.",
    "Un misterio oculto durante décadas sale a la luz y transforma a todo el pueblo.",
    "Una aventura llena de humor y coraje donde la amistad será la clave para volver a casa.",
)

APELLIDOS_PERUANOS = (
    "Quispe",
    "Flores",
    "Sánchez",
    "García",
    "Rodríguez",
    "Rojas",
    "Huamán",
    "Mamani",
    "Vásquez",
    "Ramos",
    "López",
    "Torres",
    "Pérez",
    "Díaz",
    "Chávez",
    "Mendoza",
    "Espinoza",
    "Castillo",
    "Gutiérrez",
    "Vargas",
    "Romero",
    "Castro",
    "Cruz",
    "Morales",
    "Paredes",
    "Salazar",
    "Aguilar",
    "Medina",
    "Rivera",
    "Suárez",
    "Delgado",
    "Vega",
    "Campos",
    "Reyes",
    "Herrera",
    "Cárdenas",
    "Valdivia",
    "Zevallos",
    "Farfán",
    "Carrillo",
)


def _limpiar_slug(texto: str) -> str:
    normalizado = unicodedata.normalize("NFKD", texto.lower())
    solo_ascii = "".join(c for c in normalizado if c.isalnum())
    return solo_ascii or "usuario"


def _hash_bcrypt_determinista(rng: np.random.Generator) -> str:
    indices = rng.integers(0, len(ALFABETO_BCRYPT), size=22)
    cuerpo_sal = "".join(ALFABETO_BCRYPT[int(i)] for i in indices)
    # En formato Modular Crypt de 22 chars, el último carácter debe tener los 2 bits bajos en 0 (.Oeu)
    ultimo = ".Oeu"[int(rng.integers(0, 4))]
    sal = f"$2b$10${cuerpo_sal[:21]}{ultimo}".encode("ascii")
    return bcrypt.hashpw(b"CineMax2026!", sal).decode("ascii")


def _generar_sedes_y_salas(
    semilla: EstadoSemilla, desde: date, hasta: date
) -> tuple[list[SedePlan], list[SalaPlan], list[ButacaPlan]]:
    mitad = desde + (hasta - desde) // 2
    sedes_nuevas = [
        SedePlan(
            id_venue=3,
            name_venue="CineMax Santiago de Surco",
            address="Av. Primavera 1540, Santiago de Surco",
            phone_number="(01) 555-0303",
            status="Activo",
            created_at=datetime.combine(desde - timedelta(days=90), time(9, 0)),
            id_district=4,
            latitude=-12.1095,
            longitude=-76.9715,
            es_nueva=True,
        ),
        SedePlan(
            id_venue=4,
            name_venue="CineMax Yanahuara",
            address="Av. Ejército 710, Yanahuara",
            phone_number="(054) 555-0404",
            status="Activo",
            created_at=datetime.combine(desde - timedelta(days=60), time(9, 0)),
            id_district=6,
            latitude=-16.3905,
            longitude=-71.5480,
            es_nueva=True,
        ),
        SedePlan(
            id_venue=5,
            name_venue="CineMax Wanchaq",
            address="Av. de la Cultura 1420, Wanchaq",
            phone_number="(084) 555-0505",
            status="Activo",
            created_at=datetime.combine(mitad, time(9, 0)),
            id_district=7,
            latitude=-13.5226,
            longitude=-71.9675,
            es_nueva=True,
        ),
    ]

    # (id_room, id_venue, nombre, filas, columnas, es_vip)
    espec_salas = [
        (7, 3, "Sala 1", 8, 10, False),
        (8, 3, "Sala 2", 6, 10, False),
        (9, 3, "Sala 3", 5, 10, False),
        (10, 3, "Sala 4 VIP", 4, 10, True),
        (11, 4, "Sala 1", 7, 10, False),
        (12, 4, "Sala 2", 6, 10, False),
        (13, 4, "Sala 3", 5, 8, False),
        (14, 5, "Sala 1", 7, 10, False),
        (15, 5, "Sala 2", 6, 10, False),
        (16, 5, "Sala 3 VIP", 4, 10, True),
    ]

    salas_nuevas: list[SalaPlan] = []
    butacas_nuevas: list[ButacaPlan] = []
    id_butaca = max(b.id_seat for b in semilla.butacas) + 1

    for id_room, id_venue, nombre, filas, cols, es_vip in espec_salas:
        capacidad = filas * cols
        salas_nuevas.append(
            SalaPlan(
                id_room=id_room,
                name_room=nombre,
                capacity=capacidad,
                num_rows=filas,
                seats_per_row=cols,
                status="Activo",
                id_venue=id_venue,
                es_vip=es_vip,
                es_nueva=True,
            )
        )
        for r in range(1, filas + 1):
            letra = chr(64 + r)
            es_ultima_fila = r == filas
            for c in range(1, cols + 1):
                # Al menos 2 butacas WHEELCHAIR en la última fila de cada sala nueva
                tipo = 2 if (es_ultima_fila and c > cols - 2) else 1
                butacas_nuevas.append(
                    ButacaPlan(
                        id_seat=id_butaca,
                        row_name=letra,
                        column_number=c,
                        status="ACTIVO",
                        id_seat_type=tipo,
                        id_room=id_room,
                        es_nueva=True,
                    )
                )
                id_butaca += 1

    return (
        semilla.sedes + sedes_nuevas,
        semilla.salas + salas_nuevas,
        semilla.butacas + butacas_nuevas,
    )


def _generar_confiteria(
    semilla: EstadoSemilla, sedes: list[SedePlan], desde: date, hasta: date
) -> tuple[list[ProductoPlan], list[StockSedePlan]]:
    dias_ventana = (hasta - desde).days
    fecha_cambio = desde + timedelta(days=dias_ventana // 2) if dias_ventana >= 90 else None
    creado_en = datetime.combine(desde - timedelta(days=90), time(10, 0))

    productos_nuevos: list[ProductoPlan] = []
    id_actual = max(p.id_snack for p in semilla.productos) + 1
    for cat, nombre, desc, p_ini, p_fin, stock in PRODUCTOS_NUEVOS:
        inicial = Decimal(p_ini)
        final = Decimal(p_fin)
        productos_nuevos.append(
            ProductoPlan(
                id_snack=id_actual,
                id_venue=1,
                id_snack_category=cat,
                name_snack=nombre,
                description_snack=desc,
                precio_inicial=inicial if fecha_cambio else final,
                price=final,
                fecha_cambio_precio=fecha_cambio if inicial != final else None,
                stock=stock,
                status="Activo",
                created_at=creado_en,
                es_nuevo=True,
            )
        )
        id_actual += 1

    todos_productos = semilla.productos + productos_nuevos
    stocks_nuevos: list[StockSedePlan] = []
    factores_sede = {1: 1.0, 2: 0.7, 3: 0.85, 4: 0.75, 5: 0.65}
    for prod in todos_productos:
        for sede in sedes:
            par = (prod.id_snack, sede.id_venue)
            if par not in semilla.stock_existente:
                factor = factores_sede.get(sede.id_venue, 0.8)
                stocks_nuevos.append(
                    StockSedePlan(
                        id_snack=prod.id_snack,
                        id_venue=sede.id_venue,
                        stock=max(10, int(prod.stock * factor)),
                        status="Activo",
                    )
                )
    return todos_productos, stocks_nuevos


def _primer_jueves(fecha: date) -> date:
    dias = (4 - fecha.isoweekday()) % 7
    return fecha + timedelta(days=dias)


def _generar_peliculas(
    semilla: EstadoSemilla,
    parametros: Parametros,
    desde: date,
    hasta: date,
    rng: np.random.Generator,
) -> list[PeliculaPlan]:
    total = min(parametros.total_peliculas_nuevas, len(CATALOGO_PELICULAS))
    inicio_estrenos = _primer_jueves(desde - timedelta(days=35))
    fin_estrenos = hasta + timedelta(days=14)

    jueves_disponibles: list[date] = []
    actual = inicio_estrenos
    while actual <= fin_estrenos:
        jueves_disponibles.append(actual)
        actual += timedelta(days=7)

    # Si la ventana es muy corta (p. ej. 2 semanas en test_reproducible), extendemos hacia atrás
    while len(jueves_disponibles) < 36:
        inicio_estrenos -= timedelta(days=7)
        jueves_disponibles.insert(0, inicio_estrenos)

    # Asignamos 1 o 2 estrenos por jueves para cubrir el total de películas
    fechas_estreno: list[date] = []
    idx_jueves = 0
    while len(fechas_estreno) < total:
        jueves = jueves_disponibles[idx_jueves % len(jueves_disponibles)]
        fechas_estreno.append(jueves)
        idx_jueves += 1
    fechas_estreno.sort()

    peliculas: list[PeliculaPlan] = []
    for i in range(total):
        titulo, director, nombres_generos, nombre_clasif = CATALOGO_PELICULAS[i]
        if titulo in semilla.titulos_peliculas_seed:
            titulo = f"{titulo} II"

        estreno = fechas_estreno[i]
        dias_antes = int(rng.integers(14, 43))
        hora_creacion = int(rng.integers(8, 20))
        minuto_creacion = int(rng.integers(0, 60))
        creada_dt = datetime.combine(
            estreno - timedelta(days=dias_antes),
            time(hora_creacion, minuto_creacion),
            tzinfo=UTC,
        )
        estreno_dt = datetime.combine(estreno, time(0, 0), tzinfo=UTC)

        oid = object_id_determinista(creada_dt, rng)
        duracion = int(rng.integers(17, 35)) * 5  # 85 a 170 minutos
        es_animacion = "Animación" in nombres_generos

        pop_bruta = float(rng.lognormal(parametros.popularidad_mu, parametros.popularidad_sigma))
        popularidad = float(np.clip(pop_bruta, 0.30, 4.00))

        # Las películas más populares duran más semanas en cartelera (de 3 a 8)
        if popularidad >= 1.6:
            semanas = int(rng.integers(6, 9))
        elif popularidad >= 0.9:
            semanas = int(rng.integers(4, 7))
        else:
            semanas = int(rng.integers(3, 6))

        if estreno > hasta:
            estado = "Preventa"
            activa = True
        elif (hasta - estreno).days < 7:
            estado = "Estreno"
            activa = True
        else:
            estado = "Cartelera"
            activa = (estreno + timedelta(weeks=semanas)) > hasta

        genre_ids = tuple(semilla.generos[g] for g in nombres_generos if g in semilla.generos)
        clasif_id = semilla.clasificaciones[nombre_clasif]
        sinopsis = SINOPSIS_PLANTILLAS[i % len(SINOPSIS_PLANTILLAS)]

        peliculas.append(
            PeliculaPlan(
                id=oid,
                title_movie=titulo,
                synopsis=sinopsis,
                duration_minutes=duracion,
                poster_url="",
                director=director,
                release_date=estreno_dt,
                status=estado,
                created_at=creada_dt,
                is_active=activa,
                premiere_week=False,
                genre_ids=genre_ids,
                classification_id=clasif_id,
                es_animacion=es_animacion,
                popularidad=popularidad,
                semanas_cartelera=semanas,
            )
        )
    return peliculas


def _generar_clientes(
    semilla: EstadoSemilla,
    parametros: Parametros,
    desde: date,
    hasta: date,
    semilla_int: int,
    rng: np.random.Generator,
) -> list[ClientePlan]:
    faker = Faker("es_ES")
    faker.seed_instance(semilla_int)

    nombres_pool = [faker.first_name() for _ in range(400)]
    apellidos_pool = list(APELLIDOS_PERUANOS) + [faker.last_name() for _ in range(160)]

    password_hash = _hash_bcrypt_determinista(rng)
    total = parametros.total_clientes
    id_inicial = semilla.max_id_user + 1

    id_dni = semilla.tipos_documento["DNI"]
    id_ce = semilla.tipos_documento["CE"]
    id_pas = semilla.tipos_documento["PASAPORTE"]

    dias_ventana = max(1, (hasta - desde).days)
    referencia_edad = date(2026, 12, 31)

    idx_nombres = rng.integers(0, len(nombres_pool), size=total)
    idx_ape1 = rng.integers(0, len(apellidos_pool), size=total)
    idx_ape2 = rng.integers(0, len(apellidos_pool), size=total)
    u_doc = rng.random(size=total)
    num_doc_base = rng.integers(10_000_000, 99_999_999, size=total)
    u_tel = rng.random(size=total)
    num_tel = rng.integers(10_000_000, 99_999_999, size=total)
    u_nac = rng.random(size=total)
    u_tramo_edad = rng.random(size=total)
    edad_joven = rng.integers(18, 41, size=total)
    edad_adolescente = rng.integers(12, 18, size=total)
    edad_mayor = rng.integers(41, 79, size=total)
    dia_del_anio = rng.integers(0, 365, size=total)
    u_alta = rng.random(size=total)
    dias_alta_previa = rng.integers(1, 180, size=total)
    dias_alta_ventana = rng.integers(0, dias_ventana + 1, size=total)

    # Mezcla de cola larga: 78 % clientes ocasionales y 22 % clientes frecuentes
    es_frecuente = rng.random(size=total) < 0.22
    pesos_ocasionales = rng.uniform(0.04, 0.18, size=total)
    pesos_frecuentes = np.clip(rng.lognormal(mean=1.4, sigma=1.05, size=total), 0.8, 60.0)
    pesos = np.where(es_frecuente, pesos_frecuentes, pesos_ocasionales)

    clientes: list[ClientePlan] = []
    for i in range(total):
        id_user = id_inicial + i
        nombre = nombres_pool[int(idx_nombres[i])]
        apellido = f"{apellidos_pool[int(idx_ape1[i])]} {apellidos_pool[int(idx_ape2[i])]}"

        slug_n = _limpiar_slug(nombre.split()[0])
        slug_a = _limpiar_slug(apellidos_pool[int(idx_ape1[i])])
        email = f"{slug_n}.{slug_a}.{id_user}@cinemax.test"

        if u_doc[i] < 0.92:
            id_doc_type = id_dni
            doc_num = f"{int(num_doc_base[i]):08d}"
        elif u_doc[i] < 0.97:
            id_doc_type = id_ce
            doc_num = f"0{int(num_doc_base[i]):08d}"
        else:
            id_doc_type = id_pas
            doc_num = f"PE{int(num_doc_base[i]) % 10_000_000:07d}"

        telefono = f"9{int(num_tel[i]):08d}" if u_tel[i] < 0.85 else None

        if u_nac[i] < 0.97:
            if u_tramo_edad[i] < 0.68:
                edad = int(edad_joven[i])
            elif u_tramo_edad[i] < 0.80:
                edad = int(edad_adolescente[i])
            else:
                edad = int(edad_mayor[i])
            anio_nac = referencia_edad.year - edad
            nacimiento = date(anio_nac, 1, 1) + timedelta(days=int(dia_del_anio[i]))
        else:
            nacimiento = None

        if u_alta[i] < 0.65:
            fecha_alta = desde - timedelta(days=int(dias_alta_previa[i]))
        else:
            fecha_alta = desde + timedelta(days=int(dias_alta_ventana[i]))

        clientes.append(
            ClientePlan(
                id_user=id_user,
                datebirth=nacimiento,
                document_number=doc_num,
                email=email,
                first_name=nombre,
                last_name=apellido,
                password=password_hash,
                phone=telefono,
                status="Activo",
                id_doc_type=id_doc_type,
                id_role=semilla.id_rol_cliente,
                fecha_alta=fecha_alta,
                peso=float(pesos[i]),
            )
        )
    return clientes


def generar_catalogo(
    semilla: EstadoSemilla,
    parametros: Parametros,
    desde: date,
    hasta: date,
    semilla_int: int,
    rng: np.random.Generator,
) -> CatalogoPlan:
    rng_peliculas, rng_clientes = rng.spawn(2)
    sedes, salas, butacas = _generar_sedes_y_salas(semilla, desde, hasta)
    productos, stocks_nuevos = _generar_confiteria(semilla, sedes, desde, hasta)
    peliculas = _generar_peliculas(semilla, parametros, desde, hasta, rng_peliculas)
    clientes = _generar_clientes(semilla, parametros, desde, hasta, semilla_int, rng_clientes)
    return CatalogoPlan(
        sedes=sedes,
        salas=salas,
        butacas=butacas,
        productos=productos,
        stocks_nuevos=stocks_nuevos,
        peliculas=peliculas,
        clientes=clientes,
        promociones=semilla.promociones,
        id_estado_completado=semilla.id_estado_completado,
    )
