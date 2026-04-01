from __future__ import annotations

import json
import platform
import socket
import uuid
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from trainer.config import RimBridgeBackendConfig
from trainer.environment.errors import BackendConnectionError, BackendProtocolError


class RimBridgeClient:
    """Direct GABP client for RimBridgeServer standalone mode."""

    def __init__(self, settings: RimBridgeBackendConfig) -> None:
        self.settings = settings
        self._socket: socket.socket | None = None
        self._stream = None
        self.session_info: dict[str, Any] = {}
        self.runtime_config: dict[str, Any] = {}

    def close(self) -> None:
        if self._stream is not None:
            try:
                self._send_request("session/goodbye", {})
            except Exception:
                pass
            self._stream.close()
            self._stream = None
        if self._socket is not None:
            self._socket.close()
            self._socket = None

    def connect(self) -> dict[str, Any]:
        runtime_config = self._load_runtime_config()
        host, port, token = self._resolve_connection_details(runtime_config)
        if port is None:
            raise BackendConnectionError(
                "RimBridgeServer port is not configured. Set backends.rimbridge.port or provide a GABP bridge config file."
            )
        if not token:
            raise BackendConnectionError(
                "RimBridgeServer token is not configured. Set backends.rimbridge.token or provide a GABP bridge config file."
            )

        try:
            self._socket = socket.create_connection((host, port), timeout=self.settings.timeout_seconds)
            self._socket.settimeout(self.settings.timeout_seconds)
            self._stream = self._socket.makefile("rwb")
        except OSError as exc:
            raise BackendConnectionError(f"Failed to connect to RimBridgeServer at {host}:{port}: {exc}") from exc

        hello = {
            "token": token,
            "bridgeVersion": self.settings.bridge_version,
            "platform": platform.system().lower(),
            "launchId": self.settings.launch_id or runtime_config.get("metadata", {}).get("launchId") or str(uuid.uuid4()),
        }
        welcome = self._send_request("session/hello", hello)
        if not isinstance(welcome, Mapping):
            raise BackendProtocolError("RimBridgeServer returned an unexpected session/welcome payload.")

        self.runtime_config = runtime_config
        self.session_info = dict(welcome)
        return dict(welcome)

    def list_tools(self) -> list[dict[str, Any]]:
        result = self._send_request("tools/list", {})
        if isinstance(result, Mapping):
            tools = result.get("tools", result.get("items", result))
            if isinstance(tools, Sequence) and not isinstance(tools, (str, bytes, bytearray)):
                return [dict(tool) if isinstance(tool, Mapping) else {"name": str(tool)} for tool in tools]
        if isinstance(result, Sequence) and not isinstance(result, (str, bytes, bytearray)):
            return [dict(tool) if isinstance(tool, Mapping) else {"name": str(tool)} for tool in result]
        raise BackendProtocolError("RimBridgeServer tools/list returned an unsupported payload shape.")

    def call_tool(self, name: str, arguments: Mapping[str, Any] | None = None) -> Any:
        payloads = (
            {"name": name, "arguments": dict(arguments or {})},
            {"tool": name, "arguments": dict(arguments or {})},
            {"toolName": name, "arguments": dict(arguments or {})},
        )
        last_error: BackendProtocolError | None = None
        for payload in payloads:
            try:
                result = self._send_request("tools/call", payload)
                return self._unwrap_tool_result(result)
            except BackendProtocolError as exc:
                last_error = exc
        raise last_error or BackendProtocolError(f"Unable to call RimBridgeServer tool '{name}'.")

    def get_bridge_status(self) -> dict[str, Any]:
        return self._coerce_mapping(self.call_tool("rimbridge/get_bridge_status"))

    def get_game_info(self) -> dict[str, Any]:
        return self._coerce_mapping(self.call_tool("rimworld/get_game_info"))

    def list_capabilities(self) -> list[dict[str, Any]]:
        result = self.call_tool("rimbridge/list_capabilities", {"limit": 200, "includeParameters": True})
        if isinstance(result, Mapping):
            items = result.get("capabilities", result.get("items", result.get("data", result)))
            if isinstance(items, Sequence) and not isinstance(items, (str, bytes, bytearray)):
                return [dict(item) if isinstance(item, Mapping) else {"id": str(item)} for item in items]
        if isinstance(result, Sequence) and not isinstance(result, (str, bytes, bytearray)):
            return [dict(item) if isinstance(item, Mapping) else {"id": str(item)} for item in result]
        return []

    def list_colonists(self) -> list[dict[str, Any]]:
        result = self.call_tool("rimworld/list_colonists", {"currentMapOnly": False})
        if isinstance(result, Mapping):
            items = result.get("colonists", result.get("items", result.get("data", result)))
            if isinstance(items, Sequence) and not isinstance(items, (str, bytes, bytearray)):
                return [dict(item) if isinstance(item, Mapping) else {"name": str(item)} for item in items]
        if isinstance(result, Sequence) and not isinstance(result, (str, bytes, bytearray)):
            return [dict(item) if isinstance(item, Mapping) else {"name": str(item)} for item in result]
        return []

    def list_alerts(self) -> list[dict[str, Any]]:
        result = self.call_tool("rimworld/list_alerts", {"limit": 40})
        if isinstance(result, Mapping):
            items = result.get("alerts", result.get("items", result.get("data", result)))
            if isinstance(items, Sequence) and not isinstance(items, (str, bytes, bytearray)):
                return [dict(item) if isinstance(item, Mapping) else {"label": str(item)} for item in items]
        if isinstance(result, Sequence) and not isinstance(result, (str, bytes, bytearray)):
            return [dict(item) if isinstance(item, Mapping) else {"label": str(item)} for item in result]
        return []

    def list_messages(self) -> list[dict[str, Any]]:
        result = self.call_tool("rimworld/list_messages", {"limit": 12})
        if isinstance(result, Mapping):
            items = result.get("messages", result.get("items", result.get("data", result)))
            if isinstance(items, Sequence) and not isinstance(items, (str, bytes, bytearray)):
                return [dict(item) if isinstance(item, Mapping) else {"text": str(item)} for item in items]
        if isinstance(result, Sequence) and not isinstance(result, (str, bytes, bytearray)):
            return [dict(item) if isinstance(item, Mapping) else {"text": str(item)} for item in result]
        return []

    def pause_game(self, pause: bool = True) -> Any:
        return self.call_tool("rimworld/pause_game", {"pause": pause})

    def set_time_speed(self, speed: str) -> Any:
        return self.call_tool("rimworld/set_time_speed", {"speed": speed})

    def start_debug_game(self) -> Any:
        return self.call_tool("rimworld/start_debug_game")

    def go_to_main_menu(self) -> Any:
        return self.call_tool("rimworld/go_to_main_menu")

    def _load_runtime_config(self) -> dict[str, Any]:
        config_path = self.settings.expanded_config_path
        if config_path is None or not config_path.exists():
            return {}
        try:
            return json.loads(config_path.read_text(encoding="utf-8"))
        except OSError as exc:
            raise BackendConnectionError(f"Failed to read RimBridgeServer config file at {config_path}: {exc}") from exc
        except json.JSONDecodeError as exc:
            raise BackendProtocolError(f"RimBridgeServer config file at {config_path} is not valid JSON.") from exc

    def _resolve_connection_details(self, runtime_config: Mapping[str, Any]) -> tuple[str, int | None, str | None]:
        host, port = self.settings.resolve_host_port()
        token = self.settings.token

        transport = runtime_config.get("transport")
        if isinstance(transport, Mapping) and str(transport.get("type", "")).lower() == "tcp":
            address = str(transport.get("address") or "").strip()
            if address.isdigit():
                port = int(address)
        if token is None:
            runtime_token = runtime_config.get("token")
            token = str(runtime_token) if runtime_token else None

        return host, port, token

    def _send_request(self, method: str, params: Mapping[str, Any] | None = None) -> Any:
        if self._stream is None:
            raise BackendConnectionError("RimBridgeServer connection is not open.")

        message_id = str(uuid.uuid4())
        envelope = {
            "v": "gabp/1",
            "id": message_id,
            "type": "request",
            "method": method,
            "params": dict(params or {}),
        }
        body = json.dumps(envelope, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
        headers = (
            f"Content-Length: {len(body)}\r\n"
            "Content-Type: application/json\r\n"
            "\r\n"
        ).encode("ascii")
        self._stream.write(headers)
        self._stream.write(body)
        self._stream.flush()

        while True:
            message = self._read_message()
            if message.get("type") == "event":
                continue
            if message.get("id") != message_id:
                continue
            if "error" in message:
                error = message["error"]
                if isinstance(error, Mapping):
                    code = error.get("code")
                    detail = error.get("message") or error.get("detail") or error
                    raise BackendProtocolError(f"GABP {method} failed with code {code}: {detail}")
                raise BackendProtocolError(f"GABP {method} failed: {error}")
            if "result" not in message:
                raise BackendProtocolError(f"GABP {method} response did not include a result payload.")
            return message["result"]

    def _read_message(self) -> dict[str, Any]:
        if self._stream is None:
            raise BackendConnectionError("RimBridgeServer connection is not open.")

        headers: dict[str, str] = {}
        while True:
            line = self._stream.readline()
            if not line:
                raise BackendConnectionError("RimBridgeServer closed the connection unexpectedly.")
            if line == b"\r\n":
                break
            decoded = line.decode("ascii", errors="replace").strip()
            if ":" not in decoded:
                raise BackendProtocolError(f"Invalid GABP frame header: {decoded!r}")
            key, value = decoded.split(":", 1)
            headers[key.lower()] = value.strip()

        try:
            content_length = int(headers["content-length"])
        except (KeyError, ValueError) as exc:
            raise BackendProtocolError("GABP frame is missing a valid Content-Length header.") from exc

        body = self._stream.read(content_length)
        if len(body) != content_length:
            raise BackendProtocolError("GABP frame ended before the declared Content-Length was read.")

        try:
            payload = json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise BackendProtocolError("GABP frame body was not valid UTF-8 JSON.") from exc
        if not isinstance(payload, Mapping):
            raise BackendProtocolError("GABP frame body must decode to a JSON object.")
        return dict(payload)

    def _unwrap_tool_result(self, result: Any) -> Any:
        if not isinstance(result, Mapping):
            return result

        for key in ("result", "data", "payload", "content"):
            if key in result:
                value = result[key]
                if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
                    if len(value) == 1 and isinstance(value[0], Mapping):
                        nested = value[0]
                        if "text" in nested:
                            try:
                                return json.loads(str(nested["text"]))
                            except json.JSONDecodeError:
                                return dict(nested)
                    return value
                if isinstance(value, Mapping):
                    return dict(value)
                return value

        if "text" in result:
            text = str(result["text"])
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                return text

        return dict(result)

    def _coerce_mapping(self, value: Any) -> dict[str, Any]:
        if isinstance(value, Mapping):
            return dict(value)
        raise BackendProtocolError(f"Expected a mapping payload from RimBridgeServer, got {type(value).__name__}.")
