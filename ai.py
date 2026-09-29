import logging
import os
from enum import Enum

from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

logger = logging.getLogger(__name__)


class ThreatLevel(Enum):
    THREAT = "THREAT"
    CLEAR = "CLEAR"
    IGNORE = "IGNORE"


SYSTEM_PROMPT = """
You are an automated analyzer for air raid operational alerts.
You will be provided with a history of recent messages.
Your goal is to analyze the LATEST message in the context of the previous ones and return exactly ONE status word.

Status determination rules:
1. THREAT — if the latest message warns about a BALLISTIC or MISSILE threat (missiles, ballistics, false targets, etc.). For example: "ballistic threat", "launches", "missiles", "still flying", "take cover", "heading to...".
2. CLEAR — if the latest message indicates the danger has passed. For example: "clear", "all clear", "skies are clear".
3. IGNORE — if there is NO NEW threat in the latest message (ads, summaries), or if the threat is NOT related to missiles/ballistics (e.g., only UAVs/drones are flying).

Important:
- Focus on the LATEST message, but consider previous ones for context.
- Reply ONLY with a single word: THREAT, CLEAR, or IGNORE. No punctuation or explanations.
"""


class ThreatAnalyzer:
    """Threat analyzer based on Gemini API."""

    def __init__(self, model: str = "gemini-2.5-flash", system_prompt: str = SYSTEM_PROMPT):
        self._client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        self._model = model
        self._system_prompt = system_prompt

    def analyze(self, message_history: list[str]) -> ThreatLevel:
        """
        Analyzes message history and returns the threat level.

        :param message_history: List of messages (from oldest to newest).
        :return: ThreatLevel.THREAT, ThreatLevel.CLEAR, or ThreatLevel.IGNORE
        """
        if not message_history:
            return ThreatLevel.IGNORE

        history_text = "\n".join([f"[{i+1}] {msg}" for i, msg in enumerate(message_history)])
        prompt = f"Message history:\n{history_text}\n\nAnalyze the latest message."

        try:
            response = self._client.models.generate_content(
                model=self._model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=self._system_prompt,
                    temperature=0.0,
                ),
            )

            result = response.text.strip().upper()

            try:
                return ThreatLevel(result)
            except ValueError:
                logger.warning(f"[AI WARNING] Unexpected response from Gemini: {result}")
                return ThreatLevel.IGNORE

        except Exception as e:
            logger.error(f"[AI ERROR] Failed to query Gemini: {e}")
            return ThreatLevel.IGNORE
