"""
GroqTool — wraps the Groq Cloud API for fast, cheap text generation.
Uses standard HTTP POST requests to Groq's OpenAI-compatible endpoint.
Tracks tokens and cost per call.
"""
from __future__ import annotations

import json
import re
import time
import asyncio
from typing import Optional

import httpx

from app.tools.base import BaseLLMTool
from app.config.settings import settings
from app.config.constants import (
    LLM_TEMPERATURE,
    MAX_OUTPUT_TOKENS,
    GROQ_LLAMA_INPUT_PRICE_PER_1M,
    GROQ_LLAMA_OUTPUT_PRICE_PER_1M,
)


class GroqTool(BaseLLMTool):
    """
    Wraps Groq Cloud API via httpx for fast text generation.
    Tracks session totals for input tokens, output tokens, and USD cost.
    """

    def __init__(self, model: str = None):
        self.model_name = model or settings.GROQ_MODEL
        self.api_key = settings.GROQ_API_KEY
        self.api_url = "https://api.groq.com/openai/v1/chat/completions"

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
        Generate text via Groq's chat completions endpoint.
        Returns: (response_text, input_tokens, output_tokens)
        """
        if not self.api_key:
            raise ValueError("GROQ_API_KEY is not configured in settings or .env file.")

        temp = temperature if temperature is not None else LLM_TEMPERATURE
        max_tok = max_tokens or MAX_OUTPUT_TOKENS

        # Groq's chat completions message format
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.model_name,
            "messages": messages,
            "temperature": temp,
            "max_tokens": max_tok,
        }
        print(f"[*] Groq payload: json_mode={json_mode}, keys={list(payload.keys())}")

        if json_mode:
            payload["response_format"] = {"type": "json_object"}
            # Groq JSON mode requires the system/user prompt to mention JSON explicitly.
            # We append a reminder to prompt if not present.
            if "json" not in prompt.lower() and (not system or "json" not in system.lower()):
                messages[-1]["content"] = prompt + "\n\nReturn ONLY valid JSON."

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        max_retries = 5
        backoff_factor = 2.0
        initial_delay = 2.0
        res_data = {}

        for attempt in range(1, max_retries + 1):
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        self.api_url,
                        json=payload,
                        headers=headers,
                        timeout=60.0,
                    )
                    
                    if response.status_code == 429:
                        # Extract Retry-After if present
                        retry_after = response.headers.get("Retry-After")
                        if retry_after:
                            try:
                                delay = float(retry_after)
                            except ValueError:
                                delay = initial_delay * (backoff_factor ** (attempt - 1))
                        else:
                            delay = initial_delay * (backoff_factor ** (attempt - 1))
                        
                        if delay > 20.0:
                            print(f"[*] Groq API rate limit Retry-After ({delay:.2f}s) is too high. Raising exception immediately.")
                            raise RuntimeError(f"Groq API 429 Rate Limit: retry delay of {delay:.2f}s is too high.")
                        
                        print(f"[*] Groq API 429 rate limit hit. Retrying in {delay:.2f}s... (Attempt {attempt}/{max_retries})")
                        await asyncio.sleep(delay)
                        continue
                        
                    response.raise_for_status()
                    res_data = response.json()
                    break
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429:
                    delay = initial_delay * (backoff_factor ** (attempt - 1))
                    print(f"[*] Groq API 429 rate limit hit. Retrying in {delay:.2f}s... (Attempt {attempt}/{max_retries})")
                    await asyncio.sleep(delay)
                    continue
                print(f"[ERROR] Groq API error {e.response.status_code}: {e.response.text}")
                raise
            except (httpx.RequestError, asyncio.TimeoutError) as e:
                if attempt == max_retries:
                    raise
                delay = initial_delay * (backoff_factor ** (attempt - 1))
                print(f"[*] Request error: {e}. Retrying in {delay:.2f}s... (Attempt {attempt}/{max_retries})")
                await asyncio.sleep(delay)
        else:
            raise RuntimeError(f"Groq API call failed after {max_retries} retries due to rate limits.")

        text = res_data["choices"][0]["message"]["content"] or ""

        # Track token usage from response
        usage = res_data.get("usage", {})
        input_tokens = usage.get("prompt_tokens", 0)
        output_tokens = usage.get("completion_tokens", 0)

        cost = self._calculate_cost(input_tokens, output_tokens)
        self.total_input_tokens += input_tokens
        self.total_output_tokens += output_tokens
        self.total_cost_usd += cost

        return text, input_tokens, output_tokens

    async def generate_json(
        self,
        prompt: str,
        system: Optional[str] = None,
        temperature: Optional[float] = None,
    ) -> tuple[dict, int, int]:
        """
        Generate structured JSON response via Groq.
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
            raise ValueError(f"Could not parse JSON from Groq response: {text[:200]}")

    # ─── Embeddings ───────────────────────────────────────────────────────────

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Groq does not support embeddings. Embedding is delegated to GeminiEmbedder."""
        raise NotImplementedError("GroqTool does not support embeddings directly. Use GeminiTool for embeddings.")

    async def embed_query(self, text: str) -> list[float]:
        """Groq does not support embeddings. Embedding is delegated to GeminiEmbedder."""
        raise NotImplementedError("GroqTool does not support embeddings directly. Use GeminiTool for embeddings.")

    # ─── Run (BaseTool interface) ──────────────────────────────────────────────

    async def run(self, prompt: str, **kwargs) -> str:
        text, _, _ = await self.generate(prompt, **kwargs)
        return text

    # ─── Cost calculation ─────────────────────────────────────────────────────

    def _calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        input_cost = (input_tokens / 1_000_000) * GROQ_LLAMA_INPUT_PRICE_PER_1M
        output_cost = (output_tokens / 1_000_000) * GROQ_LLAMA_OUTPUT_PRICE_PER_1M
        return input_cost + output_cost

    def get_session_cost(self) -> dict:
        return {
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "total_tokens": self.total_input_tokens + self.total_output_tokens,
            "total_cost_usd": round(self.total_cost_usd, 6),
        }
