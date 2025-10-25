from flask import Blueprint, jsonify, request
from ..src.db import get_conn
from ..src.utils import row_to_dict, clamp_pagination
import uuid
import json

bp = Blueprint("mood_map_rules", __name__)

def _validate_payload(p):
    if p.get("emotion") not in ("joy", "sadness", "anger"):
        return "emotion inválido"
    if p.get("intention") not in ("maintain", "change"):
        return "intention inválido"
    if "params_json" not in p:
        return "params_json requerido (objeto con energy/valence/tempo/genres)"
    return None

@bp.post("")
def create():
    try:
        p = request.get_json(force=True) or {}
        err = _validate_payload(p)
        if err: return jsonify({"error": err}), 400
        rule_id = p.get("rule_id") or str(uuid.uuid4())
        version = int(p.get("version") or 1)
        is_active = 1 if p.get("is_active", True) else 0
        valid_from = p.get("valid_from")  # opcional (str "YYYY-MM-DD HH:MM:SS")
        valid_to = p.get("valid_to")      # opcional
        params_json = json.dumps(p["params_json"])

        sql = """
        INSERT INTO mood_map_rules (rule_id, emotion, intention, version, params_json, is_active, valid_from, valid_to)
        VALUES (%s, %s, %s, %s, CAST(%s AS JSON), %s, %s, %s)
        """
        vals = (rule_id, p["emotion"], p["intention"], version, params_json, is_active, valid_from, valid_to)
        with get_conn() as conn, conn.cursor() as cur:
            cur.execute(sql, vals)
            conn.commit()
        return jsonify({"rule_id": rule_id}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@bp.get("")
def list_():
    try:
        limit, offset = clamp_pagination(request.args.get("limit"), request.args.get("offset"))
        emotion = request.args.get("emotion")
        intention = request.args.get("intention")
        where, params = [], []

        if emotion:
            where.append("emotion = %s"); params.append(emotion)
        if intention:
            where.append("intention = %s"); params.append(intention)

        cols = ["rule_id", "emotion", "intention", "version", "params_json", "is_active", "valid_from", "valid_to", "created_at"]
        base = f"SELECT {', '.join(cols)} FROM mood_map_rules"
        if where:
            base += " WHERE " + " AND ".join(where)
        base += " ORDER BY created_at DESC LIMIT %s OFFSET %s"
        params.extend([limit, offset])

        with get_conn() as conn, conn.cursor() as cur:
            cur.execute(base, tuple(params))
            rows = cur.fetchall()

        items = []
        for r in rows:
            d = row_to_dict(r, cols)
            # params_json sale como str o dict según driver; normalizamos:
            try:
                d["params_json"] = json.loads(d["params_json"]) if isinstance(d["params_json"], str) else d["params_json"]
            except Exception:
                pass
            items.append(d)
        return jsonify({"items": items, "limit": limit, "offset": offset}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@bp.get("/<rule_id>")
def get_one(rule_id):
    try:
        cols = ["rule_id", "emotion", "intention", "version", "params_json", "is_active", "valid_from", "valid_to", "created_at"]
        with get_conn() as conn, conn.cursor() as cur:
            cur.execute(f"SELECT {', '.join(cols)} FROM mood_map_rules WHERE rule_id = %s", (rule_id,))
            row = cur.fetchone()
        if not row:
            return jsonify({"error": "Regla no encontrada"}), 404
        d = row_to_dict(row, cols)
        try:
            import json
            d["params_json"] = json.loads(d["params_json"]) if isinstance(d["params_json"], str) else d["params_json"]
        except Exception:
            pass
        return jsonify(d), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@bp.patch("/<rule_id>")
def update(rule_id):
    try:
        p = request.get_json(force=True) or {}
        fields, values = [], []
        if "emotion" in p:
            if p["emotion"] not in ("joy", "sadness", "anger"):
                return jsonify({"error": "emotion inválido"}), 400
            fields.append("emotion = %s"); values.append(p["emotion"])
        if "intention" in p:
            if p["intention"] not in ("maintain", "change"):
                return jsonify({"error": "intention inválido"}), 400
            fields.append("intention = %s"); values.append(p["intention"])
        if "version" in p:
            fields.append("version = %s"); values.append(int(p["version"]))
        if "params_json" in p:
            import json
            fields.append("params_json = CAST(%s AS JSON)"); values.append(json.dumps(p["params_json"]))
        if "is_active" in p:
            fields.append("is_active = %s"); values.append(1 if p["is_active"] else 0)
        if "valid_from" in p:
            fields.append("valid_from = %s"); values.append(p["valid_from"])
        if "valid_to" in p:
            fields.append("valid_to = %s"); values.append(p["valid_to"])

        if not fields:
            return jsonify({"error": "Nada para actualizar"}), 400

        sql = f"UPDATE mood_map_rules SET {', '.join(fields)} WHERE rule_id = %s"
        values.append(rule_id)
        with get_conn() as conn, conn.cursor() as cur:
            cur.execute(sql, tuple(values))
            conn.commit()
            if cur.rowcount == 0:
                return jsonify({"error": "Regla no encontrada"}), 404
        return jsonify({"updated": True, "rule_id": rule_id}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@bp.delete("/<rule_id>")
def delete(rule_id):
    try:
        with get_conn() as conn, conn.cursor() as cur:
            cur.execute("DELETE FROM mood_map_rules WHERE rule_id = %s", (rule_id,))
            conn.commit()
            if cur.rowcount == 0:
                return jsonify({"error": "Regla no encontrada"}), 404
        return jsonify({"deleted": True, "rule_id": rule_id}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400
