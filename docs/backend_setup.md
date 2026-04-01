# Backend Setup

This project keeps the trainer bridge-agnostic by routing live RimWorld integrations through backend adapters.

## RIMAPI

RIMAPI is configured under `backends.rimapi` in `config/default.yaml`.

Relevant fields:

- `base_url`: RIMAPI server address. The documented default is `http://127.0.0.1:8765`.
- `timeout_seconds`: HTTP timeout for each request.
- `map_id`: map used for resource summary polling.
- `prefer_v2_colonists`: prefer `/api/v2/colonists/detailed` and fall back to `/api/v1/colonists/detailed`.
- `start_new_game_on_reset`: optional opt-in for `reset()` to call `/api/v1/game/start/devquick`.

Implemented now:

- `connect()` via `/api/v1/version`
- `get_capabilities()`
- `get_observation()` from:
  - `/api/v1/game/state`
  - `/api/v1|v2/colonists/detailed`
  - `/api/v1/resources/summary`
  - optional research endpoint probing
- action support for:
  - `wait`
  - `set_speed`
  - `pause`
  - `resume`

Current gaps and graceful degradation:

- work-priority control is reported as unsupported
- research choice is reported as unsupported until there is a stable documented write endpoint
- alert-posture control is reported as unsupported
- unsupported actions return a valid shared observation plus structured `info` instead of leaking backend exceptions into trainer code

Connection check:

- `bash codex/actions/check_rimapi.sh`

## RimBridgeServer

RimBridgeServer direct mode is configured under `backends.rimbridge` in `config/default.yaml`.

Relevant fields:

- `host`: direct GABP host, usually `127.0.0.1`
- `port`: direct GABP TCP port. Optional when `config_path` is available.
- `token`: direct GABP token. Optional when `config_path` is available.
- `config_path`: path to the GABP bridge config file. On Windows the common location is `%APPDATA%\gabp\bridge.json`.
- `transport`: currently `auto` or `tcp`
- `timeout_seconds`: socket timeout for connect and request/response reads
- `bridge_version`: client identifier sent in `session/hello`

Implemented now:

- `connect()` using GABP framing plus `session/hello`
- `get_capabilities()` from:
  - session capability negotiation
  - `tools/list`
  - `rimbridge/list_capabilities`
- `get_observation()` from:
  - `rimbridge/get_bridge_status`
  - `rimworld/get_game_info`
  - `rimworld/list_colonists`
  - `rimworld/list_alerts`
  - `rimworld/list_messages`
- action support for:
  - `wait`
  - `set_speed`
  - `pause`
  - `resume`
  - `request_restart` when both `rimworld/go_to_main_menu` and `rimworld/start_debug_game` are available

Current gaps and graceful degradation:

- resource totals are often not exposed as first-class bridge tools, so `can_read_resources` may be false
- work-priority and research-selection support stay false unless the live bridge surface exposes explicit compatible capabilities
- partial observations are marked in metadata with `partial_observation` and `unavailable_fields`
- failure detection now respects missing read capabilities so partial bridge snapshots do not trigger false starvation/resource failures

Connection check:

- `bash codex/actions/check_rimbridge.sh`

## Profile Selection

Use profiles to switch backends without changing code:

- `python -m trainer.main --profile mock`
- `python -m trainer.main --profile rimapi`
- `python -m trainer.main --profile rimbridge`

The mock profile still works without RimWorld installed.
