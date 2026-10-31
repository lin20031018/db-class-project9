-- 可重複執行；不變更既有書店資料。
CREATE TABLE IF NOT EXISTS department (
    did VARCHAR(20) PRIMARY KEY,
    dname VARCHAR(128) NOT NULL
);
INSERT INTO department (did, dname) VALUES ('GENERAL', '校園共同單位')
ON CONFLICT (did) DO NOTHING;

CREATE TABLE IF NOT EXISTS app_user (
    uid VARCHAR(20) PRIMARY KEY,
    user_name VARCHAR(128) NOT NULL,
    password_hash TEXT NOT NULL,
    identity VARCHAR(20) NOT NULL CHECK (identity IN ('student', 'teacher', 'manager')),
    email VARCHAR(254) NOT NULL UNIQUE,
    phone VARCHAR(40),
    did VARCHAR(20) REFERENCES department(did)
);

CREATE TABLE IF NOT EXISTS reservation (
    id BIGSERIAL PRIMARY KEY,
    applicant_uid VARCHAR(20) NOT NULL REFERENCES app_user(uid),
    venue VARCHAR(128) NOT NULL CHECK (length(trim(venue)) > 0),
    starts_at TIMESTAMP NOT NULL,
    ends_at TIMESTAMP NOT NULL,
    purpose VARCHAR(1000) NOT NULL CHECK (length(trim(purpose)) > 0),
    attendees INTEGER NOT NULL CHECK (attendees > 0 AND attendees <= 100000),
    status VARCHAR(20) NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'approved', 'rejected')),
    review_note VARCHAR(1000) NOT NULL DEFAULT '',
    reviewed_by VARCHAR(20) REFERENCES app_user(uid),
    reviewed_at TIMESTAMPTZ,
    created_by VARCHAR(20) NOT NULL REFERENCES app_user(uid),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at TIMESTAMPTZ,
    version INTEGER NOT NULL DEFAULT 1,
    CHECK (ends_at > starts_at)
);
CREATE INDEX IF NOT EXISTS reservation_schedule_idx
    ON reservation (starts_at, ends_at) WHERE deleted_at IS NULL;
CREATE TABLE IF NOT EXISTS reservation_audit (
    id BIGSERIAL PRIMARY KEY,
    reservation_id BIGINT NOT NULL REFERENCES reservation(id),
    actor_uid VARCHAR(20) NOT NULL REFERENCES app_user(uid),
    action VARCHAR(30) NOT NULL,
    note TEXT NOT NULL DEFAULT '',
    occurred_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
