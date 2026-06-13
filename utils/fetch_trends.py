"""Fetch real fashion-trend data into data/trends.json.

Source: Wikimedia Pageviews API (official, public, keyless).
https://wikimedia.org/api/rest_v1/

Each trend tag maps to an English Wikipedia article about that style.
  mentions  = total article pageviews over the most recent 30 days
  momentum  = (recent 30-day views / prior 30-day views) - 1
              e.g. 0.25 means reader interest is up 25% month over month

Tags are drawn from the listings dataset's own style_tags so trends can
cross-reference stock. A few real current trends with no stock in the
dataset (e.g. gorpcore) are included deliberately, so check_trends can
honestly report in_stock: 0.

Rerun to refresh the snapshot:
    .venv/bin/python utils/fetch_trends.py
"""
import json
import time
import urllib.parse
import urllib.request
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "trends.json"
UA = "fitfindr-ai201-student-project/0.1 (educational; contact via course)"

# dataset style_tag -> English Wikipedia article
TAG_ARTICLES = {
    "vintage": "Vintage_clothing",
    "streetwear": "Streetwear",
    "cottagecore": "Cottagecore",
    "grunge": "Grunge_fashion",
    "y2k": "Y2K_aesthetic",
    "90s": "1990s_in_fashion",
    "2000s": "2000s_in_fashion",
    "denim": "Denim",
    "athletic": "Athleisure",
    "goth": "Gothic_fashion",
    "western": "Western_wear",
    "preppy": "Preppy",
    "boho": "Boho-chic",
    "dark academia": "Dark_academia",
    "workwear": "Workwear",
    "flannel": "Flannel",
    "knitwear": "Knitwear",
    "crochet": "Crochet",
    "tie-dye": "Tie-dye",
    "cargo": "Cargo_pants",
    "platform": "Platform_shoe",
    # real, current trends deliberately NOT in the listings dataset:
    "gorpcore": "Gorpcore",
    "barbiecore": "Barbiecore",
}


def fetch_views(article: str, start: str, end: str) -> list[int] | None:
    """Daily view counts for an article, or None if the article 404s."""
    url = (
        "https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/"
        f"en.wikipedia/all-access/user/{urllib.parse.quote(article, safe='')}"
        f"/daily/{start}00/{end}00"
    )
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    for attempt in range(5):
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                items = json.load(r)["items"]
            return [i["views"] for i in items]
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            if e.code == 429:
                time.sleep(5 * (attempt + 1))
                continue
            raise
    raise RuntimeError(f"rate-limited 5 times on {article}")


def main() -> None:
    end = date.today() - timedelta(days=2)  # pageview data lags ~1-2 days
    start = end - timedelta(days=59)        # 60 days = two 30-day windows
    s, e = start.strftime("%Y%m%d"), end.strftime("%Y%m%d")

    trends, skipped = [], []
    for tag, article in TAG_ARTICLES.items():
        views = fetch_views(article, s, e)
        if views is None or len(views) < 40:
            skipped.append(f"{tag} ({article})")
            continue
        half = len(views) // 2
        prior, recent = sum(views[:half]), sum(views[half:])
        momentum = round(recent / prior - 1, 3) if prior else 0.0
        trends.append({
            "tag": tag,
            "article": article,
            "mentions": recent,
            "momentum": momentum,
        })
        print(f"  {tag:<14} {recent:>7} views  momentum {momentum:+.1%}")
        time.sleep(1.5)  # be polite to the API

    trends.sort(key=lambda t: t["mentions"], reverse=True)
    snapshot = {
        "_source": (
            "Wikimedia Pageviews API (en.wikipedia, all-access, user traffic). "
            "Real reader-interest data for fashion style articles. "
            "mentions = pageviews over the most recent 30 days, "
            "momentum = 30-day views vs the prior 30 days, as a ratio - 1."
        ),
        "_fetched": date.today().isoformat(),
        "_window": {"start": start.isoformat(), "end": end.isoformat()},
        "_script": "utils/fetch_trends.py",
        "trends": trends,
    }
    OUT.write_text(json.dumps(snapshot, indent=2) + "\n")
    print(f"\nwrote {OUT.relative_to(ROOT)}: {len(trends)} trends")
    if skipped:
        print("skipped (no article/insufficient data):", ", ".join(skipped))


if __name__ == "__main__":
    main()
