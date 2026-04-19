"""Print this month's Gemini usage summary by scanning metadata.json files."""
from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from pekintv_bot.config import load_config  # noqa: E402


def main() -> int:
    cfg = load_config()
    now = datetime.now()
    month_prefix = now.strftime("%Y%m")

    total_cost = 0.0
    total_drafts = 0
    total_image_calls = 0
    for folder in cfg.draft_output_dir.iterdir():
        if not folder.is_dir() or not folder.name.startswith(month_prefix):
            continue
        meta = folder / "metadata.json"
        if not meta.exists():
            continue
        try:
            data = json.loads(meta.read_text(encoding="utf-8"))
        except Exception:
            continue
        total_drafts += 1
        total_cost += float(data.get("estimated_cost_usd") or 0.0)
        total_image_calls += len(data.get("variants") or []) + (1 if data.get("retry") else 0)

    daily_capacity = cfg.free_tier_daily_limit
    days = now.day
    monthly_capacity = daily_capacity * days
    remaining_pct = max(0, 100 - int(100 * total_image_calls / max(monthly_capacity, 1)))

    print(f"Month: {now.strftime('%Y-%m')}")
    print(f"Drafts produced: {total_drafts}")
    print(f"Image generations: {total_image_calls}")
    print(f"Estimated cost (if billed):  ${total_cost:.2f}")
    print(f"Free-tier headroom this month: ~{remaining_pct}% (capacity ≈ {monthly_capacity}/day-cum)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
