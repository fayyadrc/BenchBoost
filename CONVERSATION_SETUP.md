# 💬 FPL Chatbot Conversation System Setup

## 🗄️ Database Setup

To enable the conversation history feature, you need to create the `conversations` table in your Supabase database.

### Step 1: Open Supabase Dashboard
1. Go to https://supabase.com/dashboard
2. Open your FPL Chatbot project
3. Navigate to **SQL Editor** in the left sidebar

### Step 2: Create the Conversations Table
Copy and paste the following SQL into the SQL Editor and click **Run**:

```sql
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

-- Enable RLS (Row Level Security)
ALTER TABLE conversations ENABLE ROW LEVEL SECURITY;

-- Create policy to allow all operations (you can restrict this later)
CREATE POLICY "Allow all operations on conversations" 
ON conversations 
FOR ALL 
USING (true) 
WITH CHECK (true);
```

### Step 3: Verify Table Creation
After running the SQL, you should see:
- ✅ `conversations` table created
- ✅ Indexes created for performance
- ✅ Row Level Security enabled

## 🚀 Features Enabled

Once the table is created, your chatbot will have:

### 💬 **Persistent Conversations**
- Messages are automatically saved to Supabase
- Conversation history persists across browser sessions
- Each user gets a unique session ID

### 📊 **Session Statistics**
- Message count per session
- Average response times
- Query type breakdown
- Session duration tracking

### 🔄 **API Endpoints Available**
- `GET /conversation/history?session_id=xxx` - Get chat history
- `POST /conversation/clear` - Clear session history  
- `GET /conversation/stats?session_id=xxx` - Get session statistics
- `GET /conversations/recent` - Get recent conversations across all sessions

### 🎯 **Frontend Features**
- **New Chat** button clears current conversation
- **Chat Stats** button shows session statistics
- Automatic session management with localStorage
- History loads automatically on page refresh

## 🧪 Testing the System

After creating the table, test the conversation system:

```bash
cd /Users/fayyadrc/Documents/Programming/FPLChatbot
python -m pytest tests/ -v  # If you have tests
```

Or test manually by:
1. Starting the app: `python run.py`
2. Opening http://localhost:8080/chat
3. Sending a few messages
4. Clicking "Chat Stats" to see statistics
5. Refreshing the page to see history persist

## 🔒 Security Considerations

The current setup allows all operations on the conversations table. For production, consider:

1. **Restrict by User**: Add user authentication and limit access to own conversations
2. **Time-based Cleanup**: Automatically delete old conversations
3. **Rate Limiting**: Prevent spam or abuse

## 📈 Monitoring

The conversation system integrates with the existing analytics in Supabase:
- All queries are logged in `query_analytics` table
- Conversation metadata includes confidence scores and sources
- Performance metrics track response times

Your FPL Chatbot now has a complete conversation system! 🎉
