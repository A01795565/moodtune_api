from flask import Blueprint, jsonify, request
from ..src.db import get_conn
from ..src.utils import (
    row_to_dict,
    validate_uuid_or_none,
    clamp_pagination,
    parse_iso_timestamp,
    normalize_email,
    hash_password,
)
import uuid

bp = Blueprint("user_credentials", __name__)


@bp.post("")
def create():
    try:
        p = request.get_json(force=True) or {}
        credential_id = p.get("credential_id") or str(uuid.uuid4())
        credential_id = validate_uuid_or_none(credential_id, "credential_id")
        user_id = validate_uuid_or_none(p.get("user_id"), "user_id")
        email = normalize_email(p.get("email"))
        password = p.get("password")

        if not user_id:
            return jsonify({"error": "user_id requerido"}), 400
        if not email:
            return jsonify({"error": "email requerido"}), 400
        if not isinstance(password, str) or password == "":
            return jsonify({"error": "password requerido"}), 400

        salt, pw_hash = hash_password(password)

        sql = (
            "INSERT INTO user_credentials (credential_id, user_id, email, password_salt, password_hash) "
            "VALUES (%s, %s, %s, %s, %s)"
        )
        with get_conn() as conn, conn.cursor() as cur:
            cur.execute(sql, (credential_id, user_id, email, salt, pw_hash))
            conn.commit()

        return jsonify({
            "credential_id": credential_id,
            "user_id": user_id,
            "email": email,
        }), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@bp.get("")
def list_():
    try:
        limit, offset = clamp_pagination(request.args.get("limit"), request.args.get("offset"))
        q_user = validate_uuid_or_none(request.args.get("user_id"), "user_id")
        q_email = normalize_email(request.args.get("email"))

        cols = [
            "credential_id",
            "user_id",
            "email",
            "failed_attempts",
            "locked_until",
            "last_login_at",
            "created_at",
            "updated_at",
        ]
        where = []
        params = []
        if q_user:
            where.append("user_id = %s"); params.append(q_user)
        if q_email:
            where.append("email = %s"); params.append(q_email)
        where_sql = (" WHERE " + " AND ".join(where)) if where else ""

        sql = f"SELECT {', '.join(cols)} FROM user_credentials{where_sql} ORDER BY created_at DESC LIMIT %s OFFSET %s"
        params.extend([limit, offset])

        with get_conn() as conn, conn.cursor() as cur:
            cur.execute(sql, tuple(params))
            rows = cur.fetchall()

        return jsonify({"items": [row_to_dict(r, cols) for r in rows], "limit": limit, "offset": offset}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@bp.get("/<credential_id>")
def get_one(credential_id):
    try:
        credential_id = validate_uuid_or_none(credential_id, "credential_id")
        cols = [
            "credential_id",
            "user_id",
            "email",
            "failed_attempts",
            "locked_until",
            "last_login_at",
            "created_at",
            "updated_at",
        ]
        with get_conn() as conn, conn.cursor() as cur:
            cur.execute(f"SELECT {', '.join(cols)} FROM user_credentials WHERE credential_id = %s", (credential_id,))
            row = cur.fetchone()
        if not row:
            return jsonify({"error": "Credencial no encontrada"}), 404
        return jsonify(row_to_dict(row, cols)), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@bp.patch("/<credential_id>")
def update(credential_id):
    try:
        credential_id = validate_uuid_or_none(credential_id, "credential_id")
        p = request.get_json(force=True) or {}
        fields, values = [], []

        if "email" in p:
            new_email = normalize_email(p.get("email"))
            fields.append("email = %s"); values.append(new_email)

        if "new_password" in p and p.get("new_password"):
            salt, pw_hash = hash_password(p.get("new_password"))
            fields.append("password_salt = %s"); values.append(salt)
            fields.append("password_hash = %s"); values.append(pw_hash)

        if p.get("reset_lock") is True:
            fields.append("failed_attempts = 0")
            fields.append("locked_until = NULL")
        elif "locked_until" in p:
            fields.append("locked_until = %s"); values.append(parse_iso_timestamp(p.get("locked_until")))

        if not fields:
            return jsonify({"error": "Nada para actualizar"}), 400

        sql = f"UPDATE user_credentials SET {', '.join(fields)} WHERE credential_id = %s"
        values.append(credential_id)
        with get_conn() as conn, conn.cursor() as cur:
            cur.execute(sql, tuple(values))
            conn.commit()
            if cur.rowcount == 0:
                return jsonify({"error": "Credencial no encontrada"}), 404
        return jsonify({"updated": True, "credential_id": credential_id}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@bp.delete("/<credential_id>")
def delete(credential_id):
    try:
        credential_id = validate_uuid_or_none(credential_id, "credential_id")
        with get_conn() as conn, conn.cursor() as cur:
            cur.execute("DELETE FROM user_credentials WHERE credential_id = %s", (credential_id,))
            conn.commit()
            if cur.rowcount == 0:
                return jsonify({"error": "Credencial no encontrada"}), 404
        return jsonify({"deleted": True, "credential_id": credential_id}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400

