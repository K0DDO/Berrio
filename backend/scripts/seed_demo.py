"""CLI: python -m scripts.seed_demo  (run from backend/ with venv)."""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

# Allow `python -m scripts.seed_demo` from backend/
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import get_settings
from app.db.session import _session_factory
from app.modules.dev.seed import seed_demo_data


async def _main() -> None:
    settings = get_settings()
    print(f"Seeding demo data (env={settings.app_env}, debug={settings.debug})…")
    async with _session_factory()() as session:
        result = await seed_demo_data(session)
    # Password only printed by CLI for local convenience
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print("\nLogin in the app with demo@berrio.app / Demo1234!")


if __name__ == "__main__":
    asyncio.run(_main())
