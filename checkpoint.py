"""
checkpoint.py — remember which papers are already done, so re-running skips them.

Keeps a small JSON file (output/checkpoint.json) keyed by each paper's dedup key
(PMID, else DOI, else title). A paper is "done" once it's either extracted or
confirmed closed-source; anything marked "error" is retried on the next run.
"""

import json
from pathlib import Path


class Checkpoint:
    def __init__(self, path):
        self.path = Path(path)
        self.data = self._load()

    def _load(self):
        if self.path.exists():
            try:
                return json.loads(self.path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                return {}
        return {}

    def _save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(self.data, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    def is_done(self, key):
        return self.data.get(key, {}).get("status") in ("extracted", "closed")

    def mark(self, key, status, **extra):
        self.data[key] = {"status": status, **extra}
        self._save()

    def reset(self):
        self.data = {}
        self._save()
