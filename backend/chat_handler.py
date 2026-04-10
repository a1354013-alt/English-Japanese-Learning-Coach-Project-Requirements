"""WebSocket handler for AI role-play chat."""
import json
from typing import Any, Dict, List

from fastapi import WebSocket, WebSocketDisconnect

from config import settings
from ollama_client import ollama_client


class ChatManager:
    def __init__(self) -> None:
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def handle_chat(self, websocket: WebSocket, language: str, scenario: str) -> None:
        # TODO: replace with persisted memory source; this is explicit fallback.
        user_memory_fallback = "No stored user memory is available in this build."

        system_prompt = (
            "You are a supportive language coach. "
            f"Scenario: {scenario}. Language: {language}. "
            f"Memory fallback: {user_memory_fallback} "
            "Respond in 1-3 sentences and end with one follow-up question."
        )

        history: List[Dict[str, Any]] = [{"role": "system", "content": system_prompt}]

        try:
            while True:
                raw = await websocket.receive_text()
                payload = json.loads(raw)
                user_text = str(payload.get("text", "")).strip()
                if not user_text:
                    continue

                history.append({"role": "user", "content": user_text})
                recent = history[-8:]
                lines = []
                for msg in recent:
                    role = msg["role"]
                    if role == "user":
                        lines.append(f"User: {msg['content']}")
                    elif role == "assistant":
                        lines.append(f"Assistant: {msg['content']}")
                full_prompt = "\n".join(lines + [f"User: {user_text}"])

                response = ollama_client.generate(
                    prompt=full_prompt,
                    system_prompt=system_prompt,
                    model=settings.small_model_name,
                    format="text",
                    use_cache=False,
                )

                if response.get("success"):
                    ai_text = response.get("response", "")
                    history.append({"role": "assistant", "content": ai_text})
                    await websocket.send_json({"role": "assistant", "text": ai_text})
                else:
                    await websocket.send_json({
                        "role": "system",
                        "text": "AI chat is currently unavailable.",
                    })
        except WebSocketDisconnect:
            self.disconnect(websocket)


chat_manager = ChatManager()
