from flask import Blueprint, jsonify, request
from ..src.db import get_conn
from ..src.utils import row_to_dict, validate_uuid_or_none, clamp_pagination
import uuid
import base64
from datetime import datetime
import requests

bp = Blueprint("oauth_tokens", __name__)

# Music service base URL for token refresh
MUSIC_SERVICE_URL = "http://localhost:8020"

@bp.post("")
def create_or_replace():
    try:
        p = request.get_json(force=True) or {}

        # Debug logging
        print("=" * 80)
        print("POST /oauth-tokens - Received payload:")
        print(f"  Raw JSON keys: {list(p.keys())}")
        print(f"  user_id: {p.get('user_id')} (type: {type(p.get('user_id'))})")
        print(f"  provider: {p.get('provider')} (type: {type(p.get('provider'))})")
        print(f"  token_id: {p.get('token_id')}")
        print(f"  expires_at: {p.get('expires_at')} (type: {type(p.get('expires_at'))})")
        print(f"  has access_cipher_b64: {bool(p.get('access_cipher_b64'))}")
        print(f"  has refresh_cipher_b64: {bool(p.get('refresh_cipher_b64'))}")
        if p.get('access_cipher_b64'):
            print(f"  access_cipher_b64 length: {len(p.get('access_cipher_b64'))}")
        if p.get('refresh_cipher_b64'):
            print(f"  refresh_cipher_b64 length: {len(p.get('refresh_cipher_b64'))}")
        print("=" * 80)

        token_id = p.get("token_id") or str(uuid.uuid4())
        print(f"DEBUG: Validating token_id: {token_id}")
        token_id = validate_uuid_or_none(token_id, "token_id")
        print(f"DEBUG: token_id validated: {token_id}")

        print(f"DEBUG: Validating user_id: {p.get('user_id')}")
        user_id = validate_uuid_or_none(p.get("user_id"), "user_id")
        print(f"DEBUG: user_id validated: {user_id}")

        provider = p.get("provider", "spotify")
        print(f"DEBUG: Provider: {provider}")
        if provider not in ("spotify","apple_music","amazon_music"):
            print(f"ERROR: Invalid provider: {provider}")
            return jsonify({"error": "provider inválido"}), 400

        # ciphertexts PREVIA y necesariamente cifrados por tu app (AES-GCM/KMS)
        access_cipher = p.get("access_cipher_b64")
        refresh_cipher = p.get("refresh_cipher_b64")
        expires_at = p.get("expires_at")  # "YYYY-MM-DD HH:MM:SS" o ISO

        print(f"DEBUG: access_cipher present: {bool(access_cipher)}")
        print(f"DEBUG: refresh_cipher present: {bool(refresh_cipher)}")
        print(f"DEBUG: expires_at: {expires_at}")

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
        print(f"DEBUG: Executing SQL with values: {vals}")
        with get_conn() as conn, conn.cursor() as cur:
            cur.execute(sql, vals)
            conn.commit()
        print(f"SUCCESS: Token upserted successfully: {token_id}")
        return jsonify({"token_id": token_id, "user_id": user_id, "provider": provider}), 201
    except Exception as e:
        print(f"ERROR in POST /oauth-tokens: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
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


@bp.get("/valid/<user_id>/<provider>")
def get_valid_token(user_id, provider):
    """
    Obtiene un token válido para el usuario, refrescándolo automáticamente si está expirado.

    Este endpoint:
    1. Busca el token del usuario en la BD
    2. Descifra el token (actualmente base64, en producción usar KMS)
    3. Verifica si está expirado
    4. Si está expirado, lo refresca usando el refresh_token
    5. Actualiza la BD con el nuevo token
    6. Devuelve el access_token válido
    """
    try:
        user_id = validate_uuid_or_none(user_id, "user_id")
        if provider not in ("spotify", "apple_music", "amazon_music"):
            return jsonify({"error": "provider inválido"}), 400

        # Buscar token en BD
        with get_conn() as conn, conn.cursor() as cur:
            cur.execute("""
                SELECT token_id, user_id, provider,
                       TO_BASE64(access_cipher) as access_b64,
                       TO_BASE64(refresh_cipher) as refresh_b64,
                       expires_at
                FROM oauth_tokens
                WHERE user_id = %s AND provider = %s
            """, (user_id, provider))
            row = cur.fetchone()

        if not row:
            return jsonify({"error": "Token no encontrado. Conecta tu cuenta primero."}), 404

        token_id, user_id, provider, access_b64, refresh_b64, expires_at = row

        # Descifrar tokens (actualmente base64, en producción usar KMS/AES-GCM)
        access_token = base64.b64decode(access_b64).decode('utf-8') if access_b64 else None
        refresh_token = base64.b64decode(refresh_b64).decode('utf-8') if refresh_b64 else None

        if not access_token:
            return jsonify({"error": "Token corrupto en la BD"}), 500

        # Verificar si está expirado (buffer de 5 minutos)
        is_expired = False
        if expires_at:
            now = datetime.utcnow()
            # Agregar buffer de 5 minutos
            if (expires_at - now).total_seconds() < 300:
                is_expired = True

        # Si está expirado, refrescar
        if is_expired and refresh_token:
            if provider == "spotify":
                try:
                    # Llamar al music service para refrescar
                    refresh_resp = requests.post(
                        f"{MUSIC_SERVICE_URL}/auth/spotify/refresh",
                        json={"refresh_token": refresh_token},
                        timeout=10
                    )
                    refresh_resp.raise_for_status()
                    token_data = refresh_resp.json()

                    # Extraer nuevos tokens
                    new_access = token_data.get("access_token")
                    new_refresh = token_data.get("refresh_token") or refresh_token
                    expires_in = token_data.get("expires_in", 3600)

                    # Actualizar en BD
                    from datetime import timedelta
                    new_expires = datetime.utcnow() + timedelta(seconds=expires_in)

                    with get_conn() as conn, conn.cursor() as cur:
                        cur.execute("""
                            UPDATE oauth_tokens
                            SET access_cipher = FROM_BASE64(%s),
                                refresh_cipher = FROM_BASE64(%s),
                                expires_at = %s,
                                updated_at = CURRENT_TIMESTAMP
                            WHERE token_id = %s
                        """, (
                            base64.b64encode(new_access.encode()).decode(),
                            base64.b64encode(new_refresh.encode()).decode(),
                            new_expires,
                            token_id
                        ))
                        conn.commit()

                    # Usar nuevo token
                    access_token = new_access

                except requests.RequestException as e:
                    return jsonify({
                        "error": "No se pudo refrescar el token",
                        "detail": str(e),
                        "suggestion": "Por favor reconecta tu cuenta"
                    }), 502
            else:
                return jsonify({"error": f"Refresh no implementado para {provider}"}), 501

        # Devolver token válido
        return jsonify({
            "provider": provider,
            "access_token": access_token,
            "expires_at": expires_at.isoformat() if expires_at else None,
            "was_refreshed": is_expired
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500