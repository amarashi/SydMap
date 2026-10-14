"""Fact checks: every claim the map makes in its own words (quests, landmark figures) names a Wikipedia article and
the strings that article must contain. Articles are fetched once (data/raw/articles/) and compared case-insensitively,
with typographic quotes and dashes folded to plain ones.

    uv run python -m pipeline.checks          # check the landmark figures and every quest
"""
import json
import re
import time

from .config import RAW

CACHE = RAW / "articles"


def norm(s: str) -> str:
    s = s.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    s = s.replace("–", "-").replace("—", "-").replace(" ", " ")
    return re.sub(r"\s+", " ", s).casefold()


def article(title: str) -> str:
    """The plain text of an English Wikipedia article (cached)."""
    from .s00_fetch import wiki_get
    CACHE.mkdir(parents=True, exist_ok=True)
    p = CACHE / (re.sub(r"[^\w.-]+", "_", title) + ".json")
    if p.exists():
        return json.loads(p.read_text())["text"]
    d = wiki_get(dict(action="query", prop="extracts|info", explaintext=1, inprop="url", titles=title, redirects=1))
    page = d["query"]["pages"][0]
    if page.get("missing"):
        raise KeyError(f"no Wikipedia article {title!r}")
    p.write_text(json.dumps(dict(title=page["title"], url=page.get("fullurl"), text=page.get("extract", "")), ensure_ascii=False))
    time.sleep(0.5)
    return page.get("extract", "")


def url(title: str) -> str:
    article(title)
    p = CACHE / (re.sub(r"[^\w.-]+", "_", title) + ".json")
    return json.loads(p.read_text())["url"]


def failures(checks) -> list[str]:
    """The (article, string) pairs that do not hold; empty when every claim is in its article."""
    bad = []
    for title, strings in checks:
        try:
            text = norm(article(title))
        except KeyError as e:
            bad.append(str(e))
            continue
        bad += [f"{title}: {s!r}" for s in strings if norm(s) not in text]
    return bad


if __name__ == "__main__":
    from .landmarks import CHECKS
    from .quests import QUESTS
    allc = list(CHECKS) + [c for q in QUESTS for s in q["steps"] for c in s["checks"]]
    bad = failures(allc)
    print(f"{len(allc)} checks, {len(bad)} failing")
    for b in bad:
        print("  ✗", b)
