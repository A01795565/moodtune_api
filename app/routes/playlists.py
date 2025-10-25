from flask import Blueprint, jsonify, request
from ..src.db import get_conn
from ..src.utils import row_to_dict, validate_uuid_or_none, clamp_pagination
import uuid

bp = Blueprint("playlists", __name__)

@bp.post("")
def create():
    try:
        p = request.get_json(force=True) or {}
        playlist_id = p.get("playlist_id") or str(uuid.uuid4())
        playlist_id = validate_uuid_or_none(playlist_id, "playlist_id")
        user_id = validate_uuid_or_none(p.get("user_id"), "user_id")
        if not user_id:
            return jsonify({"error": "user_id es requerido"}), 400

        provider = p.get("provider", "spotify")
        if provider not in ("spotify", "apple_music", "amazon_music"):
            return jsonify({"error": "provider inválido"}), 400

        external_id = p.get("external_playlist_id")
        deep_link_url = p.get("deep_link_url")
        title = p.get("title")
        description = p.get("description")

        sql = """
        INSERT INTO playlists (playlist_id, user_id, provider, external_playlist_id, deep_link_url, title, description)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        vals = (playlist_id, user_id, provider, external_id, deep_link_url, title, description)
        with get_conn() as conn, conn.cursor() as cur:
            cur.execute(sql, vals)
            conn.commit()

        return jsonify({"playlist_id": playlist_id, "user_id": user_id, "provider": provider}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@bp.get("")
def list_():
    try:
        limit, offset = clamp_pagination(request.args.get("limit"), request.args.get("offset"))
        user_id = request.args.get("user_id")
        cols = ["playlist_id", "user_id", "provider", "external_playlist_id", "deep_link_url", "title", "description", "created_at"]
        base = f"SELECT {', '.join(cols)} FROM playlists"
        params = []
        if user_id:
            user_id = validate_uuid_or_none(user_id, "user_id")
            base += " WHERE user_id = %s"
            params.append(user_id)
        base += " ORDER BY created_at DESC LIMIT %s OFFSET %s"
        params.extend([limit, offset])

        with get_conn() as conn, conn.cursor() as cur:
            cur.execute(base, tuple(params))
            rows = cur.fetchall()
        return jsonify({"items": [row_to_dict(r, cols) for r in rows], "limit": limit, "offset": offset}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@bp.get("/<playlist_id>")
def get_one(playlist_id):
    try:
        playlist_id = validate_uuid_or_none(playlist_id, "playlist_id")
        cols = ["playlist_id", "user_id", "provider", "external_playlist_id", "deep_link_url", "title", "description", "created_at"]
        with get_conn() as conn, conn.cursor() as cur:
            cur.execute(f"SELECT {', '.join(cols)} FROM playlists WHERE playlist_id = %s", (playlist_id,))
            row = cur.fetchone()
        if not row:
            return jsonify({"error": "Playlist no encontrada"}), 404
        return jsonify(row_to_dict(row, cols)), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@bp.patch("/<playlist_id>")
def update(playlist_id):
    try:
        playlist_id = validate_uuid_or_none(playlist_id, "playlist_id")
        p = request.get_json(force=True) or {}
        fields, values = [], []

        if "provider" in p:
            if p["provider"] not in ("spotify", "apple_music", "amazon_music"):
                return jsonify({"error": "provider inválido"}), 400
            fields.append("provider = %s"); values.append(p["provider"])
        if "external_playlist_id" in p:
            fields.append("external_playlist_id = %s"); values.append(p["external_playlist_id"])
        if "deep_link_url" in p:
            fields.append("deep_link_url = %s"); values.append(p["deep_link_url"])
        if "title" in p:
            fields.append("title = %s"); values.append(p["title"])
        if "description" in p:
            fields.append("description = %s"); values.append(p["description"])

        if not fields:
            return jsonify({"error": "Nada para actualizar"}), 400

        sql = f"UPDATE playlists SET {', '.join(fields)} WHERE playlist_id = %s"
        values.append(playlist_id)
        with get_conn() as conn, conn.cursor() as cur:
            cur.execute(sql, tuple(values))
            conn.commit()
            if cur.rowcount == 0:
                return jsonify({"error": "Playlist no encontrada"}), 404
        return jsonify({"updated": True, "playlist_id": playlist_id}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@bp.delete("/<playlist_id>")
def delete(playlist_id):
    try:
        playlist_id = validate_uuid_or_none(playlist_id, "playlist_id")
        with get_conn() as conn, conn.cursor() as cur:
            cur.execute("DELETE FROM playlists WHERE playlist_id = %s", (playlist_id,))
            conn.commit()
            if cur.rowcount == 0:
                return jsonify({"error": "Playlist no encontrada"}), 404
        return jsonify({"deleted": True, "playlist_id": playlist_id}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400
