"""BM25 retrieval over bundled Langflow component_index.json (no Langflow backend)."""

from __future__ import annotations

import json
import math
import re
from collections import Counter
from pathlib import Path
from typing import Any

_TOKEN = re.compile(r"\w+", re.UNICODE)


def _default_index_path() -> Path:
    """Resolve …/langflow/src/lfx/src/lfx/_assets/component_index.json from this package."""
    here = Path(__file__).resolve()
    for parent in here.parents:
        candidate = parent / "langflow" / "src" / "lfx" / "src" / "lfx" / "_assets" / "component_index.json"
        if candidate.is_file():
            return candidate
    msg = (
        "component_index.json not found. Clone langflow next to workflow_compactor or set "
        "WORKFLOW_COMPACTOR_COMPONENT_INDEX to the file path."
    )
    raise FileNotFoundError(msg)


def load_registry_flat(index_path: Path | None = None) -> dict[str, dict[str, Any]]:
    import os

    if index_path is not None:
        path = index_path
    elif os.environ.get("WORKFLOW_COMPACTOR_COMPONENT_INDEX"):
        path = Path(os.environ["WORKFLOW_COMPACTOR_COMPONENT_INDEX"])
    else:
        path = _default_index_path()

    data = json.loads(path.read_text(encoding="utf-8"))
    registry: dict[str, dict[str, Any]] = {}
    for cat in data.get("entries", []):
        if isinstance(cat, list) and len(cat) > 1 and isinstance(cat[1], dict):
            category = cat[0] if isinstance(cat[0], str) else ""
            for name, comp in cat[1].items():
                if isinstance(comp, dict) and "template" in comp:
                    registry[name] = {**comp, "category": category}
    if not registry:
        msg = f"No components in {path}"
        raise ValueError(msg)
    return registry


def _build_card(name: str, category: str, comp: dict[str, Any]) -> str:
    parts = [
        name,
        category,
        str(comp.get("display_name", "")),
        str(comp.get("description", ""))[:400],
    ]
    tmpl = comp.get("template")
    if isinstance(tmpl, dict):
        for key, spec in tmpl.items():
            if key == "code":
                continue
            if isinstance(spec, dict):
                parts.append(key.replace("_", " "))
                for k in ("display_name", "name", "info"):
                    v = spec.get(k)
                    if isinstance(v, str) and len(v) < 300:
                        parts.append(v)
    return " ".join(p for p in parts if p)


class _BM25:
    def __init__(self, docs: list[list[str]], k1: float = 1.5, b: float = 0.75) -> None:
        self._k1 = k1
        self._b = b
        self._docs = docs
        self._n = len(docs)
        self._freqs: list[Counter[str]] = []
        lens: list[int] = []
        nd: dict[str, int] = {}
        for doc in docs:
            c = Counter(doc)
            self._freqs.append(c)
            lens.append(len(doc))
            for w in c:
                nd[w] = nd.get(w, 0) + 1
        self._avgdl = sum(lens) / self._n if self._n else 0.0
        self._idf = {w: math.log((self._n - f + 0.5) / (f + 0.5) + 1.0) for w, f in nd.items()}

    def score(self, q: list[str]) -> list[float]:
        if not self._n or not self._avgdl:
            return [0.0] * self._n
        out = [0.0] * self._n
        for term in set(q):
            if term not in self._idf:
                continue
            idf = self._idf[term]
            for i, fr in enumerate(self._freqs):
                tf = fr.get(term)
                if not tf:
                    continue
                dl = len(self._docs[i])
                denom = tf + self._k1 * (1 - self._b + self._b * dl / self._avgdl)
                out[i] += idf * (tf * (self._k1 + 1)) / denom
        return out


_bm: _BM25 | None = None
_rows: list[dict[str, str]] | None = None


def search_component_cards(query: str, top_k: int = 24, index_path: Path | None = None) -> list[dict[str, Any]]:
    global _bm, _rows
    if _bm is None or _rows is None:
        reg = load_registry_flat(index_path)
        docs: list[list[str]] = []
        rows: list[dict[str, str]] = []
        for name, comp in reg.items():
            cat = str(comp.get("category") or "")
            text = _build_card(name, cat, comp)
            tok = [t.casefold() for t in _TOKEN.findall(text)] or [name.casefold()]
            docs.append(tok)
            rows.append(
                {
                    "name": name,
                    "category": cat,
                    "display_name": str(comp.get("display_name") or name),
                }
            )
        _bm = _BM25(docs)
        _rows = rows

    assert _bm is not None and _rows is not None
    q = [t.casefold() for t in _TOKEN.findall(query)]
    if not q:
        return []
    scores = _bm.score(q)
    order = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]
    return [{**_rows[i], "score": round(scores[i], 4)} for i in order if scores[i] > 0]
