import os
from dotenv import load_dotenv

class Config:
    # DB
    load_dotenv()
    DB_HOST = os.getenv("DB_HOST")
    DB_PORT = int(os.getenv("DB_PORT"))
    DB_USER = os.getenv("DB_USER")
    DB_PASSWORD = os.getenv("DB_PASSWORD")
    DB_NAME = os.getenv("DB_NAME")
    DB_CHARSET = "utf8mb4"
    DB_COLLATION = "utf8mb4_0900_ai_ci"
    DB_POOL_NAME = os.getenv("DB_POOL_NAME", "moodtune_pool")
    DB_POOL_SIZE = int(os.getenv("DB_POOL_SIZE", "5"))

    DEBUG = os.getenv("DEBUG", "true").lower() == "true"
    # CORS
    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*")

    # Bandera para impedir borrar logs de auditoría en producción
    ALLOW_AUDIT_DELETE = os.getenv("ALLOW_AUDIT_DELETE", "false").lower() == "true"
