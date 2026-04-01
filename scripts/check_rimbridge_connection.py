from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from trainer.config import load_config
from trainer.environment.errors import BackendError
from trainer.environment.rimbridge.adapter import RimBridgeServerAdapter


def main() -> int:
    config = load_config(profile="rimbridge")
    adapter = RimBridgeServerAdapter(settings=config.backends.rimbridge)
    try:
        adapter.connect()
        capabilities = adapter.get_capabilities()
        observation = adapter.get_observation()
    except BackendError as exc:
        print(f"RimBridgeServer connection failed: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:  # pragma: no cover - defensive CLI path
        print(f"Unexpected RimBridgeServer failure: {exc}", file=sys.stderr)
        return 1
    finally:
        adapter.close()

    host, port = config.backends.rimbridge.resolve_host_port()
    print(f"backend={adapter.backend_name}")
    print(f"host={host}")
    print(f"port={port}")
    print(f"config_path={config.backends.rimbridge.expanded_config_path}")
    print(f"colonists={observation.colonist_count} wealth={observation.colony_wealth} partial={observation.metadata.get('partial_observation')}")
    print("capabilities=" + json.dumps(capabilities.model_dump(mode="python"), sort_keys=True))
    print("metadata=" + json.dumps(observation.metadata, sort_keys=True, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
