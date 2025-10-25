from mysql.connector import pooling, Error
from .config import Config

_pool = None

def init_db_pool():
    global _pool
    if _pool is None:
        _pool = pooling.MySQLConnectionPool(
            pool_name=Config.DB_POOL_NAME,
            pool_size=Config.DB_POOL_SIZE,
            pool_reset_session=True,
            host=Config.DB_HOST,
            port=Config.DB_PORT,
            user=Config.DB_USER,
            password=Config.DB_PASSWORD,
            database=Config.DB_NAME,
            charset=Config.DB_CHARSET,
            collation=Config.DB_COLLATION,
        )
    return _pool

def get_conn():
    if _pool is None:
        init_db_pool()
    return _pool.get_connection()

def ping():
    try:
        with get_conn() as conn, conn.cursor() as cur:
            cur.execute("SELECT 1")
            cur.fetchone()
        return True, None
    except Error as e:
        return False, str(e)
