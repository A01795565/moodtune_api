-- Crea base de datos (si no existe) con UTF8MB4
CREATE DATABASE IF NOT EXISTS moodtune
  DEFAULT CHARACTER SET utf8mb4
  DEFAULT COLLATE utf8mb4_0900_ai_ci;

-- Crea usuario de aplicación (no root) y permisos
CREATE USER IF NOT EXISTS 'moodTuneTest'@'%' IDENTIFIED BY 'StrongPassword123!';
GRANT ALL PRIVILEGES ON moodtune.* TO 'moodTuneTest'@'%';
FLUSH PRIVILEGES;
