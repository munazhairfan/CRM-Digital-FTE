-- =============================================
-- FlowForge Customer Success FTE - CRM Database
-- PostgreSQL Schema (Production)
-- =============================================

-- 1. Customers (unified across channels)
CREATE TABLE customers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE,
    phone VARCHAR(50),
    name VARCHAR(255),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'
);

-- 2. Customer Identifiers (for cross-channel matching)
CREATE TABLE customer_identifiers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id UUID REFERENCES customers(id) ON DELETE CASCADE,
    identifier_type VARCHAR(20) NOT NULL, -- 'email', 'phone', 'wa_id'
    identifier_value VARCHAR(255) NOT NULL,
    verified BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(identifier_type, identifier_value)
);

-- 3. Conversations (one conversation = one customer thread)
CREATE TABLE conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id UUID REFERENCES customers(id) ON DELETE CASCADE,
    initial_channel VARCHAR(20) NOT NULL,
    started_at TIMESTAMPTZ DEFAULT NOW(),
    ended_at TIMESTAMPTZ,
    status VARCHAR(20) DEFAULT 'active', -- active, resolved, escalated
    sentiment_score DECIMAL(3,2),
    resolution_type VARCHAR(50),
    escalated_to VARCHAR(255),
    metadata JSONB DEFAULT '{}'
);

-- 4. Messages (full history with channel tracking)
CREATE TABLE messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID REFERENCES conversations(id) ON DELETE CASCADE,
    channel VARCHAR(20) NOT NULL,
    direction VARCHAR(10) NOT NULL, -- inbound, outbound
    role VARCHAR(20) NOT NULL, -- customer, agent, system
    content TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    sentiment DECIMAL(3,2),
    tokens_used INTEGER,
    latency_ms INTEGER,
    tool_calls JSONB DEFAULT '[]',
    channel_message_id VARCHAR(255), -- Gmail ID, Twilio SID, etc.
    delivery_status VARCHAR(20) DEFAULT 'pending'
);

-- 5. Tickets (your main CRM table)
CREATE TABLE tickets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID REFERENCES conversations(id),
    customer_id UUID REFERENCES customers(id),
    ticket_number VARCHAR(20) UNIQUE, -- TKT-XXXXXX
    source_channel VARCHAR(20) NOT NULL,
    category VARCHAR(100),
    priority VARCHAR(20) DEFAULT 'medium',
    status VARCHAR(20) DEFAULT 'open', -- open, in_progress, resolved, escalated
    created_at TIMESTAMPTZ DEFAULT NOW(),
    resolved_at TIMESTAMPTZ,
    resolution_notes TEXT,
    escalated_reason TEXT
);

-- 6. Knowledge Base (with pgvector for RAG)
-- Note: pgvector must be enabled. On Neon, run: CREATE EXTENSION IF NOT EXISTS vector;
CREATE TABLE knowledge_base (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR(500) NOT NULL,
    content TEXT NOT NULL,
    category VARCHAR(100),
    embedding VECTOR(1536), -- OpenAI text-embedding-3-small
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 7. Escalated Tickets (for human handoff tracking)
CREATE TABLE escalated_tickets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ticket_id UUID REFERENCES tickets(id),
    reason TEXT NOT NULL,
    urgency VARCHAR(20),
    escalated_at TIMESTAMPTZ DEFAULT NOW(),
    status VARCHAR(20) DEFAULT 'pending', -- pending, assigned, resolved
    notes TEXT
);

-- 8. Agent Metrics (for daily sentiment reports)
CREATE TABLE agent_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    metric_name VARCHAR(100) NOT NULL,
    metric_value DECIMAL(10,4),
    channel VARCHAR(20),
    recorded_at TIMESTAMPTZ DEFAULT NOW(),
    dimensions JSONB DEFAULT '{}'
);

-- Indexes for performance
CREATE INDEX idx_customers_email ON customers(email);
CREATE INDEX idx_customer_identifiers_value ON customer_identifiers(identifier_value);
CREATE INDEX idx_conversations_customer ON conversations(customer_id);
CREATE INDEX idx_messages_conversation ON messages(conversation_id);
CREATE INDEX idx_tickets_status ON tickets(status);
CREATE INDEX idx_tickets_channel ON tickets(source_channel);
CREATE INDEX idx_knowledge_embedding ON knowledge_base USING ivfflat (embedding vector_cosine_ops);
CREATE INDEX idx_escalated_tickets_status ON escalated_tickets(status);

-- Enable pgvector extension (run once)
-- CREATE EXTENSION IF NOT EXISTS vector;