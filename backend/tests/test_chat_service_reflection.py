"""Coverage for chat/reflection orchestration seams."""

from __future__ import annotations

import asyncio
import unittest
from typing import Any

from app.core.config import Settings
from app.models.chat import ChatMessage, ChatRequest, ChatResponse
from app.services.chat_service import ChatService


class FakeOllamaClient:
    """Minimal Ollama stand-in that captures prepared chat requests."""

    def __init__(self) -> None:
        self.requests: list[ChatRequest] = []

    async def chat(
        self, request: ChatRequest, *, request_id: str | None = None
    ) -> ChatResponse:
        self.requests.append(request)
        return ChatResponse(
            model="fake-model",
            message=ChatMessage(role="assistant", content="prepared"),
        )


class FakeReflectionManager:
    """Synchronous ReflectionManager stand-in used through asyncio.to_thread."""

    def __init__(self, *, fail_trigger: bool = False) -> None:
        self.fail_trigger = fail_trigger
        self.triggered_histories: list[list[ChatMessage]] = []

    def get_relevant_reflections(self, query: str) -> list[dict[str, Any]]:
        return [
            {
                "entry_id": "journal_trust",
                "themes": ["trust", "reassurance"],
                "confidence": 0.82,
                "insights": [
                    {
                        "kind": "preference",
                        "summary": "User values gentle reassurance when anxious.",
                        "source_turn_indices": [0],
                    }
                ],
            }
        ]

    def trigger_reflection(self, conversation_history: list[ChatMessage]) -> dict[str, Any]:
        self.triggered_histories.append(conversation_history)
        if self.fail_trigger:
            raise RuntimeError("journal unavailable")
        return {"entry_id": "journal_new", "themes": ["reassurance"], "insights": []}


class ChatServiceReflectionTests(unittest.IsolatedAsyncioTestCase):
    async def test_injects_reflection_context_and_queues_background_reflection(self) -> None:
        ollama = FakeOllamaClient()
        reflection = FakeReflectionManager()
        service = ChatService(
            settings=Settings(memory_enabled=False),
            ollama_client=ollama,  # type: ignore[arg-type]
            reflection_manager=reflection,  # type: ignore[arg-type]
        )
        request = ChatRequest(
            stream=False,
            messages=[
                ChatMessage(role="system", content="Stay in character."),
                ChatMessage(role="user", content="I felt anxious earlier."),
                ChatMessage(role="assistant", content="I stayed close and gentle."),
                ChatMessage(
                    role="user",
                    content="Please remember that reassurance helps me trust you.",
                ),
            ],
        )

        await service.chat(request, request_id="req-reflect")
        await asyncio.sleep(0.05)

        prepared = ollama.requests[0]
        self.assertEqual(prepared.messages[0].content, "Stay in character.")
        self.assertIn("Private reflection journal context", prepared.messages[1].content)
        self.assertIn("User values gentle reassurance", prepared.messages[1].content)
        self.assertEqual(len(reflection.triggered_histories), 1)
        self.assertLessEqual(len(reflection.triggered_histories[0]), 12)

    async def test_background_reflection_failure_does_not_break_chat(self) -> None:
        ollama = FakeOllamaClient()
        reflection = FakeReflectionManager(fail_trigger=True)
        service = ChatService(
            settings=Settings(memory_enabled=False),
            ollama_client=ollama,  # type: ignore[arg-type]
            reflection_manager=reflection,  # type: ignore[arg-type]
        )
        request = ChatRequest(
            stream=False,
            messages=[
                ChatMessage(role="user", content="I was worried."),
                ChatMessage(role="assistant", content="I listened."),
                ChatMessage(role="user", content="Please remember I prefer comfort."),
            ],
        )

        response = await service.chat(request, request_id="req-fail")
        await asyncio.sleep(0.05)

        self.assertEqual(response.message.content, "prepared")
        self.assertEqual(len(ollama.requests), 1)
        self.assertEqual(len(reflection.triggered_histories), 1)


if __name__ == "__main__":
    unittest.main()
