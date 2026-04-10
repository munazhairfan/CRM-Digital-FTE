-- migration_add_conversation_summaries.sql
-- Run once against your Neon PostgreSQL database.
-- Adds the conversation_summaries table used by message_repo.py
-- for 7-day episodic memory retrieval.

CREATE TABLE IF NOT EXISTS conversation_summaries (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id     UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    customer_id         UUID NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    channel             VARCHAR(50) NOT NULL,
    summary             TEXT NOT NULL,
    created_at          TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- One summary per conversation (upserted on re-resolution)
    CONSTRAINT uq_conversation_summary UNIQUE (conversation_id)
);

-- Index for fast 7-day lookups by customer
CREATE INDEX IF NOT EXISTS idx_summaries_customer_created
    ON conversation_summaries (customer_id, created_at DESC);

-- Add plan_tier to customer metadata if not already present
-- (used by get_customer_context for profile memory)
COMMENT ON COLUMN customers.metadata IS
    'JSONB bag. Recognized keys: plan_tier (free|pro|enterprise), company, notes';
