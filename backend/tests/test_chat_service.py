"""Coverage for chat prompt continuity orchestration."""

from __future__ import annotations

import asyncio
import json
import unittest
from typing import Any

from app.core.config import Settings
from app.models.chat import ChatMessage, ChatRequest, ChatResponse
from app.models.tts import TTSContext
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

    async def stream_chat(self, request: ChatRequest, *, request_id: str | None = None):
        self.requests.append(request)
        yield 'event: message\ndata: {"content": "I remember ", "request_id": "req-stream"}\n\n'
        yield 'event: message\ndata: {"content": "what helps you feel safe.", "request_id": "req-stream"}\n\n'
        yield 'event: done\ndata: {"done": true, "request_id": "req-stream"}\n\n'


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

    def test_stream_infers_visual_state_only_on_done_event(self) -> None:
        asyncio.run(self._assert_stream_infers_visual_state_only_on_done_event())

    async def _assert_stream_infers_visual_state_only_on_done_event(self) -> None:
        entry = {
            "entry_id": "journal_visual",
            "status": "active",
            "character_summary": "Reverie noticed reassurance and trust help the user feel safe.",
            "insights": [{"summary": "Trust is becoming a warmer pattern."}],
            "themes": ["trust"],
            "confidence": 0.88,
            "evidence_count": 2,
            "growth_notification": {
                "id": "growth_journal_visual",
                "journal_entry_id": "journal_visual",
                "created_at": "2026-06-11T00:00:00Z",
                "message": "Reverie seems steadier in your trust.",
                "why": "A private reflection noticed reassurance helps you feel safe.",
                "theme": "trust",
                "style": "whisper",
                "controls": ["dismiss", "review", "disable_similar"],
            },
        }
        service = ChatService(
            settings=Settings(
                memory_enabled=True,
                reflection_min_interval_seconds=0,
                growth_notification_min_user_messages=1,
                growth_notification_message_interval=1,
                growth_notification_min_interval_seconds=0,
            ),
            ollama_client=FakeOllamaClient(),  # type: ignore[arg-type]
            memory_manager=FakeMemoryManager(context="memory tag: reassurance, safe trust"),  # type: ignore[arg-type]
            reflection_manager=FakeReflectionManager(entries=[entry]),  # type: ignore[arg-type]
        )
        request = ChatRequest(
            stream=True,
            messages=[
                ChatMessage(
                    role="user",
                    content="I feel anxious; please remember reassurance helps.",
                )
            ],
        )

        frames = [
            frame
            async for frame in await service.stream_chat(
                request, request_id="req-stream"
            )
        ]

        self.assertEqual(sum("event: message" in frame for frame in frames), 2)
        self.assertTrue(all("visual_state" not in frame for frame in frames[:2]))
        done_payload = json.loads(frames[-1].split("data: ", 1)[1])
        self.assertEqual(
            done_payload["visual_state"]["growth_cue"], "relationship_trust"
        )
        self.assertIn(
            done_payload["visual_state"]["expression"],
            {"happy", "concerned", "thinking", "neutral"},
        )
        self.assertEqual(
            done_payload["growth_notification"]["id"], "growth_journal_visual"
        )

    def test_chat_echoes_tts_context_for_future_voice_playback(self) -> None:
        async def run_test() -> None:
            tts_context = TTSContext(
                character_id="tara", mode="one_to_one", emotion_hint="warm"
            )
            service = ChatService(
                settings=Settings(memory_enabled=False, reflection_enabled=False),
                ollama_client=FakeOllamaClient(),  # type: ignore[arg-type]
            )
            request = ChatRequest(
                stream=False,
                tts_context=tts_context,
                messages=[ChatMessage(role="user", content="Say hi.")],
            )

            response = await service.chat(request, request_id="req-tts-context")

            self.assertEqual(response.tts_context, tts_context)
            self.assertIsNotNone(response.tts_text)
            self.assertIsNotNone(response.voice_id)
            self.assertIsNotNone(response.emotion)
            self.assertNotIn("<", response.message.content)

        asyncio.run(run_test())

    def test_stream_done_frame_echoes_tts_context(self) -> None:
        async def run_test() -> None:
            tts_context = TTSContext(character_id="tara", is_narration=True, mode="rpg")
            service = ChatService(
                settings=Settings(memory_enabled=False, reflection_enabled=False),
                ollama_client=FakeOllamaClient(),  # type: ignore[arg-type]
            )
            request = ChatRequest(
                stream=True,
                tts_context=tts_context,
                messages=[ChatMessage(role="user", content="Describe the room.")],
            )

            frames = [
                frame
                async for frame in await service.stream_chat(
                    request, request_id="req-stream-tts-context"
                )
            ]

            done_payload = json.loads(frames[-1].split("data: ", 1)[1])
            self.assertEqual(done_payload["tts_context"], tts_context.model_dump())
            self.assertIn("tts_text", done_payload)
            self.assertIn("voice_id", done_payload)
            self.assertIn("emotion", done_payload)
            self.assertNotIn("<", done_payload["text"])

        asyncio.run(run_test())

    def test_stream_strips_model_emotion_tags_from_visible_chunks(self) -> None:
        class TaggedOllamaClient(FakeOllamaClient):
            async def stream_chat(
                self, request: ChatRequest, *, request_id: str | None = None
            ):
                self.requests.append(request)
                yield 'event: message\ndata: {"content": "<wh", "request_id": "req-stream"}\n\n'
                yield 'event: message\ndata: {"content": "isper>I trust ", "request_id": "req-stream"}\n\n'
                yield 'event: message\ndata: {"content": "you <moan>deeply.", "request_id": "req-stream"}\n\n'
                yield 'event: done\ndata: {"done": true, "request_id": "req-stream"}\n\n'

        async def run_test() -> None:
            service = ChatService(
                settings=Settings(memory_enabled=False, reflection_enabled=False),
                ollama_client=TaggedOllamaClient(),  # type: ignore[arg-type]
            )
            request = ChatRequest(
                stream=True,
                tts_context=TTSContext(emotion_hint="intimate", intensity=1.5),
                messages=[ChatMessage(role="user", content="Stay close to me.")],
            )

            frames = [
                frame
                async for frame in await service.stream_chat(
                    request, request_id="req-stream-tags"
                )
            ]

            visible_text = "".join(
                json.loads(frame.split("data: ", 1)[1])["content"]
                for frame in frames
                if "event: message" in frame
            )
            done_payload = json.loads(frames[-1].split("data: ", 1)[1])

            self.assertEqual(visible_text, "I trust you deeply.")
            self.assertNotIn("<", done_payload["text"])
            self.assertIn("<", done_payload["tts_text"])
            self.assertTrue(done_payload["emotion"]["tags"])

        asyncio.run(run_test())


if __name__ == "__main__":
    unittest.main()
