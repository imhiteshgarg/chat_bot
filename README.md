# 🦁 Leo - AI Chat Assistant

A beautiful, modern AI chat interface built with FastAPI and vanilla JavaScript, featuring Leo as your friendly AI assistant.

## Features

- 🎨 Beautiful gradient UI with smooth animations
- 🌓 **Dark/Light Mode Theming** - Toggle between themes with full CSS variable support
- 💬 Session-based chat with persistent history
- 🔍 **Message Search** - Search across all conversations with real-time highlighting
- 🔊 **Sound Notifications** - Toggle audio notifications on/off with persistent preference
- 🎈 Interactive visual effects (balloons, stars, hearts, confetti, fireworks)
- 📱 Fully responsive design with advanced hover effects
- 🦁 Meet Leo - your AI companion with personality
- 📋 Command history with arrow key navigation
- 💾 SQLite database for conversation storage
- 🎯 Click-to-navigate search results
- 🗂️ Enhanced session management with sidebar navigation
- ✨ Smooth transitions and polished UI interactions
- 📊 **Database Analysis** - Ask Leo about your chat statistics and patterns via MCP integration

## Prerequisites

- Python 3.8 or higher
- [Ollama](https://ollama.ai/) installed and running locally
- Git (optional, for cloning)
- Node.js and npm (optional, for enhanced MCP database analysis)

## Quick Start

### 1. Clone the Repository

```bash
git clone <your-repo-url>
cd chat_bot
```

### 2. Set Up Python Environment

```bash
# Create virtual environment
python -m venv .venv

# Activate virtual environment
# On macOS/Linux:
source .venv/bin/activate
# On Windows:
.venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Set Up Ollama

Make sure Ollama is installed and running:

```bash
# Install Ollama (if not already installed)
# Visit https://ollama.ai/ for installation instructions

# Pull the required model
ollama pull llama3.1

# Verify Ollama is running
ollama list
```

### 5. Run the Application

```bash
python main.py
```

The application will:
- Automatically create an empty SQLite database (`chat_history.db`)
- Start the web server on `http://localhost:8000`
- Initialize all necessary database tables

### 6. Open Your Browser

Navigate to `http://localhost:8000` and start chatting with Leo!

### 7. Enhanced Database Analysis (Optional)

For advanced database analysis features, install the MCP SQLite server:

```bash
# Install Node.js (if not already installed)
# Visit https://nodejs.org/ for installation instructions

# Install the MCP SQLite server globally
npm install -g mcp-sqlite
```

Leo will automatically detect and use the MCP server if available, providing enhanced database analysis capabilities.

## Usage

### Basic Chat
- Type your messages and press Enter or click Send
- Leo will respond using the Ollama AI model
- Each conversation is automatically saved

### Dark/Light Mode Theming
- Click the 🌓 **Theme** button in the top-right corner to toggle between dark and light modes
- Theme preference is automatically saved and restored
- All UI components seamlessly adapt to the selected theme

### Sound Notifications
- Click the 🔊 **Sound** button in the top-right corner to toggle audio notifications
- When enabled, Leo plays a pleasant C major chord when responding to messages
- Sound preference is automatically saved and restored across sessions
- Visual feedback shows 🔊 when enabled or 🔇 when muted (with red highlighting)

### Message Search
- Use the 🔍 **Search** input at the top of the sidebar to find messages
- Search works across all conversations and sessions
- Matching text is highlighted in real-time
- Click on search results to jump directly to that conversation

### Visual Effects
Try these special commands:
- "Show me balloons" 🎈
- "Show me stars" ⭐
- "Show me hearts" 💖
- "Show me confetti" 🎉
- "Show me fireworks" 🎆

Or use the "✨ Show me" dropdown button in the top-right corner!

### Database Analysis (MCP Integration)
Leo can analyze your chat history and provide insights! Try asking:
- "Show me my chat statistics"
- "How many conversations have I had?"
- "What's my recent activity?"
- "Analyze my database"
- "Show me session stats"

Leo will automatically detect database-related questions and provide:
- 📊 Total session and message counts
- 📅 Recent activity trends (last 7 days)
- 🔥 Most active conversations
- 📈 Usage patterns and statistics

**Note**: For enhanced database analysis, Leo attempts to start an MCP SQLite server. If Node.js is not installed, basic analysis mode is used.

### Navigation
- **Arrow Keys**: Navigate through your command history (Up/Down arrows in input field)
- **Enter Key**: Send messages quickly without clicking the send button
- **New Chat**: Start a fresh conversation
- **Sidebar**: View and switch between previous chat sessions
- **Search Results**: Click any search result to navigate to that conversation
- **Session Switching**: Seamlessly switch between conversations with full history

### User Experience Features
- **Typing Indicators**: Animated dots show when Leo is processing your message
- **Auto-scroll**: Messages automatically scroll to the latest response
- **Error Handling**: Graceful error messages and fallback behaviors
- **Input Validation**: Message length limits and input sanitization
- **Persistent State**: All preferences and session data saved automatically

## Configuration

### Changing the AI Model

Edit `main.py` and modify these variables:

```python
OLLAMA_API_URL = "http://localhost:11434/api/chat"
MODEL_NAME = "llama3.1"  # Change to your preferred model
```

**Popular Model Options:**
- `llama3.1` (8B) - Good balance of speed and quality (recommended)
- `llama3.1:70b` - Higher quality, requires more resources
- `codellama` - Specialized for programming tasks
- `mistral` - Fast and efficient alternative

To switch models:
```bash
ollama pull <model-name>
# Then update MODEL_NAME in main.py
```

### Database Location

The SQLite database is automatically created as `chat_history.db` in the project directory. This file is excluded from git via `.gitignore` to keep your conversations private.

## Development

### Project Structure

```
chat_bot/
├── main.py              # FastAPI backend server
├── index.html           # Frontend interface with theming & search
├── app.js               # JavaScript functionality (modular organization)
├── database.py          # Database operations and schema
├── models.py            # Pydantic models and data structures
├── ollama_utils.py      # Ollama API integration utilities
├── mcp_sqllite.py       # MCP SQLite server management
├── requirements.txt     # Python dependencies
├── .gitignore          # Git ignore rules (protects database)
├── chat_history.db     # SQLite database (auto-created, excluded from git)
└── chat_bot.log        # Application logs
```

### Key Technical Features

- **Theming System**: CSS custom properties (variables) for comprehensive dark/light mode support
- **Search Implementation**: Real-time search with debouncing and result highlighting
- **Session Management**: UUID-based sessions with full conversation history
- **Visual Effects**: Canvas-based animations triggered by keywords or manual selection
- **Responsive Design**: Mobile-first approach with smooth transitions
- **Database Security**: SQLite database automatically excluded from version control

### API Endpoints

- `GET /` - Serve the main chat interface
- `GET /app.js` - Serve the JavaScript module file
- `POST /chat` - Send message and get AI response  
- `GET /sessions` - List recent chat sessions
- `GET /sessions/{id}` - Get specific session history
- `POST /sessions` - Create new session

### Frontend Features

- **Theme Toggle**: Persistent dark/light mode switching
- **Sound Notifications**: Audio feedback with Web Audio API and localStorage persistence
- **Search Functionality**: Cross-session message search with highlighting
- **Visual Effects**: Keyword-triggered canvas animations
- **Session Navigation**: Smooth switching between conversation histories
- **Responsive Layout**: Adaptive design for all screen sizes
- **Modular JavaScript**: Clean separation of concerns with organized app.js file

## Security Notes

- The SQLite database containing your chat history is automatically excluded from git
- Each fresh clone starts with an empty database
- Chat sessions are identified by UUIDs for privacy
- No data is sent to external services except your local Ollama instance

## Troubleshooting

### Ollama Connection Issues
- Ensure Ollama is running: `ollama list`
- Check if the model is available: `ollama pull llama3.1`
- Verify Ollama is accessible at `http://localhost:11434`

### Database Issues
- The database is automatically created on first run
- If you encounter issues, delete `chat_history.db` and restart the application

### Port Conflicts
If port 8000 is in use, modify the uvicorn command in `main.py`:

```python
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)  # Change port here
```

## Contributing

Feel free to submit issues and enhancement requests!

## License

This project is open source and available under the MIT License.

---

**Enjoy chatting with Leo! 🦁**