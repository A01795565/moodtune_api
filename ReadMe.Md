MoodTune API (Flask + MySQL)

Backend modular y escalable desarrollado en Flask (Python) con conexión a MySQL. Actúa como núcleo relacional dentro de la arquitectura de MoodTune (RDBMS + servicios externos) y expone endpoints CRUD y utilitarios.

Características
- Arquitectura modular basada en Blueprints.
- Endpoints CRUD para: `users`, `sessions`, `inferences`, `playlists`, `mood_map_rules`, `audit_logs`, `oauth_tokens`, `user-credentials`.
- Conexión a MySQL mediante pool y validaciones (UUID, fechas, tipos).
- Respuestas JSON consistentes y manejo centralizado de errores.
- CORS configurable y preparado para Docker.

Estructura (resumen)
- `app/__init__.py` App factory, CORS, health y registro de blueprints.
- `app/src/{config,db,utils}.py` Configuración, pool MySQL y utilidades.
- `app/routes/*.py` Blueprints por recurso.
- `db/*.sql` Scripts de creación de DB y esquema.
- `docs/openapi/moodtune.yaml` Especificación del API + colecciones Postman.

OpenAPI y Postman
- OpenAPI: `moodtune_api/docs/openapi/moodtune.yaml`
- Postman: `moodtune_api/docs/openapi/MoodTune_API.postman_collection.json`
- Entorno: `moodtune_api/docs/openapi/MoodTune_Local.postman_environment.json`

Requisitos (venv)
```
python -m venv .venv
# Linux/Mac: source .venv/bin/activate
# Windows:   .venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
python run.py
```
Health: `curl http://127.0.0.1:8000/health`

Docker Compose
1) Copia `.env.example` a `.env` y ajusta valores.
2) `docker compose up --build`
3) API: `http://localhost:8000`

Comandos útiles
```
# Reconstruir solo la API tras cambios
docker compose up -d --build api

# Logs
docker compose logs -f db
docker compose logs -f api

# Detener
docker compose down
```

Acceso a MySQL
```
# Desde el host
mysql -h 127.0.0.1 -P 3310 -u moodTuneTest -p

# Dentro del contenedor de la API (host=db, puerto interno 3306)
docker exec -it moodtune_api bash
mysql -h db -P 3306 -u moodTuneTest -p
```

Notas
- No comprometas credenciales reales; usa `.env.example` como referencia.
- Ajusta CORS con `CORS_ORIGINS` según tu entorno.

