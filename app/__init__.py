from flask import Flask, jsonify
try:
    from flask_cors import CORS
except Exception:
    CORS = None
from .src.config import Config
from .src.db import init_db_pool, ping
from .routes.users import bp as users_bp
from .routes.sessions import bp as sessions_bp
from .routes.inferences import bp as inferences_bp
from .routes.playlists import bp as playlists_bp
from .routes.mood_map_rules import bp as mood_map_rules_bp
from .routes.audit_logs import bp as audit_logs_bp
from .routes.oauth_tokens import bp as oauth_tokens_bp
from .routes.user_credentials import bp as user_credentials_bp

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Habilitar CORS si está disponible
    if CORS:
        origins = Config.CORS_ORIGINS if hasattr(Config, 'CORS_ORIGINS') else '*'
        CORS(app, resources={r"/*": {"origins": origins}}, supports_credentials=True)

    # Init DB pool
    init_db_pool()

    # Health endpoint
    @app.get("/health")
    def health():
        ok, detail = ping()
        code = 200 if ok else 500
        return jsonify({"status": "ok" if ok else "error", "detail": detail}), code

    # Register blueprints
    app.register_blueprint(users_bp, url_prefix="/users")
    app.register_blueprint(sessions_bp, url_prefix="/sessions")
    app.register_blueprint(inferences_bp, url_prefix="/inferences")
    app.register_blueprint(playlists_bp, url_prefix="/playlists")
    app.register_blueprint(mood_map_rules_bp, url_prefix="/mood-map-rules")
    app.register_blueprint(audit_logs_bp, url_prefix="/audit-logs")
    app.register_blueprint(oauth_tokens_bp, url_prefix="/oauth-tokens")
    app.register_blueprint(user_credentials_bp, url_prefix="/user-credentials")

    return app
