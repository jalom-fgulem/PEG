from pathlib import Path
import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    APP_NAME = "SGPEG - Sistema de Gestión de Propuestas Específicas de Gasto"
    DEBUG = os.getenv("DEBUG", "true").lower() == "true"
    BASE_DIR = Path(__file__).resolve().parent.parent
    TEMPLATES_DIR = BASE_DIR / "templates"
    STATIC_DIR = BASE_DIR / "static"

    # Conexión SQL Server — configurar en .env
    # Ejemplo .env:
    #   DB_SERVER=192.168.1.100
    #   DB_NAME=SGPEG
    #   DB_USER=sgpeg_user
    #   DB_PASSWORD=tu_password
    #   DB_DRIVER=ODBC Driver 17 for SQL Server
    # Clave secreta para firmar cookies de sesión — cambiar en producción
    SECRET_KEY: str = os.getenv("SECRET_KEY", "dev-secret-key-cambiar-en-produccion")

    # SMTP — configurar en .env para habilitar notificaciones por correo
    SMTP_HOST: str     = os.getenv("SMTP_HOST", "")
    SMTP_PORT: int     = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER: str     = os.getenv("SMTP_USER", "")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
    SMTP_FROM: str     = os.getenv("SMTP_FROM", "")
    BASE_URL: str      = os.getenv("BASE_URL", "http://localhost:8000")

    DB_SERVER: str = os.getenv("DB_SERVER", "localhost")
    DB_NAME: str = os.getenv("DB_NAME", "SGPEG")
    DB_USER: str = os.getenv("DB_USER", "")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "")
    DB_DRIVER: str = os.getenv("DB_DRIVER", "ODBC Driver 17 for SQL Server")

    @property
    def DATABASE_URL(self) -> str:
        if self.DB_USER and self.DB_PASSWORD:
            return (
                f"DRIVER={{{self.DB_DRIVER}}};"
                f"SERVER={self.DB_SERVER};"
                f"DATABASE={self.DB_NAME};"
                f"UID={self.DB_USER};"
                f"PWD={self.DB_PASSWORD};"
                "TrustServerCertificate=yes;"
            )
        else:
            return (
                f"DRIVER={{{self.DB_DRIVER}}};"
                f"SERVER={self.DB_SERVER};"
                f"DATABASE={self.DB_NAME};"
                "Trusted_Connection=yes;"
                "TrustServerCertificate=yes;"
            )


settings = Settings()
