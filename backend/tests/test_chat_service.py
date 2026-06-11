"""Coverage for chat prompt continuity orchestration."""

from __future__ import annotations

import asyncio
import unittest
from typing import Any

from app.core.config import Settings
from app.models.chat import ChatMessage, ChatRequest, ChatResponse
from app.services.chat_service import ChatService


class FakeOllamaClient:
    def __init__(self) -> None:
        self.requests: list[ChatRequest] = []

    async def chat(
        self, request: ChatRequest, *, request_id: str | None = None
    ) -> ChatResponse:
        self.requests.append(request)
        return ChatResponse(
            model="fake-model",
            message=ChatMessage(role="assistant", content="I hear you."),
        )


class FakeMemoryManager:
    def __init__(self, context: str = "", failure: Exception | None = None) -> None:
        self.context = context
        self.failure = failure
        self.queries: list[str] = []

    def get_relevant_context(self, query: str) -> str:
        self.queries.append(query)
        if self.failure:
            raise self.failure
        return self.context


class FakeReflectionManager:
    def __init__(
        self,
        *,
        entries: list[dict[str, Any]] | None = None,
        trigger_failure: Exception | None = None,
        recent_failure: Exception | None = None,
    ) -> None:
        self.entries = entries or []
        self.trigger_failure = trigger_failure
        self.recent_failure = recent_failure
        self.triggered_histories: list[list[dict[str, str]]] = []

    def get_recent_journal_entries(self, limit: int = 5) -> list[dict[str, Any]]:
        if self.recent_failure:
            raise self.recent_failure
        return self.entries[:limit]

    def trigger_reflection(self, conversation_history: list[dict[str, str]]) -> dict[str, Any]:
        if self.trigger_failure:
            raise self.trigger_failure
        self.triggered_histories.append(conversation_history)
        return {
            "entry_id": f"journal_fake_{len(self.triggered_histories)}",
            "insights": [{"summary": "The user values reassurance."}],
            "linked_memory_ids": [],
        }


class ChatServiceReflectionTests(unittest.TestCase):
    def setUp(self) -> None:
        ChatService._reflection_lock = None
        ChatService._last_reflection_started_at = 0.0
        ChatService._inflight_reflection_tasks.clear()

    def test_chat_injects_memory_and_reflection_context_then_triggers_background_reflection(
        self,
    ) -> None:
        asyncio.run(self._assert_chat_injects_and_triggers())

    async def _assert_chat_injects_and_triggers(self) -> None:
        ollama = FakeOllamaClient()
        memory = FakeMemoryManager(context="User prefers gentle reassurance.")
        reflection = FakeReflectionManager(
            entries=[
                {
                    "entry_id": "journal_1",
                    "status": "active",
                    "character_summary": "I noticed reassurance helps the user feel safe.",
                    "insights": [
                        {
                            "summary": "Use gentle reassurance when the user feels anxious."
                        }
                    ],
                    "themes": ["trust"],
                    "confidence": 0.8,
                }
            ]
        )
        service = ChatService(
            settings=Settings(
                reflection_min_interval_seconds=0,
                reflection_user_message_interval=6,
            ),
            ollama_client=ollama,  # type: ignore[arg-type]
            memory_manager=memory,  # type: ignore[arg-type]
            reflection_manager=reflection,  # type: ignore[arg-type]
        )
        request = ChatRequest(
            stream=False,
            messages=[
                ChatMessage(role="system", content="You are Reverie."),
                ChatMessage(
                    role="user",
                    content="Please remember that reassurance helps when I feel anxious.",
                ),
            ],
        )

        response = await service.chat(request, request_id="req-test")
        await asyncio.gather(*ChatService._inflight_reflection_tasks)

        self.assertEqual(response.message.content, "I hear you.")
        prepared_messages = ollama.requests[0].messages
        self.assertEqual(prepared_messages[0].content, "You are Reverie.")
        self.assertIn("Long-term memory context", prepared_messages[1].content)
        self.assertIn("User prefers gentle reassurance", prepared_messages[1].content)
        self.assertIn("Private reflection journal context", prepared_messages[2].content)
        self.assertIn("tentative, lower-priority", prepared_messages[2].content)
        self.assertIn("not canon rewrites", prepared_messages[2].content)
        self.assertIn("reassurance helps the user", prepared_messages[2].content)
        self.assertEqual(prepared_messages[3].role, "user")
        self.assertEqual(len(reflection.triggered_histories), 1)
        self.assertEqual(reflection.triggered_histories[0][-1]["role"], "user")

    def test_reflection_failures_do_not_block_chat(self) -> None:
        asyncio.run(self._assert_reflection_failures_do_not_block())

    async def _assert_reflection_failures_do_not_block(self) -> None:
        ollama = FakeOllamaClient()
        reflection = FakeReflectionManager(
            recent_failure=RuntimeError("journal unavailable"),
            trigger_failure=RuntimeError("reflection unavailable"),
        )
        service = ChatService(
            settings=Settings(reflection_min_interval_seconds=0),
            ollama_client=ollama,  # type: ignore[arg-type]
            memory_manager=FakeMemoryManager(),  # type: ignore[arg-type]
            reflection_manager=reflection,  # type: ignore[arg-type]
        )
        request = ChatRequest(
            stream=False,
            messages=[
                ChatMessage(role="user", content="Please remember this boundary."),
            ],
        )

        response = await service.chat(request, request_id="req-fail")
        await asyncio.gather(*ChatService._inflight_reflection_tasks)

        self.assertEqual(response.message.content, "I hear you.")
        self.assertEqual(len(ollama.requests), 1)
        self.assertEqual(ollama.requests[0].messages, request.messages)

    def test_reflection_disabled_skips_journal_context_and_background_work(self) -> None:
        asyncio.run(self._assert_reflection_disabled_skips_work())

    async def _assert_reflection_disabled_skips_work(self) -> None:
        ollama = FakeOllamaClient()
        reflection = FakeReflectionManager(
            entries=[
                {
                    "entry_id": "journal_1",
                    "status": "active",
                    "character_summary": "Should not be injected.",
                    "confidence": 1.0,
                }
            ]
        )
        service = ChatService(
            settings=Settings(reflection_enabled=False, memory_enabled=False),
            ollama_client=ollama,  # type: ignore[arg-type]
            reflection_manager=reflection,  # type: ignore[arg-type]
        )
        request = ChatRequest(
            stream=False,
            messages=[ChatMessage(role="user", content="Please remember this.")],
        )

        await service.chat(request, request_id="req-disabled")

        self.assertEqual(ollama.requests[0].messages, request.messages)
        self.assertEqual(reflection.triggered_histories, [])


if __name__ == "__main__":
    unittest.main()
