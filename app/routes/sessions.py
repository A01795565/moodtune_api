from flask import Blueprint, jsonify, request
from ..src.db import get_conn
from ..src.utils import (
    row_to_dict,
    validate_uuid_or_none,
    parse_iso_timestamp,
    clamp_pagination,
    normalize_email,
    email_sha256_hex,
    verify_password,
)
import uuid

bp = Blueprint("sessions", __name__)


@bp.post("/login")
def login():
    try:
        p = request.get_json(force=True) or {}
        email = normalize_email(p.get("email"))
        password = p.get("password")
        device_info = p.get("device_info")
        ip_hash = p.get("ip_hash")

        if not email or not isinstance(password, str) or password == "":
            return jsonify({"error": "Email y contraseña requeridos"}), 400

        with get_conn() as conn, conn.cursor() as cur:
            cur.execute(
                "SELECT user_id, password_salt, password_hash, failed_attempts, locked_until FROM user_credentials WHERE email = %s",
                (email,),
            )
            row = cur.fetchone()
            if not row:
                return jsonify({"error": "Credenciales inválidas"}), 401

            user_id, salt, pw_hash, failed_attempts, locked_until = row

            # Verificación de bloqueo
            if locked_until is not None:
                cur.execute("SELECT NOW() < %s", (locked_until,))
                is_locked = cur.fetchone()[0]
                if is_locked:
                    return jsonify({"error": "Cuenta bloqueada temporalmente"}), 423

            ok = verify_password(password, salt, pw_hash)
            if not ok:
                new_failed = int(failed_attempts or 0) + 1
                # Bloqueo tras 5 intentos fallidos por 15 minutos
                if new_failed >= 5:
                    cur.execute(
                        "UPDATE user_credentials SET failed_attempts = 0, locked_until = DATE_ADD(NOW(), INTERVAL 15 MINUTE) WHERE email = %s",
                        (email,),
                    )
                else:
                    cur.execute(
                        "UPDATE user_credentials SET failed_attempts = %s WHERE email = %s",
                        (new_failed, email),
                    )
                conn.commit()
                return jsonify({"error": "Credenciales inválidas"}), 401

            # Login exitoso: reset de contadores y last_login_at
            cur.execute(
                "UPDATE user_credentials SET failed_attempts = 0, locked_until = NULL, last_login_at = NOW() WHERE email = %s",
                (email,),
            )

            # Asegurar users.email_hash poblado
            cur.execute("SELECT email_hash, display_name FROM users WHERE user_id = %s", (user_id,))
            urow = cur.fetchone()
            display_name = None
            email_hash = None
            if urow:
                email_hash, display_name = urow
                if not email_hash:
                    email_hash = email_sha256_hex(email)
                    cur.execute("UPDATE users SET email_hash = %s WHERE user_id = %s", (email_hash, user_id))

            # Crear sesión
            session_id = str(uuid.uuid4())
            cur.execute(
                "INSERT INTO sessions (session_id, user_id, device_info, ip_hash) VALUES (%s, %s, %s, %s)",
                (session_id, user_id, device_info, ip_hash),
            )
            conn.commit()

        return jsonify({
            "session_id": session_id,
            "user": {
                "user_id": user_id,
                "display_name": display_name,
                "email_hash": email_hash,
            }
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@bp.post("")
def create():
    try:
        p = request.get_json(force=True) or {}
        session_id = p.get("session_id") or str(uuid.uuid4())
        session_id = validate_uuid_or_none(session_id, "session_id")
        user_id = validate_uuid_or_none(p.get("user_id"), "user_id")
        device_info = p.get("device_info")
        ip_hash = p.get("ip_hash")
        sql = "INSERT INTO sessions (session_id, user_id, device_info, ip_hash) VALUES (%s, %s, %s, %s)"
        with get_conn() as conn, conn.cursor() as cur:
            cur.execute(sql, (session_id, user_id, device_info, ip_hash))
            conn.commit()
        return jsonify({"session_id": session_id, "user_id": user_id, "device_info": device_info, "ip_hash": ip_hash}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@bp.get("")
def list_():
    try:
        limit, offset = clamp_pagination(request.args.get("limit"), request.args.get("offset"))
        cols = ["session_id", "user_id", "started_at", "ended_at", "device_info", "ip_hash"]
        sql = f"SELECT {', '.join(cols)} FROM sessions ORDER BY started_at DESC LIMIT %s OFFSET %s"
        with get_conn() as conn, conn.cursor() as cur:
            cur.execute(sql, (limit, offset))
            rows = cur.fetchall()
        return jsonify({"items": [row_to_dict(r, cols) for r in rows], "limit": limit, "offset": offset}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@bp.get("/<session_id>")
def get_one(session_id):
    try:
        session_id = validate_uuid_or_none(session_id, "session_id")
        cols = ["session_id", "user_id", "started_at", "ended_at", "device_info", "ip_hash"]
        with get_conn() as conn, conn.cursor() as cur:
            cur.execute(f"SELECT {', '.join(cols)} FROM sessions WHERE session_id = %s", (session_id,))
            row = cur.fetchone()
        if not row:
            return jsonify({"error": "Sesión no encontrada"}), 404
        return jsonify(row_to_dict(row, cols)), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@bp.patch("/<session_id>")
def update(session_id):
    try:
        session_id = validate_uuid_or_none(session_id, "session_id")
        p = request.get_json(force=True) or {}
        fields, values = [], []

        if "user_id" in p:
            fields.append("user_id = %s"); values.append(validate_uuid_or_none(p.get("user_id"), "user_id"))
        if p.get("end") is True:
            fields.append("ended_at = NOW()")
        elif "ended_at" in p:
            fields.append("ended_at = %s"); values.append(parse_iso_timestamp(p.get("ended_at")))
        if "device_info" in p:
            fields.append("device_info = %s"); values.append(p.get("device_info"))
        if "ip_hash" in p:
            fields.append("ip_hash = %s"); values.append(p.get("ip_hash"))

        if not fields:
            return jsonify({"error": "Nada para actualizar"}), 400

        sql = f"UPDATE sessions SET {', '.join(fields)} WHERE session_id = %s"
        values.append(session_id)
        with get_conn() as conn, conn.cursor() as cur:
            cur.execute(sql, tuple(values))
            conn.commit()
            if cur.rowcount == 0:
                return jsonify({"error": "Sesión no encontrada"}), 404
        return jsonify({"updated": True, "session_id": session_id}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@bp.delete("/<session_id>")
def delete(session_id):
    try:
        session_id = validate_uuid_or_none(session_id, "session_id")
        with get_conn() as conn, conn.cursor() as cur:
            cur.execute("DELETE FROM sessions WHERE session_id = %s", (session_id,))
            conn.commit()
            if cur.rowcount == 0:
                return jsonify({"error": "Sesión no encontrada"}), 404
        return jsonify({"deleted": True, "session_id": session_id}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400

