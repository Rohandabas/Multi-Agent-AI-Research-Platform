"""
GeminiTool — the single point for all Gemini API calls.
Tracks tokens and cost per call. Never call Gemini directly from agents.
"""
from __future__ import annotations

import json
import re
import time
from typing import Optional

import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold

from app.tools.base import BaseLLMTool
from app.config.settings import settings
from app.config.constants import (
    LLM_TEMPERATURE,
    MAX_OUTPUT_TOKENS,
    GEMINI_FLASH_INPUT_PRICE_PER_1M,
    GEMINI_FLASH_OUTPUT_PRICE_PER_1M,
)

# Configure Gemini
genai.configure(api_key=settings.GOOGLE_API_KEY)

# Safety settings — permissive for research content
_SAFETY = {
    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
}


class GeminiTool(BaseLLMTool):
    """
    Wraps google-generativeai for text generation and embeddings.
    All LLM calls go through here — tokens and cost are tracked.
    """

    def __init__(
        self,
        model: str = None,
        embedding_model: str = None,
    ):
        self.model_name = model or settings.GEMINI_MODEL
        self.embedding_model_name = embedding_model or settings.EMBEDDING_MODEL
        self._model = genai.GenerativeModel(
            model_name=self.model_name,
            safety_settings=_SAFETY,
        )
        # Running session totals
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_cost_usd = 0.0

    # ─── Text generation ──────────────────────────────────────────────────────

    async def generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        json_mode: bool = False,
    ) -> tuple[str, int, int]:
        """
        Generate text via Gemini with automatic fallback and retry on rate limits.
        Returns: (response_text, input_tokens, output_tokens)
        """
        temp = temperature if temperature is not None else LLM_TEMPERATURE
        max_tok = max_tokens or MAX_OUTPUT_TOKENS

        generation_config = genai.GenerationConfig(
            temperature=temp,
            max_output_tokens=max_tok,
            response_mime_type="application/json" if json_mode else "text/plain",
        )

        # Build full prompt
        full_prompt = f"{system}\n\n{prompt}" if system else prompt

        primary_model = self.model_name
        if not primary_model.startswith("models/"):
            primary_model = f"models/{primary_model}"

        candidates = [primary_model]
        fallbacks = [
            "models/gemini-2.0-flash-lite",
            "models/gemini-2.5-flash",
            "models/gemini-3.5-flash",
            "models/gemini-2.0-flash"
        ]
        for f in fallbacks:
            if f not in candidates:
                candidates.append(f)

        from google.api_core import exceptions as google_exceptions
        import asyncio

        last_error = None
        for model_candidate in candidates:
            model_instance = genai.GenerativeModel(
                model_name=model_candidate,
                safety_settings=_SAFETY,
            )

            max_retries = 3
            for attempt in range(1, max_retries + 1):
                try:
                    response = await model_instance.generate_content_async(
                        full_prompt,
                        generation_config=generation_config,
                    )

                    text = response.text or ""

                    # Track token usage
                    input_tokens = 0
                    output_tokens = 0
                    if hasattr(response, "usage_metadata") and response.usage_metadata:
                        input_tokens = response.usage_metadata.prompt_token_count or 0
                        output_tokens = response.usage_metadata.candidates_token_count or 0

                    cost = self._calculate_cost(input_tokens, output_tokens)
                    self.total_input_tokens += input_tokens
                    self.total_output_tokens += output_tokens
                    self.total_cost_usd += cost

                    # Stick to the working model
                    self.model_name = model_candidate
                    self._model = model_instance

                    return text, input_tokens, output_tokens
                except google_exceptions.ResourceExhausted as e:
                    last_error = e
                    sleep_time = min(2 * attempt, 6)
                    print(f"[*] Gemini model {model_candidate} rate limited. Retrying in {sleep_time}s... (Attempt {attempt}/{max_retries})")
                    await asyncio.sleep(sleep_time)
                except Exception as e:
                    last_error = e
                    print(f"[*] Gemini model {model_candidate} call failed: {e}")
                    break

        if last_error:
            raise last_error
        raise RuntimeError("All Gemini model generation attempts failed.")

    async def generate_json(
        self,
        prompt: str,
        system: Optional[str] = None,
        temperature: Optional[float] = None,
    ) -> tuple[dict, int, int]:
        """
        Generate structured JSON response.
        Returns: (parsed_dict, input_tokens, output_tokens)
        """
        text, in_tok, out_tok = await self.generate(
            prompt, system=system, temperature=temperature, json_mode=True
        )
        try:
            # Strip markdown code blocks if present
            clean = re.sub(r"```(?:json)?\s*|\s*```", "", text).strip()
            return json.loads(clean), in_tok, out_tok
        except json.JSONDecodeError:
            # Fallback: try to extract JSON from the text
            match = re.search(r"\{.*\}", text, re.DOTALL)
            if match:
                return json.loads(match.group()), in_tok, out_tok
            raise ValueError(f"Could not parse JSON from Gemini response: {text[:200]}")

    # ─── Embeddings ───────────────────────────────────────────────────────────

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """
        Generate embeddings using Gemini text-embedding-004.
        Processes in batches of 100 (API limit).
        """
        if not texts:
            return []

        all_embeddings = []
        batch_size = 100

        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            result = genai.embed_content(
                model=self.embedding_model_name,
                content=batch,
                task_type="retrieval_document",
            )
            all_embeddings.extend(result["embedding"])

        return all_embeddings

    async def embed_query(self, text: str) -> list[float]:
        """Embed a single query string (uses retrieval_query task type)."""
        result = genai.embed_content(
            model=self.embedding_model_name,
            content=text,
            task_type="retrieval_query",
        )
        return result["embedding"]

    # ─── Run (BaseTool interface) ──────────────────────────────────────────────

    async def run(self, prompt: str, **kwargs) -> str:
        text, _, _ = await self.generate(prompt, **kwargs)
        return text

    # ─── Cost calculation ─────────────────────────────────────────────────────

    def _calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        input_cost = (input_tokens / 1_000_000) * GEMINI_FLASH_INPUT_PRICE_PER_1M
        output_cost = (output_tokens / 1_000_000) * GEMINI_FLASH_OUTPUT_PRICE_PER_1M
        return input_cost + output_cost

    def get_session_cost(self) -> dict:
        return {
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "total_tokens": self.total_input_tokens + self.total_output_tokens,
            "total_cost_usd": round(self.total_cost_usd, 6),
        }
