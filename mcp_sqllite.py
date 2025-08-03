import asyncio
import os
import json
from typing import Optional
from ollama_utils import parse_ollama_response
import logging
import requests
import sqlite3

# Get logger and constants
logger = logging.getLogger(__name__)
DATABASE_NAME = os.getenv("DATABASE_NAME", "chat_history.db")
OLLAMA_API_URL = os.getenv("OLLAMA_API_URL", "http://localhost:11434/api/chat")
MODEL_NAME = os.getenv("MODEL_NAME", "llama3.1")

# MCP SQLite Server Manager
class MCPSQLiteManager:
    def __init__(self):
        self.server_process = None
        self.server_running = False
        self.request_id = 0
        
    async def start_server(self):
        """Start the MCP SQLite server as a subprocess."""
        try:
            # Check if npx is available
            result = await asyncio.create_subprocess_exec(
                'which', 'npx',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await result.wait()
            
            if result.returncode != 0:
                logger.error("npx not found. Please install Node.js and npm")
                return False
                
            # Start the MCP SQLite server
            db_path = os.path.abspath(DATABASE_NAME)
            self.server_process = await asyncio.create_subprocess_exec(
                'npx', '-y', 'mcp-sqlite', db_path,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            # Give the server a moment to start
            await asyncio.sleep(2)
            
            if self.server_process.returncode is None:
                # Initialize MCP connection
                init_success = await self._initialize_mcp_connection()
                if init_success:
                    self.server_running = True
                    logger.info("MCP SQLite server started successfully")
                    return True
                else:
                    logger.error("MCP SQLite server started but initialization failed")
                    return False
            else:
                logger.error("MCP SQLite server failed to start")
                return False
                
        except Exception as e:
            logger.error(f"Error starting MCP SQLite server: {e}")
            return False
    
    async def _initialize_mcp_connection(self):
        """Initialize the MCP connection with handshake."""
        try:
            # Send initialize request
            init_request = {
                "jsonrpc": "2.0",
                "id": self._get_request_id(),
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "tools": {}
                    },
                    "clientInfo": {
                        "name": "Leo Chatbot",
                        "version": "1.0.0"
                    }
                }
            }
            
            response = await self._send_mcp_request(init_request)
            if response and "result" in response:
                logger.info("MCP initialization successful")
                return True
            else:
                logger.error(f"MCP initialization failed: {response}")
                return False
                
        except Exception as e:
            logger.error(f"Error initializing MCP connection: {e}")
            return False
    
    def _get_request_id(self):
        """Get next request ID."""
        self.request_id += 1
        return self.request_id
    
    async def _send_mcp_request(self, request):
        """Send a JSON-RPC request to the MCP server."""
        try:
            if not self.server_process or not self.server_process.stdin:
                return None
                
            # Send request
            request_str = json.dumps(request) + "\n"
            self.server_process.stdin.write(request_str.encode())
            await self.server_process.stdin.drain()
            
            # Read response
            response_line = await self.server_process.stdout.readline()
            if response_line:
                response = json.loads(response_line.decode().strip())
                return response
            else:
                return None
                
        except Exception as e:
            logger.error(f"Error sending MCP request: {e}")
            return None
    
    def stop_server(self):
        """Stop the MCP SQLite server."""
        if self.server_process:
            self.server_process.terminate()
            self.server_running = False
            logger.info("MCP SQLite server stopped")
    
    def is_database_query(self, message: str) -> bool:
        """Check if the message is asking for database analysis."""
        keywords = [
            'database', 'db', 'sql', 'query', 'table', 'sessions', 'messages',
            'conversation', 'chat history', 'statistics', 'stats', 'count',
            'analyze', 'analysis', 'data', 'search history', 'most active',
            'recent sessions', 'message count', 'user activity', 'trends'
        ]
        message_lower = message.lower()
        return any(keyword in message_lower for keyword in keywords)
    
    async def execute_database_query(self, user_question: str = None) -> str:
        """Execute database analysis using MCP tools."""
        if not self.server_running:
            # Fallback to basic analysis
            return self._basic_database_analysis()
        
        try:
            # Always try natural language processing first for any database query
            if user_question and user_question.strip():
                logger.info(f"Attempting natural language processing for: {user_question}")
                custom_result = await self._handle_natural_language_query(user_question)
                if custom_result:
                    logger.info("Natural language processing succeeded")
                    return custom_result
                else:
                    logger.info("Natural language processing failed, falling back to default analysis")
            
            # Use MCP to get comprehensive database analysis
            results = await self._get_mcp_database_stats()
            
            if results:
                return "\n".join(results)
            else:
                return "No database analysis results available via MCP."
                
        except Exception as e:
            logger.error(f"Error in MCP database analysis: {e}")
            return self._basic_database_analysis()
    
    async def _handle_natural_language_query(self, user_question: str) -> Optional[str]:
        """Convert natural language question to SQL and execute via MCP."""
        try:
            logger.info(f"Processing natural language query: {user_question}")
            
            # Check for metadata queries that might be better handled with MCP tools
            if self._is_metadata_query(user_question):
                metadata_result = await self._handle_metadata_query(user_question)
                if metadata_result:
                    return metadata_result
            
            # Generate SQL from natural language using LLM
            sql_query = await self._generate_sql_from_question(user_question)
            
            if sql_query:
                logger.info(f"Generated SQL: {sql_query}")
                
                # Execute the generated SQL via MCP
                result = await self._call_mcp_tool("query", {
                    "sql": sql_query,
                    "values": []
                })
                
                if result:
                    # Format the results nicely
                    formatted_result = self._format_query_results(result)
                    return f"📊 **Answer to: \"{user_question}\"**\n\n{formatted_result}\n\n💡 *Generated SQL: `{sql_query}`*"
                else:
                    logger.warning(f"MCP query returned no results for: {sql_query}")
                    return f"❌ No results found for: \"{user_question}\""
            else:
                logger.warning(f"Could not generate SQL for question: {user_question}")
                return None  # Fall back to default analysis
                
        except Exception as e:
            logger.error(f"Error handling natural language query: {e}")
            return None
    
    def _is_metadata_query(self, question: str) -> bool:
        """Check if the question is asking for database metadata."""
        metadata_keywords = [
            'table', 'tables', 'schema', 'structure', 'columns', 'database structure',
            'what tables', 'how many tables', 'table names', 'table list'
        ]
        question_lower = question.lower()
        return any(keyword in question_lower for keyword in metadata_keywords)
    
    async def _handle_metadata_query(self, user_question: str) -> Optional[str]:
        """Handle metadata queries using MCP tools."""
        try:
            question_lower = user_question.lower()
            
            if any(phrase in question_lower for phrase in ['how many tables', 'count tables', 'number of tables']):
                # Get table count
                tables = await self._call_mcp_tool("list_tables", {})
                if tables:
                    if isinstance(tables, dict) and 'tables' in tables:
                        table_count = len(tables['tables'])
                    elif isinstance(tables, list):
                        table_count = len(tables)
                    else:
                        table_count = "Unknown"
                    
                    return f"📊 **Answer to: \"{user_question}\"**\n\n**Result:** {table_count} tables\n\n💡 *Used MCP list_tables tool*"
            
            elif any(phrase in question_lower for phrase in ['what tables', 'list tables', 'table names', 'show tables']):
                # List all tables
                tables = await self._call_mcp_tool("list_tables", {})
                if tables:
                    if isinstance(tables, dict) and 'tables' in tables:
                        table_list = tables['tables']
                    elif isinstance(tables, list):
                        table_list = tables
                    else:
                        table_list = []
                    
                    if table_list:
                        formatted_tables = []
                        for i, table in enumerate(table_list, 1):
                            if isinstance(table, dict) and 'name' in table:
                                formatted_tables.append(f"  {i}. {table['name']}")
                            else:
                                formatted_tables.append(f"  {i}. {table}")
                        
                        return f"📊 **Answer to: \"{user_question}\"**\n\n**Tables in your database:**\n" + "\n".join(formatted_tables) + "\n\n💡 *Used MCP list_tables tool*"
            
            elif any(phrase in question_lower for phrase in ['database info', 'db info', 'database structure']):
                # Get database info
                db_info = await self._call_mcp_tool("db_info", {})
                if db_info:
                    formatted_info = []
                    if isinstance(db_info, dict):
                        for key, value in db_info.items():
                            formatted_info.append(f"  • {key}: {value}")
                    
                    return f"📊 **Answer to: \"{user_question}\"**\n\n**Database Information:**\n" + "\n".join(formatted_info) + "\n\n💡 *Used MCP db_info tool*"
            
            return None
            
        except Exception as e:
            logger.error(f"Error handling metadata query: {e}")
            return None
    
    async def _generate_sql_from_question(self, question: str) -> Optional[str]:
        """Use LLM to convert natural language question to SQL."""
        try:
            # Database schema information
            schema_info = """
            Database Schema:
            - sessions table: id (TEXT), created_at (TIMESTAMP), last_activity (TIMESTAMP)
            - messages table: id (INTEGER), session_id (TEXT), role (TEXT), content (TEXT), timestamp (TIMESTAMP)
            
            The 'role' field contains either 'user' or 'assistant'.
            """
            
            prompt = f"""Convert this natural language question to a SQL query for a chat application database.

{schema_info}

Question: {question}

Generate ONLY the SQL query, no explanations. The query should be safe and read-only (SELECT only).
If the question cannot be converted to SQL or seems unsafe, respond with "INVALID".

Examples:
- "How many messages have I sent?" → SELECT COUNT(*) FROM messages WHERE role = 'user'
- "What are my most recent conversations?" → SELECT s.id, s.last_activity FROM sessions s ORDER BY s.last_activity DESC LIMIT 5
- "How many sessions do I have?" → SELECT COUNT(*) FROM sessions
- "How many tables do I have?" → SELECT COUNT(*) FROM sqlite_master WHERE type='table'
- "What tables exist?" → SELECT name FROM sqlite_master WHERE type='table'
- "Show me table information" → SELECT name, type FROM sqlite_master WHERE type='table'

For metadata queries about tables, use sqlite_master system table:
- sqlite_master contains: name, type, sql columns
- type='table' for user tables

SQL Query:"""

            # Use the existing Ollama connection
            response = requests.post(OLLAMA_API_URL, json={
                "model": MODEL_NAME,
                "messages": [{"role": "user", "content": prompt}],
                "stream": False
            })
            
            if response.status_code == 200:
                sql_query = parse_ollama_response(response).strip()
                
                # Remove markdown code block formatting if present
                if sql_query.startswith('```sql'):
                    sql_query = sql_query.replace('```sql', '').replace('```', '').strip()
                elif sql_query.startswith('```'):
                    sql_query = sql_query.replace('```', '').strip()
                
                # Basic safety checks
                if (sql_query.upper().startswith('SELECT') and 
                    'DROP' not in sql_query.upper() and 
                    'DELETE' not in sql_query.upper() and 
                    'UPDATE' not in sql_query.upper() and 
                    'INSERT' not in sql_query.upper() and
                    sql_query != "INVALID"):
                    return sql_query
                else:
                    logger.warning(f"Generated unsafe or invalid SQL: {sql_query}")
                    return None
            else:
                logger.error(f"LLM request failed: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Error generating SQL from question: {e}")
            return None
    
    def _format_query_results(self, result) -> str:
        """Format MCP query results for display."""
        try:
            data = self._extract_query_results(result)
            
            if not data:
                return "No data found."
            
            if len(data) == 1 and len(data[0]) == 1:
                # Single value result
                value = list(data[0].values())[0]
                return f"**Result:** {value}"
            else:
                # Multi-row or multi-column result
                formatted_lines = []
                for i, row in enumerate(data[:10]):  # Limit to first 10 rows
                    if isinstance(row, dict):
                        row_items = []
                        for key, value in row.items():
                            row_items.append(f"{key}: {value}")
                        formatted_lines.append(f"  • {', '.join(row_items)}")
                    else:
                        formatted_lines.append(f"  • {row}")
                
                if len(data) > 10:
                    formatted_lines.append(f"  ... and {len(data) - 10} more rows")
                
                return "\n".join(formatted_lines)
                
        except Exception as e:
            logger.error(f"Error formatting query results: {e}")
            return f"Results available but formatting failed: {str(e)}"
    
    async def _get_mcp_database_stats(self):
        """Get database statistics using MCP tools."""
        results = []
        
        # Get database info using MCP
        db_info = await self._call_mcp_tool("db_info", {})
        if db_info:
            results.append("📊 **Database Information (via MCP):**")
            results.append(f"Database: {DATABASE_NAME}")
            if isinstance(db_info, dict):
                # Add any additional info from MCP response
                for key, value in db_info.items():
                    if key not in ['tables']:  # Skip tables here, handle separately
                        results.append(f"{key}: {value}")
        
        # List tables using MCP
        tables = await self._call_mcp_tool("list_tables", {})
        if tables:
            if isinstance(tables, dict) and 'tables' in tables:
                table_list = tables['tables']
            elif isinstance(tables, list):
                table_list = tables
            elif isinstance(tables, str):
                # If it's a string, try to extract table names
                table_list = [tables]
            else:
                table_list = []
                
            if table_list:
                results.append(f"\n🗂️ **Tables:** {', '.join(str(t) for t in table_list)}")
        
        # Get session statistics using MCP query
        session_stats = await self._call_mcp_tool("query", {
            "sql": "SELECT COUNT(*) as total_sessions FROM sessions",
            "values": []
        })
        if session_stats:
            total_sessions = self._extract_query_result(session_stats, 'total_sessions')
            if total_sessions is not None:
                results.append(f"\n📈 **Total Sessions:** {total_sessions}")
        
        # Get message statistics using MCP query
        message_stats = await self._call_mcp_tool("query", {
            "sql": "SELECT COUNT(*) as total_messages FROM messages",
            "values": []
        })
        if message_stats:
            total_messages = self._extract_query_result(message_stats, 'total_messages')
            if total_messages is not None:
                results.append(f"💬 **Total Messages:** {total_messages}")
        
        # Get recent activity using MCP query
        recent_activity = await self._call_mcp_tool("query", {
            "sql": """
                SELECT DATE(s.last_activity) as date, COUNT(*) as sessions
                FROM sessions s 
                WHERE s.last_activity > datetime('now', '-7 days')
                GROUP BY DATE(s.last_activity) 
                ORDER BY date DESC 
                LIMIT 5
            """,
            "values": []
        })
        if recent_activity:
            activity_data = self._extract_query_results(recent_activity)
            if activity_data:
                results.append("\n📅 **Recent Activity (last 7 days):**")
                for row in activity_data:
                    if isinstance(row, dict) and 'date' in row and 'sessions' in row:
                        results.append(f"  • {row['date']}: {row['sessions']} sessions")
        
        # Get most active sessions using MCP query
        active_sessions = await self._call_mcp_tool("query", {
            "sql": """
                SELECT s.id, COUNT(m.id) as message_count, 
                       datetime(s.last_activity) as last_active
                FROM sessions s 
                LEFT JOIN messages m ON s.id = m.session_id 
                GROUP BY s.id 
                ORDER BY message_count DESC 
                LIMIT 3
            """,
            "values": []
        })
        if active_sessions:
            sessions_data = self._extract_query_results(active_sessions)
            if sessions_data:
                results.append("\n🔥 **Most Active Sessions:**")
                for i, row in enumerate(sessions_data, 1):
                    if isinstance(row, dict) and all(key in row for key in ['id', 'message_count', 'last_active']):
                        short_id = str(row['id'])[:8] + "..."
                        results.append(f"  {i}. Session {short_id}: {row['message_count']} messages (last active: {row['last_active']})")
        
        if results:
            results.append("\n✅ *Analysis via MCP SQLite server*")
        
        return results
    
    def _extract_query_result(self, query_response, column_name):
        """Extract a single value from MCP query response."""
        try:
            if isinstance(query_response, dict):
                if 'results' in query_response and isinstance(query_response['results'], list):
                    results = query_response['results']
                    if len(results) > 0 and isinstance(results[0], dict):
                        return results[0].get(column_name)
                elif column_name in query_response:
                    return query_response[column_name]
            return None
        except Exception as e:
            logger.error(f"Error extracting query result for {column_name}: {e}")
            return None
    
    def _extract_query_results(self, query_response):
        """Extract multiple rows from MCP query response."""
        try:
            if isinstance(query_response, dict) and 'results' in query_response:
                return query_response['results']
            elif isinstance(query_response, list):
                return query_response
            return []
        except Exception as e:
            logger.error(f"Error extracting query results: {e}")
            return []
    
    async def _call_mcp_tool(self, tool_name: str, arguments: dict):
        """Call an MCP tool and return the result."""
        try:
            request = {
                "jsonrpc": "2.0",
                "id": self._get_request_id(),
                "method": "tools/call",
                "params": {
                    "name": tool_name,
                    "arguments": arguments
                }
            }
            
            response = await self._send_mcp_request(request)
            if response and "result" in response:
                # Handle different response formats
                result = response["result"]
                
                # If result has content array (text response)
                if isinstance(result, dict) and "content" in result:
                    content = result["content"]
                    if isinstance(content, list) and len(content) > 0:
                        text_content = content[0].get("text", "")
                        # Try to parse as JSON if it looks like JSON
                        try:
                            return json.loads(text_content)
                        except (json.JSONDecodeError, TypeError):
                            return text_content
                
                # Return result directly if it's already structured data
                return result
            else:
                logger.warning(f"MCP tool call failed for {tool_name}: {response}")
                return None
                
        except Exception as e:
            logger.error(f"Error calling MCP tool {tool_name}: {e}")
            return None
    
    def _basic_database_analysis(self) -> str:
        """Fallback basic database analysis when MCP is not available."""
        try:
            conn = sqlite3.connect(DATABASE_NAME)
            cursor = conn.cursor()
            
            results = []
            
            # Session count
            cursor.execute("SELECT COUNT(*) FROM sessions")
            session_count = cursor.fetchone()[0]
            results.append(f"📊 **Total Sessions:** {session_count}")
            
            # Message count
            cursor.execute("SELECT COUNT(*) FROM messages")
            message_count = cursor.fetchone()[0]
            results.append(f"💬 **Total Messages:** {message_count}")
            
            # Recent activity
            cursor.execute("""
                SELECT DATE(s.last_activity) as date, COUNT(*) as sessions
                FROM sessions s 
                WHERE s.last_activity > datetime('now', '-7 days')
                GROUP BY DATE(s.last_activity) 
                ORDER BY date DESC 
                LIMIT 5
            """)
            recent_activity = cursor.fetchall()
            if recent_activity:
                results.append("\n📅 **Recent Activity (last 7 days):**")
                for date, count in recent_activity:
                    results.append(f"  • {date}: {count} sessions")
            
            # Most active sessions
            cursor.execute("""
                SELECT s.id, COUNT(m.id) as message_count, 
                       datetime(s.last_activity) as last_active
                FROM sessions s 
                LEFT JOIN messages m ON s.id = m.session_id 
                GROUP BY s.id 
                ORDER BY message_count DESC 
                LIMIT 3
            """)
            active_sessions = cursor.fetchall()
            if active_sessions:
                results.append("\n🔥 **Most Active Sessions:**")
                for i, (session_id, msg_count, last_active) in enumerate(active_sessions, 1):
                    short_id = session_id[:8] + "..."
                    results.append(f"  {i}. Session {short_id}: {msg_count} messages (last active: {last_active})")
            
            conn.close()
            
            results.append("\n⚠️ *Using basic mode - MCP server not available*")
            return "\n".join(results)
            
        except Exception as e:
            logger.error(f"Error in basic database analysis: {e}")
            return f"Error analyzing database: {str(e)}"
