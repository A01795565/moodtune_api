from flask import Blueprint, jsonify, request
from ..src.db import get_conn
from ..src.utils import row_to_dict, validate_uuid_or_none, clamp_pagination

bp = Blueprint("users", __name__)

@bp.post("")
def create():
    try:
        payload = request.get_json(force=True) or {}
        user_id = validate_uuid_or_none(payload.get("user_id"), "user_id")
        email_hash = payload.get("email_hash")
        display_name = payload.get("display_name")

        if not user_id:
            import uuid
            user_id = str(uuid.uuid4())

        sql = "INSERT INTO users (user_id, email_hash, display_name) VALUES (%s, %s, %s)"
        with get_conn() as conn, conn.cursor() as cur:
            cur.execute(sql, (user_id, email_hash, display_name))
            conn.commit()
        return jsonify({"user_id": user_id, "email_hash": email_hash, "display_name": display_name}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@bp.get("")
def list_():
    try:
        limit, offset = clamp_pagination(request.args.get("limit"), request.args.get("offset"))
        cols = ["user_id", "email_hash", "display_name", "created_at", "updated_at"]
        sql = f"SELECT {', '.join(cols)} FROM users ORDER BY created_at DESC LIMIT %s OFFSET %s"
        with get_conn() as conn, conn.cursor() as cur:
            cur.execute(sql, (limit, offset))
            rows = cur.fetchall()
        return jsonify({"items": [row_to_dict(r, cols) for r in rows], "limit": limit, "offset": offset}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@bp.get("/<user_id>")
def get_one(user_id):
    try:
        user_id = validate_uuid_or_none(user_id, "user_id")
        cols = ["user_id", "email_hash", "display_name", "created_at", "updated_at"]
        with get_conn() as conn, conn.cursor() as cur:
            cur.execute(f"SELECT {', '.join(cols)} FROM users WHERE user_id = %s", (user_id,))
            row = cur.fetchone()
        if not row:
            return jsonify({"error": "Usuario no encontrado"}), 404
        return jsonify(row_to_dict(row, cols)), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@bp.patch("/<user_id>")
def update(user_id):
    try:
        user_id = validate_uuid_or_none(user_id, "user_id")
        payload = request.get_json(force=True) or {}
        fields, values = [], []

        if "email_hash" in payload:
            fields.append("email_hash = %s"); values.append(payload.get("email_hash"))
        if "display_name" in payload:
            fields.append("display_name = %s"); values.append(payload.get("display_name"))

        if not fields:
            return jsonify({"error": "Nada para actualizar"}), 400

        sql = f"UPDATE users SET {', '.join(fields)} WHERE user_id = %s"
        values.append(user_id)
        with get_conn() as conn, conn.cursor() as cur:
            cur.execute(sql, tuple(values))
            conn.commit()
            if cur.rowcount == 0:
                return jsonify({"error": "Usuario no encontrado"}), 404
        return jsonify({"updated": True, "user_id": user_id}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@bp.delete("/<user_id>")
def delete(user_id):
    try:
        user_id = validate_uuid_or_none(user_id, "user_id")
        with get_conn() as conn, conn.cursor() as cur:
            cur.execute("DELETE FROM users WHERE user_id = %s", (user_id,))
            conn.commit()
            if cur.rowcount == 0:
                return jsonify({"error": "Usuario no encontrado"}), 404
        return jsonify({"deleted": True, "user_id": user_id}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400