import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Tuple
import os
import hashlib
import hmac


def validate_uuid_or_none(value, field_name: str):
    if value is None:
        return None
    try:
        return str(uuid.UUID(str(value)))
    except Exception:
        raise ValueError(f"'{field_name}' debe ser un UUID válido")


def parse_iso_timestamp(value):
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value)
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).replace(tzinfo=None)
    except Exception:
        try:
            return datetime.strptime(str(value), "%Y-%m-%d %H:%M:%S")
        except Exception:
            raise ValueError("Formato de fecha/hora inválido")


def clamp_pagination(limit, offset, max_limit=100):
    limit = int(limit) if str(limit).isdigit() else 20
    offset = int(offset) if str(offset).isdigit() else 0
    return max(1, min(limit, max_limit)), max(0, offset)


def row_to_dict(row: tuple, cols: List[str]) -> Dict[str, Any]:
    return {col: row[i] for i, col in enumerate(cols)}


def normalize_email(email: str) -> str:
    if email is None:
        return None
    return str(email).strip().lower()


def email_sha256_hex(email: str) -> str:
    e = normalize_email(email)
    if not e:
        return None
    return hashlib.sha256(e.encode('utf-8')).hexdigest()


def hash_password(password: str, salt: bytes = None, iterations: int = 200_000) -> Tuple[bytes, bytes]:
    if not isinstance(password, str) or password == "":
        raise ValueError("Contraseña inválida")
    if salt is None:
        salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, iterations)
    return salt, dk


def _to_bytes(x: Any) -> bytes:
    if x is None:
        return b""
    if isinstance(x, (bytes, bytearray)):
        return bytes(x)
    if isinstance(x, memoryview):
        return x.tobytes()
    if isinstance(x, str):
        return x.encode('utf-8')
    try:
        return bytes(x)
    except Exception:
        return b""


def verify_password(password: str, salt: bytes, expected_hash: bytes, iterations: int = 200_000) -> bool:
    """Verifica contraseña con PBKDF2-HMAC-SHA256.

    Normaliza `salt` y `expected_hash` a bytes para evitar falsos negativos
    por diferencias de tipo (bytearray/memoryview) al comparar.
    """
    try:
        salt_b = _to_bytes(salt)
        expected_b = _to_bytes(expected_hash)
        _, dk = hash_password(password, salt=salt_b, iterations=iterations)
        return hmac.compare_digest(dk, expected_b)
    except Exception:
        return False

