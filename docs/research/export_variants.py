#!/usr/bin/env python3
"""Export public Commander Spellbook variants with resumable pagination.

Usage: python docs/research/export_variants.py
Environment: SPELLBOOK_API (default https://backend.commanderspellbook.com)
Output: variants.jsonl + export_status.json in SPELLBOOK_OUTPUT_DIR.
No credentials, production DB access, or private snapshots required.
"""
import json
import os
import pathlib
import time
import urllib.error
import urllib.parse
import urllib.request

base = os.getenv("SPELLBOOK_API", "https://backend.commanderspellbook.com").rstrip("/")
out = pathlib.Path(os.getenv("SPELLBOOK_OUTPUT_DIR", "spellbook-export"))
out.mkdir(parents=True, exist_ok=True)
data_file = out / "variants.jsonl"
status_file = out / "export_status.json"
next_url = base + "/variants/?limit=100"
count = 0
if status_file.exists():
    state = json.loads(status_file.read_text())
    next_url = state.get("next_url")
    count = state.get("count", 0)
if not next_url:
    print("Already complete:", count)
    raise SystemExit(0)
with data_file.open("a", encoding="utf-8") as f:
    while next_url:
        for attempt in range(6):
            try:
                req = urllib.request.Request(next_url, headers={"User-Agent": "Sisay-Combo-Research/0.1", "Accept": "application/json"})
                with urllib.request.urlopen(req, timeout=45) as response:
                    page = json.load(response)
                break
            except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
                if attempt == 5:
                    raise
                time.sleep(min(60, 2 ** attempt * 2))
        results = page.get("results", []) if isinstance(page, dict) else page
        if not isinstance(results, list):
            raise ValueError("Unexpected API response structure")
        for record in results:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
        f.flush()
        count += len(results)
        raw_next = page.get("next") if isinstance(page, dict) else None
        next_url = urllib.parse.urljoin(base, raw_next) if raw_next else None
        status_file.write_text(json.dumps({"count": count, "next_url": next_url, "complete": next_url is None}, indent=2))
        print("exported", count, "next", bool(next_url), flush=True)
        time.sleep(0.3)
