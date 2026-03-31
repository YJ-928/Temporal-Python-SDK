"""
Translation Workflow — Activity Definition

Class-based Activities that call a translation microservice (or fall back to
a built-in dictionary) to translate greetings and farewells.

Uses aiohttp for HTTP calls, injected via __init__ for testability.
"""

from __future__ import annotations

import aiohttp
from temporalio import activity

# Import the dataclass shared with the Workflow
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from translation_workflow import TranslationInput


class TranslateActivities:
    """Activities that translate text via a microservice or local map."""

    def __init__(self, session: aiohttp.ClientSession | None = None):
        self._session = session
        self._fallback = {
            "es": {"hello": "Hola", "goodbye": "Adiós"},
            "fr": {"hello": "Bonjour", "goodbye": "Au revoir"},
            "de": {"hello": "Hallo", "goodbye": "Auf Wiedersehen"},
            "pt": {"hello": "Olá", "goodbye": "Adeus"},
        }

    async def _translate(self, term: str, lang: str) -> str:
        """Try the microservice first; fall back to the built-in map."""
        base_url = os.environ.get(
            "TRANSLATION_SERVICE_URL", "http://localhost:9998"
        )
        if self._session:
            try:
                url = f"{base_url}/translate"
                async with self._session.get(
                    url, params={"term": term, "lang": lang}
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return data.get("translation", term)
            except aiohttp.ClientError:
                pass  # fall through to local lookup

        translations = self._fallback.get(lang, {})
        return translations.get(term, term)

    @activity.defn
    async def translate_greeting(self, input: TranslationInput) -> str:
        """Translate 'hello' and compose a greeting."""
        translated = await self._translate("hello", input.language_code)
        result = f"{translated}, {input.name}!"
        activity.logger.info(f"Greeting: {result}")
        return result

    @activity.defn
    async def translate_farewell(self, input: TranslationInput) -> str:
        """Translate 'goodbye' and compose a farewell."""
        translated = await self._translate("goodbye", input.language_code)
        result = f"{translated}, {input.name}!"
        activity.logger.info(f"Farewell: {result}")
        return result
