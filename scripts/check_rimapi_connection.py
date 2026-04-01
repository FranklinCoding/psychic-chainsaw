from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from trainer.config import load_config
from trainer.environment.rimapi.adapter import RimAPIAdapter
from trainer.environment.errors import BackendError


def main() -> int:
    config = load_config(profile="rimapi")
    adapter = RimAPIAdapter(settings=config.backends.rimapi)
    try:
        adapter.connect()
        capabilities = adapter.get_capabilities()
        observation = adapter.get_observation()
    except BackendError as exc:
        print(f"RIMAPI connection failed: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:  # pragma: no cover - defensive CLI path
        print(f"Unexpected RIMAPI failure: {exc}", file=sys.stderr)
        return 1
    finally:
        adapter.close()

    print(f"backend={adapter.backend_name}")
    print(f"base_url={config.backends.rimapi.base_url}")
    print(f"timeout_seconds={config.backends.rimapi.timeout_seconds}")
    print(f"colonists={observation.colonist_count} food={observation.food} medicine={observation.medicine}")
    print("capabilities=" + json.dumps(capabilities.model_dump(mode="python"), sort_keys=True))
    print("metadata=" + json.dumps(observation.metadata, sort_keys=True, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
