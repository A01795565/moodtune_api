from flask import Blueprint, jsonify, request, current_app
from ..src.db import get_conn
from ..src.utils import row_to_dict, clamp_pagination

bp = Blueprint("audit_logs", __name__)

@bp.post("")
def create():
    try:
        p = request.get_json(force=True) or {}
        cols = ["actor_type", "actor_id", "action", "entity_type", "entity_id", "payload_json"]
        vals = [p.get("actor_type"), p.get("actor_id"), p.get("action"), p.get("entity_type"), p.get("entity_id"), p.get("payload_json")]
        sql = f"INSERT INTO audit_logs ({', '.join(cols)}) VALUES (%s, %s, %s, %s, %s, CAST(%s AS JSON))"
        with get_conn() as conn, conn.cursor() as cur:
            cur.execute(sql, tuple(vals))
            conn.commit()
        return jsonify({"created": True}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@bp.get("")
def list_():
    try:
        limit, offset = clamp_pagination(request.args.get("limit"), request.args.get("offset"))
        cols = ["audit_id", "actor_type", "actor_id", "action", "entity_type", "entity_id", "payload_json", "created_at"]
        sql = f"SELECT {', '.join(cols)} FROM audit_logs ORDER BY created_at DESC LIMIT %s OFFSET %s"
        with get_conn() as conn, conn.cursor() as cur:
            cur.execute(sql, (limit, offset))
            rows = cur.fetchall()
        return jsonify({"items": [row_to_dict(r, cols) for r in rows], "limit": limit, "offset": offset}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@bp.get("/<int:audit_id>")
def get_one(audit_id: int):
    try:
        cols = ["audit_id", "actor_type", "actor_id", "action", "entity_type", "entity_id", "payload_json", "created_at"]
        with get_conn() as conn, conn.cursor() as cur:
            cur.execute(f"SELECT {', '.join(cols)} FROM audit_logs WHERE audit_id = %s", (audit_id,))
            row = cur.fetchone()
        if not row:
            return jsonify({"error": "Registro no encontrado"}), 404
        return jsonify(row_to_dict(row, cols)), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@bp.patch("/<int:audit_id>")
def update(audit_id: int):
    try:
        p = request.get_json(force=True) or {}
        fields, values = [], []
        for k in ("actor_type","actor_id","action","entity_type","entity_id"):
            if k in p:
                fields.append(f"{k} = %s"); values.append(p[k])
        if "payload_json" in p:
            fields.append("payload_json = CAST(%s AS JSON)"); values.append(p["payload_json"])

        if not fields:
            return jsonify({"error": "Nada para actualizar"}), 400

        sql = f"UPDATE audit_logs SET {', '.join(fields)} WHERE audit_id = %s"
        values.append(audit_id)
        with get_conn() as conn, conn.cursor() as cur:
            cur.execute(sql, tuple(values))
            conn.commit()
            if cur.rowcount == 0:
                return jsonify({"error": "Registro no encontrado"}), 404
        return jsonify({"updated": True, "audit_id": audit_id}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@bp.delete("/<int:audit_id>")
def delete(audit_id: int):
    try:
        if not current_app.config.get("ALLOW_AUDIT_DELETE", False):
            return jsonify({"error": "Borrado deshabilitado para audit logs"}), 405
        with get_conn() as conn, conn.cursor() as cur:
            cur.execute("DELETE FROM audit_logs WHERE audit_id = %s", (audit_id,))
            conn.commit()
            if cur.rowcount == 0:
                return jsonify({"error": "Registro no encontrado"}), 404
        return jsonify({"deleted": True, "audit_id": audit_id}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400
