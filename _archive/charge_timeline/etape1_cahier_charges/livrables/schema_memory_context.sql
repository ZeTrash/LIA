-- Schéma SQL logique pour la mémoire locale (SQLite 3.x)
PRAGMA foreign_keys = ON;

CREATE TABLE traits (
  trait_id TEXT PRIMARY KEY,
  type TEXT NOT NULL CHECK (type IN ('persona','skill','style','constraint')),
  label TEXT NOT NULL,
  value TEXT NOT NULL,
  version INTEGER NOT NULL CHECK (version > 0),
  weight REAL NOT NULL CHECK (weight BETWEEN 0 AND 1),
  confidence REAL NOT NULL CHECK (confidence BETWEEN 0 AND 1),
  origin TEXT,
  status TEXT NOT NULL CHECK (status IN ('active','staged','deprecated')),
  last_update TEXT NOT NULL,
  checksum TEXT GENERATED ALWAYS AS (lower(hex(sha3_256(value)))) STORED
);

CREATE TABLE trait_versions (
  trait_id TEXT NOT NULL,
  version INTEGER NOT NULL,
  delta JSON NOT NULL,
  changed_at TEXT NOT NULL,
  changed_by TEXT,
  PRIMARY KEY (trait_id, version),
  FOREIGN KEY (trait_id) REFERENCES traits(trait_id) ON DELETE CASCADE
);

CREATE TABLE souvenirs (
  memory_id TEXT PRIMARY KEY,
  category TEXT NOT NULL CHECK (category IN ('fact','preference','alert')),
  content TEXT NOT NULL,
  tags TEXT,
  importance_score REAL NOT NULL CHECK (importance_score BETWEEN 0 AND 1),
  recency_score REAL NOT NULL CHECK (recency_score BETWEEN 0 AND 1),
  emotion_score REAL NOT NULL CHECK (emotion_score BETWEEN -1 AND 1),
  frequency INTEGER NOT NULL DEFAULT 1,
  ttl TEXT NOT NULL,
  source TEXT,
  hash TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE souvenir_links (
  memory_id TEXT NOT NULL,
  target_type TEXT NOT NULL CHECK (target_type IN ('trait','experience','interaction')),
  target_id TEXT NOT NULL,
  PRIMARY KEY (memory_id, target_type, target_id),
  FOREIGN KEY (memory_id) REFERENCES souvenirs(memory_id) ON DELETE CASCADE
);

CREATE TABLE interaction_logs (
  interaction_id TEXT PRIMARY KEY,
  session_id TEXT NOT NULL,
  occurred_at TEXT NOT NULL,
  prompt TEXT NOT NULL,
  response TEXT NOT NULL,
  scores JSON,
  derived_traits JSON,
  anomalies JSON,
  severity TEXT NOT NULL DEFAULT 'info' CHECK (severity IN ('info','warning','error')),
  raw_size_bytes INTEGER
) WITHOUT ROWID;

CREATE TABLE experiences (
  experience_id TEXT PRIMARY KEY,
  title TEXT,
  period JSON,
  outcome TEXT,
  metrics_snapshot JSON,
  related_memories JSON
);

CREATE TABLE session_goals (
  goal_id TEXT PRIMARY KEY,
  session_id TEXT NOT NULL,
  priority REAL NOT NULL CHECK (priority BETWEEN 0 AND 1),
  description TEXT NOT NULL,
  blocking_conditions JSON,
  expires_at TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active','snoozed','done'))
);

CREATE TABLE indicators (
  indicator_id TEXT PRIMARY KEY,
  type TEXT NOT NULL,
  value REAL NOT NULL,
  window TEXT NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('ok','warn','alert')),
  thresholds JSON,
  history JSON
);

CREATE TABLE governance_params (
  param_id TEXT PRIMARY KEY,
  scope TEXT NOT NULL,
  value TEXT NOT NULL,
  default_value TEXT NOT NULL,
  min_value TEXT,
  max_value TEXT,
  updated_at TEXT NOT NULL,
  updated_by TEXT,
  metadata JSON
);

CREATE TABLE request_audit (
  audit_id TEXT PRIMARY KEY,
  endpoint TEXT NOT NULL,
  actor TEXT NOT NULL,
  session_id TEXT,
  context_version TEXT,
  status_code INTEGER NOT NULL,
  duration_ms INTEGER NOT NULL,
  checksum TEXT,
  created_at TEXT NOT NULL
);

-- Indexation recommandée
CREATE INDEX idx_traits_version ON traits(trait_id, version);
CREATE INDEX idx_souvenirs_category_score ON souvenirs(category, importance_score DESC);
CREATE INDEX idx_souvenirs_tags ON souvenirs(tags);
CREATE INDEX idx_souvenirs_hash ON souvenirs(hash);
CREATE INDEX idx_interactions_session ON interaction_logs(session_id, occurred_at DESC);
CREATE INDEX idx_session_goals_priority ON session_goals(session_id, priority DESC);
CREATE INDEX idx_audit_endpoint ON request_audit(endpoint, created_at DESC);




