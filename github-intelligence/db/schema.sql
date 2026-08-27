-- pgi SQLite Schema v1 草案（TASK-P0-03）
-- 原则：事实表只存 API 原始事实；分析结果一律进 *_analysis 表（另行设计）
-- 字段命名 snake_case；JSON 列后缀 _json

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS schema_meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

-- ---------------------------------------------------------------- 仓库维度
CREATE TABLE IF NOT EXISTS repos (
    id            TEXT PRIMARY KEY,              -- github:repo:owner/name
    full_name     TEXT NOT NULL UNIQUE,          -- owner/name
    description   TEXT,
    primary_language TEXT,
    stars         INTEGER NOT NULL DEFAULT 0,
    forks         INTEGER NOT NULL DEFAULT 0,
    is_fork       INTEGER NOT NULL DEFAULT 0,
    is_archived   INTEGER NOT NULL DEFAULT 0,
    visibility    TEXT NOT NULL DEFAULT 'public',  -- public|private
    created_at    TEXT,                          -- ISO8601 (UTC)
    pushed_at     TEXT,
    topics_json   TEXT NOT NULL DEFAULT '[]',
    my_role       TEXT,                          -- owner|contributor|viewer
    first_synced_at TEXT NOT NULL,
    last_synced_at  TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_repos_pushed ON repos(pushed_at DESC);

CREATE TABLE IF NOT EXISTS repo_languages (
    repo_id  TEXT NOT NULL REFERENCES repos(id) ON DELETE CASCADE,
    language TEXT NOT NULL,
    pct      REAL NOT NULL,
    PRIMARY KEY (repo_id, language)
);

CREATE TABLE IF NOT EXISTS dependencies (
    repo_id TEXT NOT NULL REFERENCES repos(id) ON DELETE CASCADE,
    name    TEXT NOT NULL,
    version TEXT,
    kind    TEXT NOT NULL,                       -- runtime|dev
    PRIMARY KEY (repo_id, name, kind)
);
CREATE INDEX IF NOT EXISTS idx_deps_name ON dependencies(name);

-- ---------------------------------------------------------------- 提交/议题/发布
CREATE TABLE IF NOT EXISTS commits (
    id           TEXT PRIMARY KEY,               -- github:commit:owner/name@sha
    repo_id      TEXT NOT NULL REFERENCES repos(id) ON DELETE CASCADE,
    sha          TEXT NOT NULL,
    authored_at  TEXT NOT NULL,
    author_email TEXT,
    message      TEXT NOT NULL,
    additions    INTEGER,
    deletions    INTEGER,
    files_changed INTEGER,
    is_my_commit INTEGER NOT NULL DEFAULT 1,
    UNIQUE (repo_id, sha)
);
CREATE INDEX IF NOT EXISTS idx_commits_repo_time ON commits(repo_id, authored_at);

CREATE TABLE IF NOT EXISTS issues (
    id        TEXT PRIMARY KEY,                  -- github:issue:owner/name#123 (含 PR)
    repo_id   TEXT NOT NULL REFERENCES repos(id) ON DELETE CASCADE,
    number    INTEGER NOT NULL,
    title     TEXT NOT NULL,
    state     TEXT NOT NULL,                     -- open|closed
    is_pr     INTEGER NOT NULL DEFAULT 0,
    labels_json TEXT NOT NULL DEFAULT '[]',
    opened_at TEXT,
    closed_at TEXT,
    UNIQUE (repo_id, number)
);
CREATE INDEX IF NOT EXISTS idx_issues_repo_state ON issues(repo_id, state);

CREATE TABLE IF NOT EXISTS releases (
    id           TEXT PRIMARY KEY,               -- github:release:owner/name@tag
    repo_id      TEXT NOT NULL REFERENCES repos(id) ON DELETE CASCADE,
    tag_name     TEXT NOT NULL,
    name         TEXT,
    published_at TEXT,
    notes        TEXT,
    UNIQUE (repo_id, tag_name)
);

-- 我 star 过的仓库（verdict 继承 stargrave: dead|revisit|keep）
CREATE TABLE IF NOT EXISTS my_stars (
    full_name  TEXT PRIMARY KEY,
    starred_at TEXT,
    verdict    TEXT CHECK (verdict IN ('dead','revisit','keep') OR verdict IS NULL),
    synced_at  TEXT NOT NULL
);

-- ---------------------------------------------------------------- 分析结果（_analysis 约定首例）
-- 一切派生分析入 *_analysis 表，带 model 版本，永不污染事实表（AGENTS 硬约束#3）
CREATE TABLE IF NOT EXISTS timeline_analysis (
    key           TEXT PRIMARY KEY,              -- signals:<来源标识>
    kind          TEXT NOT NULL DEFAULT 'evolution-timeline',
    model_version TEXT NOT NULL,
    payload_json  TEXT NOT NULL,
    created_at    TEXT NOT NULL
);

-- ---------------------------------------------------------------- 同步游标
CREATE TABLE IF NOT EXISTS sync_state (
    entity         TEXT PRIMARY KEY,             -- 例: commits:anyuer678/lumen
    last_synced_at TEXT NOT NULL,
    cursor         TEXT                          -- GraphQL endCursor 等，不透明
);

-- ---------------------------------------------------------------- 全文检索（FTS5 外部内容 + 全量触发器）
CREATE VIRTUAL TABLE IF NOT EXISTS commits_fts USING fts5(
    message, content='commits', content_rowid='rowid'
);
CREATE TRIGGER IF NOT EXISTS commits_ai AFTER INSERT ON commits BEGIN
    INSERT INTO commits_fts(rowid, message) VALUES (new.rowid, new.message);
END;
CREATE TRIGGER IF NOT EXISTS commits_ad AFTER DELETE ON commits BEGIN
    INSERT INTO commits_fts(commits_fts, rowid, message)
    VALUES ('delete', old.rowid, old.message);
END;
CREATE TRIGGER IF NOT EXISTS commits_au AFTER UPDATE ON commits BEGIN
    INSERT INTO commits_fts(commits_fts, rowid, message)
    VALUES ('delete', old.rowid, old.message);
    INSERT INTO commits_fts(rowid, message) VALUES (new.rowid, new.message);
END;

CREATE VIRTUAL TABLE IF NOT EXISTS issues_fts USING fts5(
    title, content='issues', content_rowid='rowid'
);
CREATE TRIGGER IF NOT EXISTS issues_ai AFTER INSERT ON issues BEGIN
    INSERT INTO issues_fts(rowid, title) VALUES (new.rowid, new.title);
END;
CREATE TRIGGER IF NOT EXISTS issues_ad AFTER DELETE ON issues BEGIN
    INSERT INTO issues_fts(issues_fts, rowid, title)
    VALUES ('delete', old.rowid, old.title);
END;
CREATE TRIGGER IF NOT EXISTS issues_au AFTER UPDATE ON issues BEGIN
    INSERT INTO issues_fts(issues_fts, rowid, title)
    VALUES ('delete', old.rowid, old.title);
    INSERT INTO issues_fts(rowid, title) VALUES (new.rowid, new.title);
END;

CREATE VIRTUAL TABLE IF NOT EXISTS repos_fts USING fts5(
    description, content='repos', content_rowid='rowid'
);
CREATE TRIGGER IF NOT EXISTS repos_ai AFTER INSERT ON repos WHEN new.description IS NOT NULL BEGIN
    INSERT INTO repos_fts(rowid, description) VALUES (new.rowid, new.description);
END;
CREATE TRIGGER IF NOT EXISTS repos_ad AFTER DELETE ON repos WHEN old.description IS NOT NULL BEGIN
    INSERT INTO repos_fts(repos_fts, rowid, description)
    VALUES ('delete', old.rowid, old.description);
END;
CREATE TRIGGER IF NOT EXISTS repos_au AFTER UPDATE ON repos BEGIN
    INSERT INTO repos_fts(repos_fts, rowid, description)
    SELECT 'delete', old.rowid, old.description WHERE old.description IS NOT NULL;
    INSERT INTO repos_fts(rowid, description)
    SELECT new.rowid, new.description WHERE new.description IS NOT NULL;
END;
