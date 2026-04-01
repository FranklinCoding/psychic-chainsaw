from __future__ import annotations

from collections.abc import Mapping
from typing import Any
from urllib.parse import urljoin

import requests

from trainer.config import RimAPIBackendConfig
from trainer.environment.errors import BackendConnectionError, BackendProtocolError


class RimAPIClient:
    """Thin HTTP client for the RIMAPI REST surface."""

    def __init__(self, settings: RimAPIBackendConfig, session: requests.Session | None = None) -> None:
        self.settings = settings
        self._session = session or requests.Session()
        self._session.headers.update({"Accept": "application/json"})

    def close(self) -> None:
        self._session.close()

    def connect(self) -> dict[str, Any]:
        return self.get_version()

    def get_version(self) -> dict[str, Any]:
        return self._get_data("/api/v1/version")

    def get_game_state(self) -> dict[str, Any]:
        return self._get_data("/api/v1/game/state")

    def get_colonists_detailed(self) -> list[dict[str, Any]]:
        endpoint = "/api/v2/colonists/detailed" if self.settings.prefer_v2_colonists else "/api/v1/colonists/detailed"
        payload = self._get_data(endpoint, allow_not_found=self.settings.prefer_v2_colonists)
        if payload is not None:
            return list(payload)
        return list(self._get_data("/api/v1/colonists/detailed"))

    def get_resources_summary(self) -> dict[str, Any]:
        return self._get_data("/api/v1/resources/summary", params={"map_id": self.settings.map_id})

    def get_research_state(self) -> dict[str, Any] | None:
        for endpoint in (
            "/api/v1/research/current",
            "/api/v2/research/current",
            "/api/v1/research",
            "/api/v2/research",
        ):
            payload = self._get_data(endpoint, allow_not_found=True)
            if payload is not None:
                return payload
        return None

    def set_game_speed(self, speed: int) -> dict[str, Any]:
        return self._post_data("/api/v1/game/speed", params={"speed": speed})

    def start_new_game_devquick(self) -> dict[str, Any]:
        return self._post_data("/api/v1/game/start/devquick")

    def _build_url(self, path: str) -> str:
        base_url = self.settings.base_url.rstrip("/") + "/"
        return urljoin(base_url, path.lstrip("/"))

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: Mapping[str, Any] | None = None,
        json_body: Any = None,
        allow_not_found: bool = False,
    ) -> Any:
        try:
            response = self._session.request(
                method=method,
                url=self._build_url(path),
                params=params,
                json=json_body,
                timeout=self.settings.timeout_seconds,
            )
        except requests.RequestException as exc:
            raise BackendConnectionError(f"Failed to reach RIMAPI at {self.settings.base_url}: {exc}") from exc

        if allow_not_found and response.status_code == 404:
            return None

        try:
            response.raise_for_status()
        except requests.HTTPError as exc:
            body = response.text.strip()
            detail = f" ({body})" if body else ""
            raise BackendConnectionError(
                f"RIMAPI request failed with HTTP {response.status_code} for {path}{detail}"
            ) from exc

        try:
            payload = response.json()
        except ValueError as exc:
            raise BackendProtocolError(f"RIMAPI returned non-JSON payload for {path}") from exc

        if isinstance(payload, Mapping) and payload.get("success") is False:
            errors = payload.get("errors") or []
            warnings = payload.get("warnings") or []
            raise BackendProtocolError(
                f"RIMAPI reported failure for {path}: errors={errors!r} warnings={warnings!r}"
            )

        return payload

    def _unwrap_data(self, payload: Any, path: str) -> Any:
        if isinstance(payload, Mapping):
            if "data" in payload:
                return payload["data"]
            return dict(payload)
        raise BackendProtocolError(f"RIMAPI returned unexpected payload shape for {path}: {type(payload).__name__}")

    def _get_data(
        self,
        path: str,
        *,
        params: Mapping[str, Any] | None = None,
        allow_not_found: bool = False,
    ) -> Any:
        payload = self._request("GET", path, params=params, allow_not_found=allow_not_found)
        if payload is None:
            return None
        return self._unwrap_data(payload, path)

    def _post_data(
        self,
        path: str,
        *,
        params: Mapping[str, Any] | None = None,
        json_body: Any = None,
        allow_not_found: bool = False,
    ) -> Any:
        payload = self._request(
            "POST",
            path,
            params=params,
            json_body=json_body,
            allow_not_found=allow_not_found,
        )
        if payload is None:
            return None
        return self._unwrap_data(payload, path)
