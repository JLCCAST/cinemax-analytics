"""Copia las 5 bases de CineMax al esquema raw del warehouse (recarga completa)."""

# El historial de Flyway no es un dato del negocio y el stock queda fuera del alcance.
TABLAS_EXCLUIDAS = {"flyway_schema_history", "snack_venue_stock"}

# Minimización de datos: lo que el análisis no necesita no sale de la fuente.
COLUMNAS_EXCLUIDAS = {
    ("usuarios", "user_account"): {
        "password",
        "reset_password_token",
        "token_expiration_date",
        "first_name",
        "last_name",
        "email",
        "phone",
        "document_number",
        "image_url",
    },
    ("facturacion", "sale_transaction"): {"qr_code_data"},
    ("confiteria", "snack"): {"stock"},
}
