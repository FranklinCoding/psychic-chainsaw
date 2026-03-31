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

## Notes

- This project is local-only and not intended as a hosted product.
- Generated artifacts should not be committed.
