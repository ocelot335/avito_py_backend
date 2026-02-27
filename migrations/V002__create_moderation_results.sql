CREATE TABLE moderation_results (
    id SERIAL PRIMARY KEY,
    item_id INTEGER NOT NULL REFERENCES ads (id) ON DELETE CASCADE,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    is_violation BOOLEAN,
    probability DOUBLE PRECISION,
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    processed_at TIMESTAMP WITH TIME ZONE
);
CREATE INDEX idx_moderation_results_item_id ON moderation_results (item_id);