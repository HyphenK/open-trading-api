from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import requests

from config import (
    HASHKEY_ENDPOINT,
    MAX_RETRIES,
    REQUEST_TIMEOUT_SECONDS,
    RETRY_BACKOFF_SECONDS,
    TOKEN_CACHE_PATH,
    TOKEN_ENDPOINT,
)


@dataclass
class TokenInfo:
    access_token: str
    expires_at: str
    issued_date: str

    @property
    def expires_at_dt(self) -> datetime:
        return datetime.fromisoformat(self.expires_at)


class AuthManager:
    def __init__(self, base_url: str, app_key: str, app_secret: str, logger: logging.Logger) -> None:
        self.base_url = base_url
        self.app_key = app_key
        self.app_secret = app_secret
        self.logger = logger

    def get_access_token(self) -> str:
        cached = self._load_cached_token()
        if cached and self._is_reusable_today(cached):
            self.logger.info("Token reuse: cached same-day token is valid.")
            return cached.access_token

        self.logger.info("Token refresh: requesting a new access token.")
        token = self._issue_token()
        self._save_cached_token(token)
        return token.access_token

    def get_hashkey(self, payload: dict[str, Any]) -> str:
        url = f"{self.base_url}{HASHKEY_ENDPOINT}"
        headers = {
            "content-type": "application/json",
            "appkey": self.app_key,
            "appsecret": self.app_secret,
        }

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                response = requests.post(url, headers=headers, json=payload, timeout=REQUEST_TIMEOUT_SECONDS)
                response.raise_for_status()
                data = response.json()
                hashkey = data.get("HASH") or data.get("hash")
                if not hashkey:
                    raise RuntimeError(f"Hashkey response missing HASH field: {data}")
                return hashkey
            except Exception as exc:
                self.logger.warning("Hashkey request failed (%s/%s): %s", attempt, MAX_RETRIES, exc)
                if attempt >= MAX_RETRIES:
                    raise
                self._sleep_for_retry(attempt)

        raise RuntimeError("Unreachable hashkey retry exit.")

    def _issue_token(self) -> TokenInfo:
        url = f"{self.base_url}{TOKEN_ENDPOINT}"
        payload = {
            "grant_type": "client_credentials",
            "appkey": self.app_key,
            "appsecret": self.app_secret,
        }
        headers = {"content-type": "application/json"}

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                response = requests.post(url, headers=headers, json=payload, timeout=REQUEST_TIMEOUT_SECONDS)
                response.raise_for_status()
                data = response.json()
                access_token = data["access_token"]
                expires_in = int(data.get("expires_in", 24 * 60 * 60))
                expires_at = datetime.now() + timedelta(seconds=max(expires_in - 60, 60))
                return TokenInfo(
                    access_token=access_token,
                    expires_at=expires_at.isoformat(),
                    issued_date=datetime.now().date().isoformat(),
                )
            except Exception as exc:
                self.logger.warning("Token request failed (%s/%s): %s", attempt, MAX_RETRIES, exc)
                if attempt >= MAX_RETRIES:
                    raise
                self._sleep_for_retry(attempt)

        raise RuntimeError("Unreachable token retry exit.")

    def _load_cached_token(self) -> TokenInfo | None:
        if not TOKEN_CACHE_PATH.exists():
            return None
        try:
            data = json.loads(TOKEN_CACHE_PATH.read_text(encoding="utf-8"))
            return TokenInfo(**data)
        except Exception as exc:
            self.logger.warning("Failed to read token cache. A new token will be requested: %s", exc)
            return None

    def _save_cached_token(self, token_info: TokenInfo) -> None:
        TOKEN_CACHE_PATH.write_text(json.dumps(token_info.__dict__, indent=2), encoding="utf-8")

    @staticmethod
    def _is_reusable_today(token_info: TokenInfo) -> bool:
        today = datetime.now().date().isoformat()
        return token_info.issued_date == today and token_info.expires_at_dt > datetime.now()

    @staticmethod
    def _sleep_for_retry(attempt: int) -> None:
        import time
        time.sleep(RETRY_BACKOFF_SECONDS * attempt)
