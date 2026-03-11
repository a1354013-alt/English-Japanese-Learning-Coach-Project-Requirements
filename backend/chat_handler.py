"""
WebSocket handler for AI Role-play Chat
"""
import json
from typing import List, Dict, Any
from fastapi import WebSocket, WebSocketDisconnect
from ollama_client import ollama_client
from config import settings

class ChatManager:
    """Manage active WebSocket connections for chat"""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        
    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        
    async def handle_chat(self, websocket: WebSocket, language: str, scenario: str):
        """Handle real-time chat session with personality and memory"""
        # Retrieve user memory from DB (mocked for now, but could be from a 'user_memories' table)
        user_memory = "User mentioned they want to travel to Tokyo and love anime."
        
        system_prompt = f"""
        You are a friendly and encouraging language coach named 'Manus'. 
        Scenario: {scenario}. Language: {language}.
        
        Personality:
        - You are patient, slightly humorous, and very supportive.
        - You remember details about the user to build an emotional connection.
        - User Memory: {user_memory}
        
        Instructions:
        - Keep responses short (1-3 sentences).
        - Occasionally refer to the user's interests (e.g., Tokyo, anime) to show you remember them.
        - Gently correct grammar mistakes.
        - Always end with a question to keep the conversation going.
        """
        
        history = [{"role": "system", "content": system_prompt}]
        
        try:
            while True:
                data = await websocket.receive_text()
                message = json.loads(data)
                user_text = message.get("text", "")
                
                if not user_text:
                    continue
                    
                history.append({"role": "user", "content": user_text})
                
                # Construct conversation context from recent history (last 8 turns)
                conversation_context = "Conversation so far:\n"
                # Exclude system prompt and take up to last 8 messages
                recent_history = history[max(1, len(history) - 8):]
                for msg in recent_history:
                    if msg["role"] == "user":
                        conversation_context += f"User: {msg["content"]}\n"
                    elif msg["role"] == "assistant":
                        conversation_context += f"Assistant: {msg["content"]}\n"
                
                full_prompt = f"{conversation_context}User: {user_text}"

                # Call Ollama (using small model for faster response)
                response = ollama_client.generate(
                    prompt=full_prompt,
                    system_prompt=history[0]["content"],
                    model=settings.small_model_name,
                    format="text",
                    use_cache=False
                )
                
                if response['success']:
                    ai_text = response['response']
                    history.append({"role": "assistant", "content": ai_text})
                    await websocket.send_json({
                        "role": "assistant",
                        "text": ai_text
                    })
                else:
                    await websocket.send_json({
                        "role": "system",
                        "text": "Error: AI partner is unavailable."
                    })
                    
        except WebSocketDisconnect:
            self.disconnect(websocket)

chat_manager = ChatManager()
