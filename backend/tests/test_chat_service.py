"""Coverage for chat prompt continuity orchestration."""

from __future__ import annotations

import asyncio
import unittest
from typing import Any

from app.core.config import Settings
from app.models.chat import ChatMessage, ChatRequest, ChatResponse
from app.services.chat_service import ChatService


class FakeOllamaClient:
    def __init__(self, stream_frames: list[str] | None = None) -> None:
        self.requests: list[ChatRequest] = []
        self.stream_frames = stream_frames or []

    async def chat(
        self, request: ChatRequest, *, request_id: str | None = None
    ) -> ChatResponse:
        self.requests.append(request)
        return ChatResponse(
            model="fake-model",
            message=ChatMessage(role="assistant", content="I hear you."),
        )

    async def stream_chat(self, request: ChatRequest, *, request_id: str | None = None):
        self.requests.append(request)
        for frame in self.stream_frames:
            yield frame


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

    def trigger_reflection(
        self, conversation_history: list[dict[str, str]]
    ) -> dict[str, Any]:
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
        ChatService._last_growth_notification_at = 0.0
        ChatService._emitted_growth_notification_ids.clear()

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
                            "summary": "Use gentle reassurance when the user feels anxious.",
                            "memory_worthy": True,
                        }
                    ],
                    "themes": ["trust"],
                    "confidence": 0.8,
                    "evidence_count": 2,
                    "growth_notification": {
                        "id": "growth_journal_1",
                        "journal_entry_id": "journal_1",
                        "created_at": "2026-06-11T00:00:00Z",
                        "message": "Reverie seems steadier lately.",
                        "why": "A private reflection noticed a trust pattern.",
                        "theme": "trust",
                        "style": "whisper",
                        "controls": ["dismiss", "review", "disable_similar"],
                    },
                }
            ]
        )
        service = ChatService(
            settings=Settings(
                reflection_min_interval_seconds=0,
                reflection_user_message_interval=6,
                growth_notification_min_user_messages=1,
                growth_notification_message_interval=1,
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
        self.assertIsNotNone(response.growth_notification)
        self.assertEqual(response.growth_notification.id, "growth_journal_1")
        self.assertEqual(
            response.growth_notification.message, "Reverie seems steadier lately."
        )
        prepared_messages = ollama.requests[0].messages
        self.assertEqual(prepared_messages[0].content, "You are Reverie.")
        self.assertIn("Long-term memory context", prepared_messages[1].content)
        self.assertIn("User prefers gentle reassurance", prepared_messages[1].content)
        self.assertIn(
            "Private reflection journal context", prepared_messages[2].content
        )
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

    def test_reflection_disabled_skips_journal_context_and_background_work(
        self,
    ) -> None:
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

    def test_growth_notifications_wait_for_message_count_and_interval(self) -> None:
        asyncio.run(self._assert_growth_notifications_wait_for_count_and_interval())

    async def _assert_growth_notifications_wait_for_count_and_interval(self) -> None:
        entry = {
            "entry_id": "journal_timing",
            "status": "active",
            "character_summary": "I noticed trust becoming easier.",
            "insights": [
                {"summary": "Trust is becoming steadier.", "memory_worthy": True}
            ],
            "themes": ["trust"],
            "confidence": 0.85,
            "evidence_count": 2,
            "growth_notification": {
                "id": "growth_journal_timing",
                "journal_entry_id": "journal_timing",
                "created_at": "2026-06-11T00:00:00Z",
                "message": "Reverie seems more confident in your trust.",
                "why": "A private reflection noticed a trust pattern.",
                "theme": "trust",
                "style": "whisper",
                "controls": ["dismiss", "review", "disable_similar"],
            },
        }
        service = ChatService(
            settings=Settings(
                memory_enabled=False,
                reflection_min_interval_seconds=0,
                growth_notification_min_user_messages=3,
                growth_notification_message_interval=3,
                growth_notification_min_interval_seconds=0,
            ),
            ollama_client=FakeOllamaClient(),  # type: ignore[arg-type]
            reflection_manager=FakeReflectionManager(entries=[entry]),  # type: ignore[arg-type]
        )

        too_early = await service.chat(
            ChatRequest(
                stream=False,
                messages=[
                    ChatMessage(role="user", content="Please remember this."),
                    ChatMessage(role="user", content="Please remember this too."),
                ],
            ),
            request_id="req-growth-too-early",
        )
        interval_turn = await service.chat(
            ChatRequest(
                stream=False,
                messages=[
                    ChatMessage(role="user", content="Please remember this."),
                    ChatMessage(role="user", content="Please remember this too."),
                    ChatMessage(
                        role="user", content="Please remember this third thing."
                    ),
                ],
            ),
            request_id="req-growth-interval",
        )

        self.assertIsNone(too_early.growth_notification)
        self.assertIsNotNone(interval_turn.growth_notification)

    def test_growth_notifications_are_throttled_and_configurable(self) -> None:
        asyncio.run(self._assert_growth_notifications_are_throttled_and_configurable())

    async def _assert_growth_notifications_are_throttled_and_configurable(self) -> None:
        entry = {
            "entry_id": "journal_growth",
            "status": "active",
            "character_summary": "I noticed trust becoming easier.",
            "insights": [
                {"summary": "Trust is becoming steadier.", "memory_worthy": True}
            ],
            "themes": ["trust"],
            "confidence": 0.85,
            "evidence_count": 2,
            "growth_notification": {
                "id": "growth_journal_growth",
                "journal_entry_id": "journal_growth",
                "created_at": "2026-06-11T00:00:00Z",
                "message": "Reverie seems more confident in your trust.",
                "why": "A private reflection noticed a trust pattern.",
                "theme": "trust",
                "style": "whisper",
                "controls": ["dismiss", "review", "disable_similar"],
            },
        }
        request = ChatRequest(
            stream=False,
            messages=[ChatMessage(role="user", content="Please remember this.")],
        )

        service = ChatService(
            settings=Settings(
                memory_enabled=False,
                reflection_min_interval_seconds=0,
                growth_notification_min_user_messages=1,
                growth_notification_message_interval=1,
                growth_notification_min_interval_seconds=999,
            ),
            ollama_client=FakeOllamaClient(),  # type: ignore[arg-type]
            reflection_manager=FakeReflectionManager(entries=[entry]),  # type: ignore[arg-type]
        )

        first = await service.chat(request, request_id="req-growth-1")
        second = await service.chat(request, request_id="req-growth-2")

        self.assertIsNotNone(first.growth_notification)
        self.assertIsNone(second.growth_notification)

        disabled_service = ChatService(
            settings=Settings(
                memory_enabled=False,
                growth_notifications_enabled=False,
                reflection_min_interval_seconds=0,
                growth_notification_min_user_messages=1,
                growth_notification_message_interval=1,
                growth_notification_min_interval_seconds=0,
            ),
            ollama_client=FakeOllamaClient(),  # type: ignore[arg-type]
            reflection_manager=FakeReflectionManager(entries=[entry]),  # type: ignore[arg-type]
        )

        disabled = await disabled_service.chat(
            request, request_id="req-growth-disabled"
        )
        self.assertIsNone(disabled.growth_notification)

    def test_emotion_inference_attaches_neutral_fallback_when_confidence_is_low(
        self,
    ) -> None:
        asyncio.run(self._assert_emotion_inference_neutral_fallback())

    async def _assert_emotion_inference_neutral_fallback(self) -> None:
        service = ChatService(
            settings=Settings(memory_enabled=False, reflection_enabled=False),
            ollama_client=FakeOllamaClient(),  # type: ignore[arg-type]
        )

        response = await service.chat(
            ChatRequest(
                stream=False,
                messages=[ChatMessage(role="user", content="The lamp is on the desk.")],
            ),
            request_id="req-neutral-visual",
        )

        self.assertIsNotNone(response.visual_state)
        self.assertEqual(response.visual_state.expression, "neutral")
        self.assertLessEqual(response.visual_state.confidence, 0.34)

    def test_stream_emotion_inference_runs_only_on_done_with_growth_cue(self) -> None:
        asyncio.run(self._assert_stream_emotion_inference_done_only())

    async def _assert_stream_emotion_inference_done_only(self) -> None:
        entry = {
            "entry_id": "journal_growth_visual",
            "status": "active",
            "character_summary": "I am learning a gentler reassurance rhythm.",
            "themes": ["growth", "reassurance"],
            "confidence": 0.82,
            "growth_notification": {
                "id": "growth_visual",
                "journal_entry_id": "journal_growth_visual",
                "created_at": "2026-06-11T00:00:00Z",
                "message": "Reverie is practicing gentler reassurance.",
                "why": "A private reflection noticed a growth pattern.",
                "theme": "growth",
            },
        }
        service = ChatService(
            settings=Settings(
                memory_enabled=False,
                reflection_min_interval_seconds=999,
                growth_notification_min_user_messages=1,
                growth_notification_message_interval=1,
                growth_notification_min_interval_seconds=0,
            ),
            ollama_client=FakeOllamaClient(
                stream_frames=[
                    'event: message\ndata: {"content": "I am learning ", "request_id": "req"}\n\n',
                    'event: message\ndata: {"content": "to reassure you gently.", "request_id": "req"}\n\n',
                    'event: done\ndata: {"done": true, "request_id": "req"}\n\n',
                ]
            ),  # type: ignore[arg-type]
            reflection_manager=FakeReflectionManager(entries=[entry]),  # type: ignore[arg-type]
        )

        frames = [
            frame
            async for frame in await service.stream_chat(
                ChatRequest(
                    stream=True,
                    messages=[
                        ChatMessage(
                            role="user",
                            content="I feel anxious but want to trust the process.",
                        )
                    ],
                ),
                request_id="req-stream-visual",
            )
        ]

        self.assertNotIn("visual_state", frames[0])
        self.assertNotIn("visual_state", frames[1])
        self.assertIn("visual_state", frames[2])
        self.assertIn('"growth_cue": "growth"', frames[2])
        self.assertIn("growth_notification", frames[2])


if __name__ == "__main__":
    unittest.main()
