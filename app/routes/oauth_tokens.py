from flask import Blueprint, jsonify, request
from ..src.db import get_conn
from ..src.utils import row_to_dict, validate_uuid_or_none, clamp_pagination
import uuid

bp = Blueprint("oauth_tokens", __name__)

@bp.post("")
def create_or_replace():
    try:
        p = request.get_json(force=True) or {}
        token_id = p.get("token_id") or str(uuid.uuid4())
        token_id = validate_uuid_or_none(token_id, "token_id")
        user_id = validate_uuid_or_none(p.get("user_id"), "user_id")
        provider = p.get("provider", "spotify")
        if provider not in ("spotify","apple_music","amazon_music"):
            return jsonify({"error": "provider inválido"}), 400

        # ciphertexts PREVIA y necesariamente cifrados por tu app (AES-GCM/KMS)
        access_cipher = p.get("access_cipher_b64")
        refresh_cipher = p.get("refresh_cipher_b64")
        expires_at = p.get("expires_at")  # "YYYY-MM-DD HH:MM:SS" o ISO

        # UPSERT por (user_id, provider)
        sql = """
        INSERT INTO oauth_tokens (token_id, user_id, provider, access_cipher, refresh_cipher, expires_at)
        VALUES (%s, %s, %s, FROM_BASE64(%s), FROM_BASE64(%s), %s)
        ON DUPLICATE KEY UPDATE
          access_cipher = VALUES(access_cipher),
          refresh_cipher = VALUES(refresh_cipher),
          expires_at = VALUES(expires_at),
          updated_at = CURRENT_TIMESTAMP
        """
        vals = (token_id, user_id, provider, access_cipher, refresh_cipher, expires_at)
        with get_conn() as conn, conn.cursor() as cur:
            cur.execute(sql, vals)
            conn.commit()
        return jsonify({"token_id": token_id, "user_id": user_id, "provider": provider}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@bp.get("")
def list_():
    try:
        limit, offset = clamp_pagination(request.args.get("limit"), request.args.get("offset"))
        user_id = request.args.get("user_id")
        provider = request.args.get("provider")
        where, params = [], []

        if user_id:
            user_id = validate_uuid_or_none(user_id, "user_id")
            where.append("user_id = %s"); params.append(user_id)
        if provider:
            where.append("provider = %s"); params.append(provider)

        cols = ["token_id", "user_id", "provider", "expires_at", "created_at", "updated_at"]
        base = f"SELECT {', '.join(cols)} FROM oauth_tokens"
        if where:
            base += " WHERE " + " AND ".join(where)
        base += " ORDER BY updated_at DESC LIMIT %s OFFSET %s"
        params.extend([limit, offset])

        with get_conn() as conn, conn.cursor() as cur:
            cur.execute(base, tuple(params))
            rows = cur.fetchall()
        return jsonify({"items": [row_to_dict(r, cols) for r in rows], "limit": limit, "offset": offset}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@bp.get("/<token_id>")
def get_one(token_id):
    try:
        token_id = validate_uuid_or_none(token_id, "token_id")
        cols = ["token_id", "user_id", "provider", "expires_at", "created_at", "updated_at"]
        with get_conn() as conn, conn.cursor() as cur:
            cur.execute(f"SELECT {', '.join(cols)} FROM oauth_tokens WHERE token_id = %s", (token_id,))
            row = cur.fetchone()
        if not row:
            return jsonify({"error": "Token no encontrado"}), 404
        return jsonify(row_to_dict(row, cols)), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@bp.patch("/<token_id>")
def update(token_id):
    try:
        token_id = validate_uuid_or_none(token_id, "token_id")
        p = request.get_json(force=True) or {}
        fields, values = [], []

        if "provider" in p:
            if p["provider"] not in ("spotify","apple_music","amazon_music"):
                return jsonify({"error": "provider inválido"}), 400
            fields.append("provider = %s"); values.append(p["provider"])
        if "access_cipher_b64" in p:
            fields.append("access_cipher = FROM_BASE64(%s)"); values.append(p["access_cipher_b64"])
        if "refresh_cipher_b64" in p:
            fields.append("refresh_cipher = FROM_BASE64(%s)"); values.append(p["refresh_cipher_b64"])
        if "expires_at" in p:
            fields.append("expires_at = %s"); values.append(p["expires_at"])

        if not fields:
            return jsonify({"error": "Nada para actualizar"}), 400

        sql = f"UPDATE oauth_tokens SET {', '.join(fields)}, updated_at = CURRENT_TIMESTAMP WHERE token_id = %s"
        values.append(token_id)
        with get_conn() as conn, conn.cursor() as cur:
            cur.execute(sql, tuple(values))
            conn.commit()
            if cur.rowcount == 0:
                return jsonify({"error": "Token no encontrado"}), 404
        return jsonify({"updated": True, "token_id": token_id}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@bp.delete("/<token_id>")
def delete(token_id):
    try:
        token_id = validate_uuid_or_none(token_id, "token_id")
        with get_conn() as conn, conn.cursor() as cur:
            cur.execute("DELETE FROM oauth_tokens WHERE token_id = %s", (token_id,))
            conn.commit()
            if cur.rowcount == 0:
                return jsonify({"error": "Token no encontrado"}), 404
        return jsonify({"deleted": True, "token_id": token_id}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400