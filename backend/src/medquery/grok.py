from __future__ import annotations

from asyncio import to_thread
from typing import Any
import json

import httpx

from medquery.config import Settings


class GrokChatClient:
    """调用用户提供的 OpenAI-compatible Grok 中转站。"""

    def __init__(self, settings: Settings) -> None:
        self._base_url = settings.grok_base_url.rstrip("/")
        self._api_key = settings.grok_api_key.get_secret_value()
        self._model = settings.grok_model

    async def complete_json(
        self,
        system_prompt: str,
        payload: dict[str, object],
    ) -> dict[str, Any]:
        return await to_thread(self._complete_json, system_prompt, payload)

    def _complete_json(
        self,
        system_prompt: str,
        payload: dict[str, object],
    ) -> dict[str, Any]:
        request_body = {
            "model": self._model,
            "temperature": 0,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": json.dumps(payload, ensure_ascii=False),
                },
            ],
        }
        with httpx.Client(timeout=None) as client:
            response = client.post(
                f"{self._base_url}/chat/completions",
                json=request_body,
                headers={"Authorization": f"Bearer {self._api_key}"},
            )
            response.raise_for_status()
            response_payload = response.json()
        content = response_payload["choices"][0]["message"]["content"]
        return json.loads(content)
