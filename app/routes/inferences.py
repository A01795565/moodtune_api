from flask import Blueprint, jsonify, request
from ..src.db import get_conn
from ..src.utils import row_to_dict, validate_uuid_or_none, clamp_pagination
import uuid

bp = Blueprint("inferences", __name__)

@bp.post("")
def create():
    try:
        p = request.get_json(force=True) or {}
        inference_id = p.get("inference_id") or str(uuid.uuid4())
        inference_id = validate_uuid_or_none(inference_id, "inference_id")
        session_id = validate_uuid_or_none(p.get("session_id"), "session_id")
        if not session_id:
            return jsonify({"error": "session_id es requerido"}), 400

        emotion = p.get("emotion")
        if emotion not in ("joy", "sadness", "anger"):
            return jsonify({"error": "emotion inválido"}), 400
        confidence = p.get("confidence")
        intention = p.get("intention") if p.get("intention") in (None, "maintain", "change") else None
        latency_ms = p.get("latency_ms")
        model_version = p.get("model_version")

        sql = """
        INSERT INTO inferences (inference_id, session_id, emotion, confidence, intention, latency_ms, model_version)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        vals = (inference_id, session_id, emotion, confidence, intention, latency_ms, model_version)
        with get_conn() as conn, conn.cursor() as cur:
            cur.execute(sql, vals)
            conn.commit()

        return jsonify({"inference_id": inference_id, "session_id": session_id, "emotion": emotion}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@bp.get("")
def list_():
    try:
        limit, offset = clamp_pagination(request.args.get("limit"), request.args.get("offset"))
        session_id = request.args.get("session_id")
        cols = ["inference_id", "session_id", "emotion", "confidence", "intention", "latency_ms", "model_version", "created_at"]
        base = f"SELECT {', '.join(cols)} FROM inferences"
        params = []
        if session_id:
            session_id = validate_uuid_or_none(session_id, "session_id")
            base += " WHERE session_id = %s"
            params.append(session_id)
        base += " ORDER BY created_at DESC LIMIT %s OFFSET %s"
        params.extend([limit, offset])

        with get_conn() as conn, conn.cursor() as cur:
            cur.execute(base, tuple(params))
            rows = cur.fetchall()
        return jsonify({"items": [row_to_dict(r, cols) for r in rows], "limit": limit, "offset": offset}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@bp.get("/<inference_id>")
def get_one(inference_id):
    try:
        inference_id = validate_uuid_or_none(inference_id, "inference_id")
        cols = ["inference_id", "session_id", "emotion", "confidence", "intention", "latency_ms", "model_version", "created_at"]
        with get_conn() as conn, conn.cursor() as cur:
            cur.execute(f"SELECT {', '.join(cols)} FROM inferences WHERE inference_id = %s", (inference_id,))
            row = cur.fetchone()
        if not row:
            return jsonify({"error": "Inferencia no encontrada"}), 404
        return jsonify(row_to_dict(row, cols)), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@bp.patch("/<inference_id>")
def update(inference_id):
    try:
        inference_id = validate_uuid_or_none(inference_id, "inference_id")
        p = request.get_json(force=True) or {}
        fields, values = [], []

        if "emotion" in p:
            if p["emotion"] not in ("joy", "sadness", "anger"):
                return jsonify({"error": "emotion inválido"}), 400
            fields.append("emotion = %s"); values.append(p["emotion"])
        if "confidence" in p:
            fields.append("confidence = %s"); values.append(p["confidence"])
        if "intention" in p:
            if p["intention"] not in (None, "maintain", "change"):
                return jsonify({"error": "intention inválido"}), 400
            fields.append("intention = %s"); values.append(p["intention"])
        if "latency_ms" in p:
            fields.append("latency_ms = %s"); values.append(p["latency_ms"])
        if "model_version" in p:
            fields.append("model_version = %s"); values.append(p["model_version"])

        if not fields:
            return jsonify({"error": "Nada para actualizar"}), 400

        sql = f"UPDATE inferences SET {', '.join(fields)} WHERE inference_id = %s"
        values.append(inference_id)
        with get_conn() as conn, conn.cursor() as cur:
            cur.execute(sql, tuple(values))
            conn.commit()
            if cur.rowcount == 0:
                return jsonify({"error": "Inferencia no encontrada"}), 404
        return jsonify({"updated": True, "inference_id": inference_id}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@bp.delete("/<inference_id>")
def delete(inference_id):
    try:
        inference_id = validate_uuid_or_none(inference_id, "inference_id")
        with get_conn() as conn, conn.cursor() as cur:
            cur.execute("DELETE FROM inferences WHERE inference_id = %s", (inference_id,))
            conn.commit()
            if cur.rowcount == 0:
                return jsonify({"error": "Inferencia no encontrada"}), 404
        return jsonify({"deleted": True, "inference_id": inference_id}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400
