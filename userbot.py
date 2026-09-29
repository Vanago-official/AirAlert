import asyncio
import logging
import os
from collections import deque
from typing import Awaitable, Callable

from pyrogram import Client

from ai import ThreatAnalyzer, ThreatLevel

logger = logging.getLogger(__name__)

OnEventCallback = Callable[[], Awaitable[None]]


class ChannelMonitor:
    """
    Monitors Telegram channels via Pyrogram (userbot).
    Uses polling via get_chat_history.
    Analyzes new messages using ThreatAnalyzer when detected.
    """

    def __init__(
        self,
        api_id: str,
        api_hash: str,
        channels: list[int],
        analyzer: ThreatAnalyzer,
        history_size: int = 10,
        poll_interval: int = 5,
    ):
        self._channels = channels
        self._analyzer = analyzer
        self._history_size = history_size
        self._poll_interval = poll_interval
        self._listening = False

        self._message_history: dict[int, deque[str]] = {
            ch: deque(maxlen=history_size) for ch in channels
        }
        self._last_message_id: dict[int, int] = {ch: 0 for ch in channels}

        self._on_threat: OnEventCallback | None = None
        self._on_clear: OnEventCallback | None = None

        session_string = os.getenv("PYRO_SESSION")
        if not session_string:
            raise RuntimeError(
                "PYRO_SESSION не задано в .env. Спочатку запусти qr_login.py."
            )

        self._client = Client(
            name="balistika_userbot",
            api_id=int(api_id),
            api_hash=api_hash,
            session_string=session_string,
            in_memory=True,
        )

        self._poll_task: asyncio.Task | None = None

    # --- Public API ---

    def on_threat(self, callback: OnEventCallback):
        self._on_threat = callback

    def on_clear(self, callback: OnEventCallback):
        self._on_clear = callback

    async def start(self):
        """Starts the userbot and begins polling channels."""
        await self._client.start()
        logger.info(f"[USERBOT] Connected. Monitoring channels: {self._channels}")

        # З session_string кеш пірів порожній: прохід по діалогах його заповнює
        async for _ in self._client.get_dialogs():
            pass

        await self._init_last_message_ids()

        self._poll_task = asyncio.create_task(self._poll_loop())
        logger.info("[USERBOT] Polling started. Waiting for activation...")

    async def stop(self):
        if self._poll_task:
            self._poll_task.cancel()
        await self._client.stop()
        logger.info("[USERBOT] Stopped.")

    async def set_listening(self, active: bool):
        if active and not self._listening:
            logger.info("[USERBOT] Listening ACTIVATED")
            await self._fetch_recent_messages()
        elif not active and self._listening:
            logger.info("[USERBOT] Listening DEACTIVATED")
        self._listening = active

    # --- Private ---

    async def _init_last_message_ids(self):
        for ch in self._channels:
            try:
                async for msg in self._client.get_chat_history(ch, limit=1):
                    self._last_message_id[ch] = msg.id
                    logger.info(f"[USERBOT] Channel {ch}: last message id = {msg.id}")
            except Exception as e:
                logger.error(f"[USERBOT] Failed to init channel {ch}: {e}")

    async def _fetch_recent_messages(self):
        for ch in self._channels:
            try:
                self._message_history[ch].clear()
                messages = []
                async for msg in self._client.get_chat_history(
                    ch, limit=self._history_size
                ):
                    text = msg.text or msg.caption or ""
                    if text.strip():
                        messages.append((msg.id, text))

                messages.reverse()

                for msg_id, text in messages:
                    self._message_history[ch].append(text)
                    self._last_message_id[ch] = max(self._last_message_id[ch], msg_id)

                logger.info(f"[USERBOT] Fetched {len(messages)} recent messages from {ch}")
            except Exception as e:
                logger.error(f"[USERBOT] Failed to fetch messages from {ch}: {e}")

    async def _poll_loop(self):
        while True:
            await asyncio.sleep(self._poll_interval)

            if not self._listening:
                continue

            for ch in self._channels:
                try:
                    await self._process_channel(ch)
                except Exception as e:
                    logger.error(f"[USERBOT] Polling error for channel {ch}: {e}")

    async def _process_channel(self, channel_id: int):
        new_messages = []
        async for msg in self._client.get_chat_history(channel_id, limit=10):
            if msg.id <= self._last_message_id[channel_id]:
                break
            text = msg.text or msg.caption or ""
            if text.strip():
                new_messages.append((msg.id, text))

        if not new_messages:
            return

        new_messages.reverse()
        self._last_message_id[channel_id] = new_messages[-1][0]

        for msg_id, text in new_messages:
            self._message_history[channel_id].append(text)
            logger.info(f"[USERBOT] New message in {channel_id} (id={msg_id}): {text[:80]}...")

        if not self._listening:
            return

        history = list(self._message_history[channel_id])

        try:
            result = await asyncio.to_thread(self._analyzer.analyze, history)
            logger.info(f"[USERBOT] Gemini result: {result}")

            if result == ThreatLevel.THREAT and self._on_threat:
                await self._on_threat()
            elif result == ThreatLevel.CLEAR and self._on_clear:
                await self._on_clear()
        except Exception as e:
            logger.error(f"[USERBOT] Gemini analysis error: {e}")
