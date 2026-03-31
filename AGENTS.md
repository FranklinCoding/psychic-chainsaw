# AGENTS.md

## Repository rules

- Keep the trainer bridge-agnostic.
- Support both RIMAPI and RimBridgeServer through separate adapters.
- Prefer structured state/action bridges over pixel automation.
- Ensure mock mode runs even without RimWorld installed.
- Keep settings in YAML config profiles where possible.
- Do not commit generated artifacts from `runs/`, `models/`, or `data/`.
- Keep changes modular and easy to test.
- When adding a backend-specific feature, isolate it behind capability flags or adapter methods.
- Prefer a narrower working prototype over a fake complete system.

## Commands

- Install: `bash .codex/setup.sh`
- Test: `bash .codex/actions/test.sh`
- Run mock mode: `bash .codex/actions/run_mock.sh`