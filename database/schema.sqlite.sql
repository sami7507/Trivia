-- Triavia schema — SQLite flavour. No patient names or identifiers are stored with assessments.

CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    provider      TEXT NOT NULL,                 -- google | mobile | guest
    provider_id   TEXT NOT NULL,                 -- google sub | E.164 phone | random id
    name          TEXT,
    email         TEXT,
    phone         TEXT,
    created_at    TEXT NOT NULL,                 -- ISO-8601 UTC, set by the app
    last_login_at TEXT,
    UNIQUE (provider, provider_id)
);

CREATE TABLE IF NOT EXISTS assessments (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER,
    created_at      TEXT    NOT NULL,
    age             INTEGER NOT NULL,
    chief_complaint TEXT    NOT NULL,
    triage_level    INTEGER NOT NULL CHECK (triage_level BETWEEN 0 AND 3),
    triage_label    TEXT    NOT NULL,
    confidence      REAL    NOT NULL,
    safety_override INTEGER NOT NULL DEFAULT 0,
    inputs_json     TEXT    NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_assessments_created ON assessments(created_at DESC);

-- One-time SMS codes (stored hashed, short-lived, attempt-limited)
CREATE TABLE IF NOT EXISTS otp_codes (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    phone      TEXT NOT NULL,
    code_hash  TEXT NOT NULL,
    expires_at REAL NOT NULL,
    attempts   INTEGER NOT NULL DEFAULT 0,
    created_at REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_otp_phone ON otp_codes(phone, created_at);

-- Single-use codes the frontend swaps for a session token after Google sign-in
CREATE TABLE IF NOT EXISTS login_codes (
    code_hash  TEXT PRIMARY KEY,
    user_id    INTEGER NOT NULL,
    expires_at REAL NOT NULL
);

-- Visitor feedback from the in-app form (read by the author via GET /api/v1/feedback with the service key)
CREATE TABLE IF NOT EXISTS feedback (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    user_id    INTEGER,
    rating     INTEGER,
    message    TEXT NOT NULL,
    contact    TEXT
);
