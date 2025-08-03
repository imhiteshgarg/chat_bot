from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import requests
import traceback
import logging
import json
import os
import sqlite3
from datetime import datetime
from typing import List, Optional
import uuid
from database import init_database, create_session, save_message, get_conversation_history, get_recent_sessions
import aiohttp
from mcp_sqllite import MCPSQLiteManager
from ollama_utils import parse_ollama_response, make_ollama_request
from models import ChatRequest, ChatResponse, SessionResponse, MessageHistory, ConversationHistory, SessionInfo

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('chat_bot.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# Initialize MCP manager
mcp_manager = MCPSQLiteManager()

# Database setup
DATABASE_NAME = os.getenv("DATABASE_NAME", "chat_history.db")

app = FastAPI()

# Add CORS middleware to allow frontend requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve the main page
@app.get("/")
async def read_index():
    return FileResponse('index.html')

# Serve the JavaScript file
@app.get("/app.js")
async def read_app_js():
    return FileResponse('app.js', media_type='application/javascript')

@app.on_event("startup")
async def startup_event():
    logger.info("Chat bot application starting up")
    logger.info(f"Ollama API URL: {OLLAMA_API_URL}")
    logger.info(f"Model: {MODEL_NAME}")
    init_database()
    
    # Attempt to start MCP SQLite server (optional)
    logger.info("Attempting to start MCP SQLite server...")
    mcp_started = await mcp_manager.start_server()
    if mcp_started:
        logger.info("✅ MCP SQLite server started - database analysis features available")
    else:
        logger.warning("⚠️ MCP SQLite server failed to start - database analysis will use basic mode")
        logger.info("💡 To enable full MCP features, install Node.js and run: npm install -g mcp-sqlite")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Chat bot application shutting down")
    mcp_manager.stop_server()
    logger.info("Application shutdown complete")

OLLAMA_API_URL = os.getenv("OLLAMA_API_URL", "http://localhost:11434/api/chat")
MODEL_NAME = os.getenv("MODEL_NAME", "llama3.1")


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    logger.info(f"Received chat request with message length: {len(req.message)}")
    logger.info(f"Request session ID: {req.session_id if req.session_id else 'None (will create new)'}")
    logger.debug(f"User message: {req.message}")
    
    try:
        # Create new session if not provided
        session_id = req.session_id
        if not session_id:
            session_id = create_session()
            logger.info(f"Created new session: {session_id}")
        else:
            logger.info(f"Using existing session: {session_id}")
        
        # Save user message to database
        save_message(session_id, "user", req.message)
        
        # Check if this is a database analysis request
        if mcp_manager.is_database_query(req.message):
            logger.info("Detected database query, using MCP for analysis")
            reply = await mcp_manager.execute_database_query(req.message)
            
            # Add context about what Leo can analyze
            reply += "\n\n🤖 I can analyze your chat history and provide insights like:"
            reply += "\n• Session statistics and activity trends"
            reply += "\n• Message patterns and conversation lengths"
            reply += "\n• Recent activity summaries"
            reply += "\n• Most active conversations"
            reply += "\n\nJust ask me questions about your chat data!"
            
        else:
            # Get conversation history from database for regular chat
            conversation = []
            history = get_conversation_history(session_id)
            for msg in history:
                conversation.append({"role": msg["role"], "content": msg["content"]})
            
            logger.info(f"Loaded conversation history. Total messages: {len(conversation)}")

            response = make_ollama_request(conversation)
            reply = parse_ollama_response(response)
            
            logger.info(f"Received reply from Ollama with length: {len(reply)}")
            logger.debug(f"Assistant reply: {reply}")
        
        # Save assistant response to database
        save_message(session_id, "assistant", reply)
        logger.info("Saved assistant reply to database")

        return ChatResponse(response=reply, session_id=session_id)
    
    except requests.exceptions.RequestException as e:
        logger.error(f"Network error when calling Ollama API: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail="Network error occurred")
    
    except Exception as e:
        logger.error(f"Unexpected error in chat endpoint: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/sessions", response_model=SessionResponse)
def create_new_session():
    """Create a new chat session."""
    session_id = create_session()
    return SessionResponse(session_id=session_id)

@app.get("/sessions", response_model=List[SessionInfo])
def list_sessions():
    """Get list of recent chat sessions."""
    try:
        sessions = get_recent_sessions()
        return [SessionInfo(**session) for session in sessions]
    except Exception as e:
        logger.error(f"Error fetching sessions: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch sessions")

@app.get("/sessions/{session_id}", response_model=ConversationHistory)
def get_session_history(session_id: str):
    """Get conversation history for a specific session."""
    try:
        messages = get_conversation_history(session_id)
        history = [MessageHistory(**msg) for msg in messages]
        return ConversationHistory(session_id=session_id, messages=history)
    except Exception as e:
        logger.error(f"Error fetching session history: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch session history")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
