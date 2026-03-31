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

## Backend switching

The active backend should be selected through config, for example:

- `bridge_backend: mock`
- `bridge_backend: rimapi`
- `bridge_backend: rimbridge`

Profiles can override defaults from `config/default.yaml` via `config/profiles/<name>.yaml`.

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
