-- 크루 러닝 약속. 계정은 없고, 링크 토큰과 호스트 열쇠의 해시만 저장한다.

CREATE TABLE runs (
  id TEXT PRIMARY KEY,
  host_key_hash TEXT NOT NULL,
  title TEXT NOT NULL,
  memo TEXT NOT NULL DEFAULT '',
  host_nickname TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'recruiting' CHECK (status IN ('recruiting', 'confirmed', 'done')),
  max_headcount INTEGER,
  open_join INTEGER NOT NULL DEFAULT 0 CHECK (open_join IN (0, 1)),
  confirmed_date_id TEXT,
  confirmed_time_id TEXT,
  confirmed_course_id TEXT,
  expected_names TEXT NOT NULL DEFAULT '[]',
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE options (
  id TEXT PRIMARY KEY,
  run_id TEXT NOT NULL,
  kind TEXT NOT NULL CHECK (kind IN ('date', 'time', 'course')),
  label TEXT NOT NULL,
  detail TEXT NOT NULL DEFAULT '',
  sort_order INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE participants (
  id TEXT PRIMARY KEY,
  run_id TEXT NOT NULL,
  token_hash TEXT NOT NULL,
  nickname TEXT NOT NULL,
  nickname_key TEXT NOT NULL,
  seat TEXT NOT NULL DEFAULT 'voting' CHECK (seat IN ('voting', 'going', 'waitlist', 'out', 'cancelled')),
  responded INTEGER NOT NULL DEFAULT 0 CHECK (responded IN (0, 1)),
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE votes (
  participant_id TEXT NOT NULL,
  option_id TEXT NOT NULL,
  state INTEGER NOT NULL CHECK (state IN (0, 1, 2)),
  PRIMARY KEY (participant_id, option_id)
);

CREATE TABLE expenses (
  id TEXT PRIMARY KEY,
  run_id TEXT NOT NULL,
  label TEXT NOT NULL,
  amount INTEGER NOT NULL CHECK (amount >= 0),
  sort_order INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE records (
  participant_id TEXT PRIMARY KEY,
  distance_km REAL NOT NULL,
  duration_sec INTEGER NOT NULL,
  memo TEXT NOT NULL DEFAULT '',
  updated_at TEXT NOT NULL
);

CREATE TABLE rate_limits (
  bucket TEXT PRIMARY KEY,
  window_start INTEGER NOT NULL,
  count INTEGER NOT NULL
);

CREATE INDEX idx_options_run ON options(run_id, kind, sort_order);
CREATE INDEX idx_participants_run ON participants(run_id, seat, created_at);
CREATE UNIQUE INDEX idx_participants_token ON participants(run_id, token_hash);
CREATE UNIQUE INDEX idx_participants_nick ON participants(run_id, nickname_key) WHERE seat != 'cancelled';
CREATE INDEX idx_votes_option ON votes(option_id);
CREATE INDEX idx_expenses_run ON expenses(run_id, sort_order);
