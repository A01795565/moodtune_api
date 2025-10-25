# MoodTune Project

**MoodTune API** es un servicio backend modular y escalable desarrollado en **Flask (Python)** con conexión a **MySQL**.  
Su propósito es actuar como núcleo relacional dentro de una arquitectura híbrida (RDBMS + BaaS/objeto) para el sistema **MoodTune**, que combina Inteligencia Artificial y música en streaming para generar experiencias personalizadas según el estado emocional del usuario.

---

## Características principales

- Arquitectura **modular basada en Blueprints**.
- Endpoints **CRUD completos** para los módulos:
  - `users`
  - `sessions`
  - `inferences`
  - `playlists`
  - `mood_map_rules`
  - `audit_logs`
  - `oauth_tokens`
- Conexión a **MySQL mediante pool de conexiones**.
- **Validaciones de UUID**, formato de fecha y tipos de datos.
- **Respuestas JSON** estandarizadas y manejo de errores.
- Preparado para despliegue en **entornos de desarrollo o producción**.
- **Cumple principios de seguridad** (deny-by-default, cifrado, trazabilidad).

---

## Estructura del proyecto
```
.
moodtune/
├─ moodtune_api/
│  ├─ __init__.py           # app factory y registro de blueprints
│  ├─ src/
│  │  ├─ config.py             # config central (DB, pool, flags)
│  │  ├─ db.py                 # pool MySQL y helpers de conexión
│  │  └─ utils.py              # validación UUID, parsing fechas, helpers
│  └─ routes/
│     ├─ users.py
│     ├─ sessions.py
│     ├─ inferences.py
│     ├─ playlists.py
│     ├─ mood_map_rules.py
│     ├─ audit_logs.py
│     └─ oauth_tokens.py
├─ run.py                   # punto de entrada
└─ requirements.txt
```

## Requisitos
```bash
python -m venv .venv 

# Linux/Mac:
# source .venv/bin/activate  

# Windows: 
.venv\Scripts\activate

# Actualizar pip
python.exe -m pip install --upgrade pip

# Instalar librerias desde requirements.txt
pip install -r requirements.txt

# En caso de reinstalar las libreria
# pip install --upgrade --force-reinstall -r requirements.txt
# (opcional) conda: conda env create -f environment.yml
```

## Primeros pasos
```bash
cd project

python run.py
```

### Correr Contenedor Docker
```bash
# Construir e iniciar servicios
docker compose up --build

# (opcional en segundo plano)
# docker compose up --build -d

# Espera a que el servicio 'db' esté healthy (compose lo hace)
# La API arrancará automáticamente después

# Health API
curl http://127.0.0.1:8000/health

# Reconstruir sólo la API tras cambios
docker compose up -d --build api

# Logs
docker compose logs -f db
docker compose logs -f api

# Detener Docker
docker compose down
```