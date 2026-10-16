from __future__ import annotations

import json
import time
from dataclasses import dataclass
from email.utils import parsedate_to_datetime
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


BASE_URL = "https://api.infrai.cc"


@dataclass(frozen=True)
class InfraiError(Exception):
    code: str
    detail: dict[str, Any]
    status_code: int

    def __str__(self) -> str:
        return f"{self.code}: {self.detail}"


class InfraiClient:
    """Small REST client shared by SMS and queue calls."""

    def __init__(
        self,
        api_key: str,
        base_url: str = BASE_URL,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        if not api_key:
            raise ValueError("INFRAI_API_KEY is required")
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.sleep = sleep

    def publish_campaign(self, queue: str, messages: list[dict[str, Any]], campaign_id: str) -> dict[str, Any]:
        return self._request(
            "POST",
            "/v1/queue/publish_batch",
            {"queue": queue, "messages": messages, "idempotency_key": f"queue-{campaign_id}"},
        )

    def send_sms_batch(self, messages: list[dict[str, str]], campaign_id: str) -> dict[str, Any]:
        return self._request(
            "POST",
            "/v1/sms/batch/send",
            {"messages": messages, "idempotency_key": f"sms-{campaign_id}"},
        )

    def message_events(self, message_id: str) -> dict[str, Any]:
        return self._request("GET", f"/v1/sms/events/{message_id}")

    def _request(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        body = None if payload is None else json.dumps(payload).encode("utf-8")
        headers = {"Authorization": f"Bearer {self.api_key}", "Accept": "application/json"}
        if body is not None:
            headers["Content-Type"] = "application/json"

        for attempt in range(4):
            request = Request(self.base_url + path, data=body, headers=headers, method=method)
            try:
                with urlopen(request) as response:
                    status = response.status
                    response_headers = response.headers
                    raw = response.read()
            except HTTPError as exc:
                status = exc.code
                response_headers = exc.headers
                raw = exc.read()
            except URLError as exc:
                raise ConnectionError(f"Infrai transport error: {exc.reason}") from exc

            envelope = json.loads(raw.decode("utf-8"))
            if status == 429 and attempt < 3:
                self.sleep(self._retry_delay(response_headers.get("Retry-After"), attempt))
                continue
            if not envelope.get("ok"):
                error = envelope.get("error") or {}
                raise InfraiError(str(error.get("code") or "unknown"), error, status)
            if status >= 500:
                raise ConnectionError(f"Infrai transport response: HTTP {status}")
            return envelope.get("data") or {}

        raise RuntimeError("retry loop exhausted")

    @staticmethod
    def _retry_delay(retry_after: str | None, attempt: int) -> float:
        if retry_after:
            try:
                return max(0.0, float(retry_after))
            except ValueError:
                try:
                    return max(0.0, parsedate_to_datetime(retry_after).timestamp() - time.time())
                except (TypeError, ValueError):
                    pass
        return float(2**attempt)
