import os
import tempfile

# Una base de datos temporal para toda la corrida de pruebas (antes de importar los módulos).
os.environ["DB_PATH"] = os.path.join(tempfile.mkdtemp(), "test.db")
