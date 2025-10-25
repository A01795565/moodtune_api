import uuid
from datetime import datetime
from typing import Any, Dict, List

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
