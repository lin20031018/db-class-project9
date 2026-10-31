CREATE TABLE IF NOT EXISTS venue (
    vid BIGSERIAL PRIMARY KEY,
    venue_name VARCHAR(128) NOT NULL,
    venue_type VARCHAR(80) NOT NULL,
    capacity INTEGER NOT NULL CHECK (capacity > 0 AND capacity <= 100000),
    status VARCHAR(20) NOT NULL CHECK (status IN ('open','closed','maintenance')),
    description VARCHAR(2000) NOT NULL DEFAULT '',
    deleted_at TIMESTAMPTZ
);
CREATE UNIQUE INDEX IF NOT EXISTS venue_name_unique ON venue (lower(trim(venue_name))) WHERE deleted_at IS NULL;
CREATE TABLE IF NOT EXISTS venue_equipment (
    vid BIGINT NOT NULL REFERENCES venue(vid),
    equipment_name VARCHAR(128) NOT NULL,
    status VARCHAR(80) NOT NULL,
    quantity INTEGER NOT NULL CHECK (quantity >= 0 AND quantity <= 100000),
    PRIMARY KEY (vid, equipment_name)
);
ALTER TABLE reservation ADD COLUMN IF NOT EXISTS venue_id BIGINT REFERENCES venue(vid);
-- Preserve any reservations from the initial development migration.
INSERT INTO venue (venue_name,venue_type,capacity,status)
SELECT DISTINCT ON (lower(trim(r.venue))) trim(r.venue),'未分類',100000,'open'
FROM reservation r WHERE r.venue_id IS NULL
AND NOT EXISTS (SELECT 1 FROM venue v WHERE lower(trim(v.venue_name))=lower(trim(r.venue)) AND v.deleted_at IS NULL)
ON CONFLICT DO NOTHING;
UPDATE reservation r SET venue_id=v.vid FROM venue v
WHERE r.venue_id IS NULL AND lower(trim(r.venue))=lower(trim(v.venue_name)) AND v.deleted_at IS NULL;
ALTER TABLE reservation ALTER COLUMN venue_id SET NOT NULL;
ALTER TABLE reservation DROP CONSTRAINT IF EXISTS reservation_status_check;
ALTER TABLE reservation ADD CONSTRAINT reservation_status_check CHECK (status IN ('pending','approved','rejected','cancelled'));
ALTER TABLE app_user ALTER COLUMN did SET NOT NULL;
CREATE TABLE IF NOT EXISTS usage_record (
    rid BIGINT NOT NULL REFERENCES reservation(id),
    urid INTEGER NOT NULL DEFAULT 1,
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP,
    comment VARCHAR(2000) NOT NULL DEFAULT '',
    PRIMARY KEY (rid,urid),
    UNIQUE (rid),
    CHECK (end_time IS NULL OR end_time > start_time)
);
