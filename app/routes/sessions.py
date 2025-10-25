from flask import Blueprint, jsonify, request
from ..src.db import get_conn
from ..src.utils import row_to_dict, validate_uuid_or_none, parse_iso_timestamp, clamp_pagination
import uuid

bp = Blueprint("sessions", __name__)

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
