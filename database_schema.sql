-- FPL Chatbot Conversation System Database Schema
-- Run this SQL in your Supabase SQL Editor to create the conversations table

-- Create conversations table for storing chat history
CREATE TABLE IF NOT EXISTS conversations (
    id BIGSERIAL PRIMARY KEY,
    session_id TEXT NOT NULL,
    user_message TEXT NOT NULL,
    ai_response TEXT NOT NULL,
    query_type TEXT DEFAULT 'general',
    response_time NUMERIC DEFAULT 0.0,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_conversations_session_id ON conversations (session_id);
CREATE INDEX IF NOT EXISTS idx_conversations_created_at ON conversations (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_conversations_query_type ON conversations (query_type);

-- Create RLS (Row Level Security) policies if needed
-- Enable RLS on the table
ALTER TABLE conversations ENABLE ROW LEVEL SECURITY;

-- Create policy to allow all operations for now (you can restrict this later)
CREATE POLICY "Allow all operations on conversations" 
ON conversations 
FOR ALL 
USING (true) 
WITH CHECK (true);

-- Add comments for documentation
COMMENT ON TABLE conversations IS 'Stores chat conversation history between users and AI';
COMMENT ON COLUMN conversations.session_id IS 'Unique identifier for chat sessions';
COMMENT ON COLUMN conversations.user_message IS 'User input message';
COMMENT ON COLUMN conversations.ai_response IS 'AI generated response';
COMMENT ON COLUMN conversations.query_type IS 'Type of query (general, player, fixture, etc.)';
COMMENT ON COLUMN conversations.response_time IS 'Time taken to generate response in seconds';
COMMENT ON COLUMN conversations.metadata IS 'Additional metadata (confidence, sources, etc.)';
COMMENT ON COLUMN conversations.created_at IS 'When the conversation message was created';
