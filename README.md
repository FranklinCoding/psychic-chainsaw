# psychic-chainsaw
RIMWORLD

# RimWorld Agent

Local-only autonomous RimWorld trainer with switchable backends for:

- RIMAPI
- RimBridgeServer

## Goals

- keep the trainer bridge-agnostic
- support both RIMAPI and RimBridgeServer through adapters
- make mock mode runnable even without RimWorld installed
- support repeated runs, failure detection, auto-restart, and checkpointing
- prefer structured game-state bridges over pixel automation

## Initial plan

Version 1 should prioritize:
- shared trainer architecture
- mock backend
- RIMAPI adapter
- RimBridgeServer adapter
- config-driven backend switching
- logging, run summaries, and checkpoint scaffolding

## Current backend status

Implemented now:

- mock mode remains end-to-end and deterministic
- RIMAPI adapter now supports:
  - `connect()`
  - `get_capabilities()`
  - `get_observation()`
  - speed and pause/resume control
- RimBridgeServer adapter now supports:
  - `connect()` through direct GABP framing and `session/hello`
  - `get_capabilities()`
  - `get_observation()`
  - speed and pause/resume control
  - restart requests when the live tool surface exposes both main-menu and debug-start tools

Still intentionally partial:

- no pixel automation
- no trainer rewrite
- no fake "full control" surface where the backend does not expose a clean structured capability
- unsupported backend actions degrade cleanly and return shared observations with structured info

See `docs/backend_setup.md` for backend-specific setup and capability notes.

## Config profiles

Profiles are small YAML overrides applied on top of `config/default.yaml`.
They let us switch between mock, RIMAPI, and RimBridgeServer without changing code,
while keeping shared defaults centralized.

- `config/profiles/mock.yaml` selects `bridge_backend: mock`
- `config/profiles/rimapi.yaml` selects `bridge_backend: rimapi`
- `config/profiles/rimbridge.yaml` selects `bridge_backend: rimbridge`

Run with a profile using:

- `python -m trainer.main --profile mock`
- `python -m trainer.main --profile rimapi`
- `python -m trainer.main --profile rimbridge`

If `--profile` is omitted, only `config/default.yaml` is used.

## Backend switching

The active backend should be selected through config, for example:

- `bridge_backend: mock`
- `bridge_backend: rimapi`
- `bridge_backend: rimbridge`

Profiles can override defaults from `config/default.yaml` via `config/profiles/<name>.yaml`.

### Backend configuration

`config/default.yaml` now contains backend-specific settings:

- `backends.rimapi`
  - `base_url`
  - `timeout_seconds`
  - `map_id`
  - `prefer_v2_colonists`
  - `start_new_game_on_reset`
- `backends.rimbridge`
  - `host`
  - `port`
  - `token`
  - `config_path`
  - `transport`
  - `timeout_seconds`
  - `bridge_version`

RimBridgeServer can be configured either directly through `host`/`port`/`token` or indirectly through the GABP config file path.

## Run mock mode

Mock mode is deterministic and does not require RimWorld to be installed.

```bash
python -m trainer.main --profile mock
# or use the helper script:
bash codex/actions/run_mock.sh
```

The run prints a short summary including:
- total steps
- terminal reason
- final colonist count
- final food
- final medicine

## Notes

- This project is local-only and not intended as a hosted product.
- Generated artifacts should not be committed.

## Backend checks

Use the helper scripts to test each live backend independently:

```bash
bash codex/actions/check_rimapi.sh
bash codex/actions/check_rimbridge.sh
```

Each script fails clearly when the backend is unavailable and prints connection plus capability details when it succeeds.
