## Project rules

- Keep the trainer bridge-agnostic.
- Support both RIMAPI and RimBridgeServer through adapters.
- Prefer structured game-state bridges over pixels.
- Ensure mock mode runs even without RimWorld installed.
- Keep configs in YAML profiles.
- Do not commit generated artifacts from runs/, models/, or data/.