USE moodtune;

-- USERS
CREATE TABLE IF NOT EXISTS users (
  user_id           CHAR(36)       NOT NULL,
  email_hash        CHAR(64)       NULL,
  display_name      VARCHAR(120)   NULL,
  created_at        TIMESTAMP      NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at        TIMESTAMP      NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (user_id),
  UNIQUE KEY ux_users_email_hash (email_hash)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- USER CREDENTIALS (local email/password auth)
CREATE TABLE IF NOT EXISTS user_credentials (
  credential_id     CHAR(36)        NOT NULL,
  user_id           CHAR(36)        NOT NULL,
  email             VARCHAR(255)    NOT NULL,
  password_salt     VARBINARY(64)   NOT NULL,
  password_hash     VARBINARY(128)  NOT NULL,
  failed_attempts   INT             NOT NULL DEFAULT 0,
  locked_until      TIMESTAMP       NULL,
  last_login_at     TIMESTAMP       NULL,
  created_at        TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at        TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (credential_id),
  UNIQUE KEY ux_credentials_email (email),
  UNIQUE KEY ux_credentials_user (user_id),
  CONSTRAINT fk_credentials_user
    FOREIGN KEY (user_id) REFERENCES users(user_id)
    ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- SESSIONS
CREATE TABLE IF NOT EXISTS sessions (
  session_id        CHAR(36)       NOT NULL,
  user_id           CHAR(36)       NULL,
  started_at        TIMESTAMP      NOT NULL DEFAULT CURRENT_TIMESTAMP,
  ended_at          TIMESTAMP      NULL,
  device_info       VARCHAR(200)   NULL,
  ip_hash           CHAR(64)       NULL,
  PRIMARY KEY (session_id),
  KEY ix_sessions_user (user_id),
  CONSTRAINT fk_sessions_user
    FOREIGN KEY (user_id) REFERENCES users(user_id)
    ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- INFERENCES
CREATE TABLE IF NOT EXISTS inferences (
  inference_id      CHAR(36)       NOT NULL,
  session_id        CHAR(36)       NOT NULL,
  emotion           ENUM('joy','sadness','anger') NOT NULL,
  confidence        DECIMAL(5,4)   NOT NULL,
  intention         ENUM('maintain','change') NULL,
  latency_ms        INT            NULL,
  model_version     VARCHAR(50)    NULL,
  created_at        TIMESTAMP      NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (inference_id),
  KEY ix_inf_session_time (session_id, created_at),
  CONSTRAINT fk_inf_session
    FOREIGN KEY (session_id) REFERENCES sessions(session_id)
    ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- PLAYLISTS
CREATE TABLE IF NOT EXISTS playlists (
  playlist_id             CHAR(36)     NOT NULL,
  user_id                 CHAR(36)     NOT NULL,
  provider                ENUM('spotify','apple_music','amazon_music') NOT NULL DEFAULT 'spotify',
  external_playlist_id    VARCHAR(128) NOT NULL,
  deep_link_url           VARCHAR(500) NOT NULL,
  title                   VARCHAR(200) NULL,
  description             VARCHAR(500) NULL,
  created_at              TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (playlist_id),
  UNIQUE KEY ux_user_provider_external (user_id, provider, external_playlist_id),
  KEY ix_playlists_user (user_id),
  CONSTRAINT fk_playlists_user
    FOREIGN KEY (user_id) REFERENCES users(user_id)
    ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- MOOD MAP RULES
CREATE TABLE IF NOT EXISTS mood_map_rules (
  rule_id          CHAR(36)      NOT NULL,
  emotion          ENUM('joy','sadness','anger') NOT NULL,
  intention        ENUM('maintain','change') NOT NULL,
  version          INT            NOT NULL DEFAULT 1,
  params_json      JSON           NOT NULL,
  is_active        TINYINT(1)     NOT NULL DEFAULT 1,
  valid_from       TIMESTAMP      NOT NULL DEFAULT CURRENT_TIMESTAMP,
  valid_to         TIMESTAMP      NULL,
  created_at       TIMESTAMP      NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (rule_id),
  KEY ix_rule_active (emotion, intention, is_active, version)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- AUDIT LOGS
CREATE TABLE IF NOT EXISTS audit_logs (
  audit_id        BIGINT         NOT NULL AUTO_INCREMENT,
  actor_type      ENUM('system','user') NOT NULL,
  actor_id        CHAR(36)       NULL,
  action          VARCHAR(80)    NOT NULL,
  entity_type     VARCHAR(80)    NULL,
  entity_id       VARCHAR(64)    NULL,
  payload_json    JSON           NULL,
  created_at      TIMESTAMP      NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (audit_id),
  KEY ix_audit_time (created_at),
  KEY ix_audit_actor (actor_type, actor_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- OAUTH TOKENS
CREATE TABLE IF NOT EXISTS oauth_tokens (
  token_id        CHAR(36)        NOT NULL,
  user_id         CHAR(36)        NOT NULL,
  provider        ENUM('spotify','apple_music','amazon_music') NOT NULL DEFAULT 'spotify',
  access_cipher   VARBINARY(1024) NOT NULL,
  refresh_cipher  VARBINARY(1024) NULL,
  expires_at      TIMESTAMP       NULL,
  created_at      TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at      TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (token_id),
  UNIQUE KEY ux_oauth_user_provider (user_id, provider),
  CONSTRAINT fk_oauth_user
    FOREIGN KEY (user_id) REFERENCES users(user_id)
    ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
