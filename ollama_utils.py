import requests
import json
import logging
import os
from fastapi import HTTPException

# Get logger and constants
logger = logging.getLogger(__name__)
OLLAMA_API_URL = os.getenv("OLLAMA_API_URL", "http://localhost:11434/api/chat")
MODEL_NAME = os.getenv("MODEL_NAME", "llama3.1")

def parse_ollama_response(response):
    """Parse Ollama API response, handling both streaming and non-streaming formats."""
    logger.debug(f"Raw response content: {response.text}")
    
    try:
        response_data = response.json()
        return response_data["message"]["content"]
    except ValueError as json_error:
        # Handle streaming response format
        logger.warning(f"Received streaming response, parsing manually: {json_error}")
        response_lines = response.text.strip().split('\n')
        
        for line in reversed(response_lines):  # Start from the last line for efficiency
            if line.strip():
                try:
                    line_data = json.loads(line)
                    if "message" in line_data and "content" in line_data["message"]:
                        return line_data["message"]["content"]
                except json.JSONDecodeError:
                    logger.warning(f"Could not parse line: {line}")
                    continue
        
        logger.error("Could not extract reply from streaming response")
        raise HTTPException(status_code=500, detail="Failed to parse LLM response")

def make_ollama_request(messages):
    """Make request to Ollama API and return the response."""
    logger.info(f"Sending request to Ollama API: {OLLAMA_API_URL}")
    response = requests.post(OLLAMA_API_URL, json={
        "model": MODEL_NAME,
        "messages": messages,
        "stream": False  # Explicitly request non-streaming response
    })
    
    logger.info(f"Ollama API response status: {response.status_code}")
    
    if response.status_code != 200:
        logger.error(f"Ollama API call failed with status {response.status_code}: {response.text}")
        raise HTTPException(status_code=500, detail="LLM call failed")
    
    return response
