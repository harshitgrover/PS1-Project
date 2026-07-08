-- Run this in the Supabase SQL Editor to create the tables

CREATE TABLE IF NOT EXISTS zone_rules (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    location TEXT NOT NULL,
    zone TEXT NOT NULL,
    rule_key TEXT NOT NULL,
    rule_value TEXT,
    description TEXT,
    UNIQUE (location, zone, rule_key)
);

CREATE TABLE IF NOT EXISTS style_rules (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    style TEXT NOT NULL,
    rule_key TEXT NOT NULL,
    rule_value TEXT,
    description TEXT,
    UNIQUE (style, rule_key)
);

CREATE TABLE IF NOT EXISTS entity_specs (
    entity_type TEXT PRIMARY KEY,
    min_area_ft2 REAL,
    min_side_ft REAL,
    max_side_ft REAL,
    habitable BOOLEAN,
    min_aspect_ratio REAL,
    max_aspect_ratio REAL,
    requires_exterior_window BOOLEAN,
    requires_egress BOOLEAN,
    ventilation_type TEXT,
    requires_door BOOLEAN,
    requires_closet BOOLEAN,
    area_rules_json TEXT
);

CREATE TABLE IF NOT EXISTS adjacency_rules (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_entity TEXT NOT NULL,
    target_entity TEXT NOT NULL,
    relation TEXT NOT NULL,
    min_shared_wall_ft REAL,
    max_dist_ft REAL,
    description TEXT,
    UNIQUE (source_entity, target_entity, relation)
);
