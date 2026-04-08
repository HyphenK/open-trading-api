from __future__ import annotations

import logging
import time
from typing import Any

import requests

from auth import AuthManager
from config import MAX_RETRIES, REQUEST_TIMEOUT_SECONDS, RETRY_BACKOFF_SECONDS


class APIClient:
    def __init__(self, base_url: str, auth_manager: AuthManager, logger: logging.Logger) -> None:
        self.base_url = base_url.rstrip("/")
        self.auth_manager = auth_manager
        self.logger = logger
        self.session = requests.Session()
        self._last_request_ts = 0.0
        self.min_request_interval = 1.0  # ← 1초 간격

    def get(self, endpoint: str, tr_id: str, params: dict[str, Any]) -> dict[str, Any]:
        return self._request("GET", endpoint, tr_id, params=params)

    def post(self, endpoint: str, tr_id: str, body: dict[str, Any], use_hashkey: bool = False) -> dict[str, Any]:
        return self._request("POST", endpoint, tr_id, body=body, use_hashkey=use_hashkey)

    def _throttle(self):
        now = time.monotonic()
        elapsed = now - self._last_request_ts

        if elapsed < self.min_request_interval:
            time.sleep(self.min_request_interval - elapsed)

        self._last_request_ts = time.monotonic()
    
    def _request(
        self,
        method: str,
        endpoint: str,
        tr_id: str,
        params: dict[str, Any] | None = None,
        body: dict[str, Any] | None = None,
        use_hashkey: bool = False,
    ) -> dict[str, Any]:
        self._throttle()  # ← 추가
        url = f"{self.base_url}{endpoint}"
        token = self.auth_manager.get_access_token()

        headers = {
            "content-type": "application/json; charset=utf-8",
            "authorization": f"Bearer {token}",
            "appkey": self.auth_manager.app_key,
            "appsecret": self.auth_manager.app_secret,
            "tr_id": tr_id,
            "custtype": "P",
        }

        if use_hashkey and body is not None:
            headers["hashkey"] = self.auth_manager.get_hashkey(body)

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                response = self.session.request(
                    method=method,
                    url=url,
                    headers=headers,
                    params=params,
                    json=body,
                    timeout=REQUEST_TIMEOUT_SECONDS,
                )

                if response.status_code in {429, 500, 502, 503, 504}:
                    raise requests.HTTPError(f"Retryable HTTP {response.status_code}: {response.text}")

                response.raise_for_status()
                data = response.json()
                rt_cd = data.get("rt_cd")
                if rt_cd not in (None, "0"):
                    msg1 = data.get("msg1")
                    msg_cd = data.get("msg_cd")
                    raise RuntimeError(f"API business error {msg_cd}: {msg1}")
                return data
            except Exception as exc:
                self.logger.warning(
                    "API request failed (%s %s, attempt %s/%s): %s",
                    method,
                    endpoint,
                    attempt,
                    MAX_RETRIES,
                    exc,
                )
                if attempt >= MAX_RETRIES:
                    self.logger.exception("API request permanently failed: %s %s", method, endpoint)
                    raise
                time.sleep(RETRY_BACKOFF_SECONDS * attempt)

        raise RuntimeError("Unreachable request retry exit.")
