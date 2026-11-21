import os

# Las pruebas usan PostgreSQL (el servicio no soporta otra base de datos).
# Define TEST_DATABASE_URL, p. ej. postgresql://ecoconecta:clave@localhost:5432/ecoconecta_test
# (¡las pruebas borran las tablas de esa base!).
_u = os.environ.get("TEST_DATABASE_URL")
if not _u:
    raise RuntimeError("Define TEST_DATABASE_URL apuntando a una base PostgreSQL de pruebas.")
os.environ["DATABASE_URL"] = _u
os.environ.pop("BACKEND_URL", None)
os.environ.pop("PILOTO_NUMEROS", None)
for _v in ("ANTHROPIC_API_KEY", "STT_API_KEY", "STT_URL", "STT_MODEL"):
    os.environ.pop(_v, None)  # pruebas deterministas: sin IA ni transcripción reales
