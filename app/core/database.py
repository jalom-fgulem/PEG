import pyodbc
from contextlib import contextmanager
from app.core.config import settings


def get_connection():
    """
    Devuelve una conexión activa a SQL Server.
    Usar preferiblemente con get_db() como context manager.
    """
    conn = pyodbc.connect(settings.DATABASE_URL, timeout=10)
    conn.setdecoding(pyodbc.SQL_CHAR, encoding="utf-8")
    conn.setdecoding(pyodbc.SQL_WCHAR, encoding="utf-8")
    conn.setencoding(encoding="utf-8")
    return conn


@contextmanager
def get_db():
    """
    Context manager para gestión automática de conexión y transacción.

    Uso:
        with get_db() as db:
            rows = db.execute("SELECT ...").fetchall()

    Hace commit automático al salir sin error.
    Hace rollback automático si hay excepción.
    Cierra siempre la conexión.
    """
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def fetchall_as_dicts(cursor) -> list[dict]:
    """Convierte filas de cursor a lista de diccionarios."""
    columns = [col[0] for col in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


def fetchone_as_dict(cursor) -> dict | None:
    """Convierte una fila de cursor a diccionario, o None si no hay resultado."""
    columns = [col[0] for col in cursor.description]
    row = cursor.fetchone()
    if row is None:
        return None
    return dict(zip(columns, row))