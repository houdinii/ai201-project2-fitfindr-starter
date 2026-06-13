"""
tools.py

The three required FitFindr tools. Each tool is a standalone function that
can be called and tested independently before being wired into the agent loop.

Complete and test each tool before moving to agent.py.

Tools:
    search_listings(description, size, max_price)               → list[dict]
    suggest_outfit(new_item, wardrobe, style_profile, trends)   → str
    create_fit_card(outfit, new_item)                           → str
    compare_prices(item)                                        → dict
    check_trends(category, size)                                → list[dict]
    save_style_preference(preference)                           → list[str] | str
"""

import json
import os
import re
import statistics
import time

from dotenv import load_dotenv
from groq import Groq

from utils.data_loader import load_listings
from utils.trace import log, trunc

load_dotenv()

_DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
_TRENDS_PATH = os.path.join(_DATA_DIR, "trends.json")
_STYLE_PROFILE_PATH = os.path.join(_DATA_DIR, "style_profile.json")


# ── Groq client ───────────────────────────────────────────────────────────────

def _get_groq_client():
    """Initialize and return a Groq client using GROQ_API_KEY from .env."""
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError(
            "GROQ_API_KEY not set. Add it to a .env file in the project root."
        )
    return Groq(api_key=api_key)


# ── Tool 1: search_listings ───────────────────────────────────────────────────

def _tokenize(text: str) -> list[str]:
    """Lowercase and split text into word tokens, keeping apostrophes."""
    return re.findall(r"[a-z0-9']+", text.lower())


def _size_matches(requested: str, listing_size: str) -> bool:
    """
    Token-based size match. The listing size splits on '/', spaces, and
    parentheses, and the requested size must equal one of the tokens, so
    "M" matches "S/M" but "L" never matches "XL". "One Size" matches any
    requested size.
    """
    if "one size" in listing_size.lower():
        return True
    tokens = [t for t in re.split(r"[/\s()]+", listing_size.lower()) if t]
    return requested.strip().lower() in tokens


def search_listings(
    description: str,
    size: str | None = None,
    max_price: float | None = None,
) -> list[dict]:
    """
    Search the mock listings dataset for items matching the description,
    optional size, and optional price ceiling.

    Args:
        description: Keywords describing what the user is looking for
                     (e.g., "vintage graphic tee").
        size:        Size string to filter by, or None to skip size filtering.
                     Matching is case-insensitive (e.g., "M" matches "S/M").
        max_price:   Maximum price (inclusive), or None to skip price filtering.

    Returns:
        A list of matching listing dicts, sorted by relevance (best match first).
        Returns an empty list if nothing matches — does NOT raise an exception.

    Each listing dict has the following fields:
        id, title, description, category, style_tags (list), size,
        condition, price (float), colors (list), brand, platform

    TODO:
        1. Load all listings with load_listings().
        2. Filter by max_price and size (if provided).
        3. Score each remaining listing by keyword overlap with `description`.
        4. Drop any listings with a score of 0 (no relevant matches).
        5. Sort by score, highest first, and return the listing dicts.

    Before writing code, fill in the Tool 1 section of planning.md.
    """
    query_words = set(_tokenize(description))
    scored = []

    for listing in load_listings():
        if max_price is not None and listing["price"] > max_price:
            continue
        if size is not None and not _size_matches(size, listing["size"]):
            continue

        haystack_parts = [
            listing["title"],
            listing["description"],
            " ".join(listing["style_tags"]),
            " ".join(listing["colors"]),
            listing["category"],
        ]
        if listing["brand"] is not None:
            haystack_parts.append(listing["brand"])
        haystack = set(_tokenize(" ".join(haystack_parts)))

        score = len(query_words & haystack)
        if score > 0:
            scored.append((score, listing))

    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [listing for _, listing in scored]


# ── Tool 2: suggest_outfit ────────────────────────────────────────────────────

_GROQ_MODEL = "llama-3.3-70b-versatile"


def _format_listing(item: dict) -> str:
    """Format a listing dict into prompt-ready lines. Skips null brand."""
    lines = [
        f"Title: {item['title']}",
        f"Description: {item['description']}",
        f"Category: {item['category']}",
        f"Style tags: {', '.join(item['style_tags'])}",
        f"Colors: {', '.join(item['colors'])}",
        f"Size: {item['size']}",
        f"Condition: {item['condition']}",
        f"Price: ${item['price']:.2f}",
        f"Platform: {item['platform']}",
    ]
    if item.get("brand"):
        lines.insert(1, f"Brand: {item['brand']}")
    return "\n".join(lines)


def _format_wardrobe(items: list[dict]) -> str:
    """
    Format wardrobe items into prompt-ready bullet lines.

    Wardrobe items have only name, category, colors, style_tags, and notes.
    No size or price. Null notes are skipped, same guard as null brand.
    """
    lines = []
    for w in items:
        line = (
            f"- {w['name']} (category: {w['category']}, "
            f"colors: {', '.join(w['colors'])}, "
            f"style: {', '.join(w['style_tags'])})"
        )
        if w.get("notes"):
            line += f". Notes: {w['notes']}"
        lines.append(line)
    return "\n".join(lines)


def suggest_outfit(
    new_item: dict,
    wardrobe: dict,
    style_profile: list[str] | None = None,
    trends: list[dict] | None = None,
) -> str:
    """
    Given a thrifted item and the user's wardrobe, suggest 1-2 complete outfits.

    Args:
        new_item:      A listing dict (the item the user is considering buying).
        wardrobe:      A wardrobe dict with an 'items' key containing a list of
                       wardrobe item dicts. May be empty, handled gracefully.
        style_profile: Saved preferences loaded from data/style_profile.json,
                       injected by the executor when present. Optional.
        trends:        Trend data from check_trends, injected by the executor
                       when available. Optional.

    Returns:
        A non-empty string with outfit suggestions. If the wardrobe is empty,
        the string is general styling advice for the item instead of
        wardrobe-specific outfits.

    Raises:
        Propagates Groq client errors, and raises RuntimeError if the LLM
        returns an empty response. The executor owns the catch, wait, and
        retry-once behavior per the Error Handling table in planning.md.
    """
    items = wardrobe.get("items", [])

    sections = [
        "The user is considering buying this thrifted item:",
        _format_listing(new_item),
    ]

    if items:
        sections += [
            "",
            "Their current wardrobe:",
            _format_wardrobe(items),
            "",
            "Suggest 1-2 complete outfits built around the new item. Use "
            "specific pieces from the wardrobe, referring to each piece by "
            "its name. Briefly say why each outfit works.",
        ]
    else:
        sections += [
            "",
            "The user has not added any wardrobe items yet. Give general "
            "styling advice for this item instead: what kinds of pieces pair "
            "well with it, what colors and silhouettes to reach for, and "
            "what vibe it suits.",
        ]

    if style_profile:
        sections += [
            "",
            "The user's saved style preferences, weigh these when choosing "
            "pieces: " + ", ".join(style_profile),
        ]

    if trends:
        sections += [
            "",
            "Current trend data, mention a trend only where it genuinely "
            "fits the outfit: " + json.dumps(trends),
        ]

    client = _get_groq_client()
    log(f"llm  call  suggest_outfit (item={trunc(new_item['title'], 40)}, "
        f"wardrobe={len(items)}, profile={len(style_profile or [])}, "
        f"trends={len(trends or [])}, temp=0.7)")
    t0 = time.time()
    response = client.chat.completions.create(
        model=_GROQ_MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are FitFindr, a friendly secondhand-fashion stylist. "
                    "Keep suggestions concrete and wearable, grounded in the "
                    "pieces you are given. Plain text, no markdown headers."
                ),
            },
            {"role": "user", "content": "\n".join(sections)},
        ],
        temperature=0.7,
    )

    text = (response.choices[0].message.content or "").strip()
    log(f"llm  resp  suggest_outfit ({(time.time() - t0) * 1000:.0f}ms, "
        f"{len(text)} chars)")
    if not text:
        raise RuntimeError(
            f"suggest_outfit got an empty LLM response for "
            f"'{new_item['title']}'"
        )
    return text


# ── Tool 3: create_fit_card ───────────────────────────────────────────────────

def create_fit_card(outfit: str, new_item: dict) -> str:
    """
    Generate a short, shareable outfit caption for the thrifted find.

    Args:
        outfit:   The outfit suggestion string from suggest_outfit().
        new_item: The listing dict for the thrifted item.

    Returns:
        A 2-4 sentence string in the style of an Instagram/TikTok caption,
        mentioning the item name, price, and platform once each. Output
        varies run to run for the same input, enforced with a higher LLM
        temperature.

        If outfit is missing or empty, returns a descriptive error message
        string instead. This tool never raises for bad outfit input, the
        agent's guard on session["outfit_suggestion"] makes that branch
        unreachable in normal operation.

    Raises:
        Propagates Groq client errors, and raises RuntimeError if the LLM
        returns an empty response, same contract as suggest_outfit. The
        agent sets session["error"] but still shows the outfit suggestion,
        so the user keeps the styling work even when the caption fails.
    """
    if not outfit or not outfit.strip():
        return (
            f"Can't create a fit card for '{new_item['title']}' because "
            f"there is no outfit suggestion to caption. Run suggest_outfit "
            f"for this item first, then try the fit card again."
        )

    prompt = "\n".join([
        "Write a shareable caption for this thrifted find and the outfit "
        "built around it.",
        "",
        "The item:",
        _format_listing(new_item),
        "",
        "The outfit:",
        outfit,
        "",
        "Rules for the caption:",
        "- 2-4 sentences, plain text, no markdown",
        "- casual and authentic, like a real OOTD post, not a product "
        "description",
        f"- mention the item name, the price (${new_item['price']:.2f}), "
        f"and the platform ({new_item['platform']}) naturally, exactly once "
        f"each, never repeating any of them",
        "- capture the outfit vibe in specific terms, not generic hype",
    ])

    client = _get_groq_client()
    log(f"llm  call  create_fit_card (item={trunc(new_item['title'], 40)}, "
        f"temp=1.0)")
    t0 = time.time()
    response = client.chat.completions.create(
        model=_GROQ_MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "You write short, casual outfit captions for social "
                    "media. You sound like a real person posting their "
                    "thrift find, never like an ad."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        temperature=1.0,
    )

    text = (response.choices[0].message.content or "").strip()
    log(f"llm  resp  create_fit_card ({(time.time() - t0) * 1000:.0f}ms, "
        f"{len(text)} chars)")
    if not text:
        raise RuntimeError(
            f"create_fit_card got an empty LLM response for "
            f"'{new_item['title']}'"
        )
    return text


# ── Tool 4: compare_prices (stretch: Price Comparison) ────────────────────────

def compare_prices(item: dict) -> dict:
    """
    Estimate whether an item's price is fair based on comparable listings.

    The router-visible parameter is item_id, resolved by the executor to
    this listing dict per the state-by-reference design.

    Comparables are listings in the same category sharing at least one
    style_tag with the item, the item itself always excluded. Fewer than 3
    falls back to the whole category. The verdict band is the comparable
    median plus or minus 10 percent. Pure local computation, no LLM call.

    Args:
        item: The listing dict to assess.

    Returns:
        A dict with verdict ("below market", "fair", "above market", or
        "not enough data"), item_price, comparable_count, comp_min,
        comp_median, comp_max, and a one-sentence reasoning string.
        On "not enough data" the comp stats are None. Never raises and
        never blocks the core chain.
    """
    others = [l for l in load_listings() if l["id"] != item["id"]]
    same_category = [l for l in others if l["category"] == item["category"]]

    item_tags = set(item["style_tags"])
    comparables = [
        l for l in same_category if item_tags & set(l["style_tags"])
    ]
    if len(comparables) < 3:
        comparables = same_category

    price = item["price"]

    if len(comparables) < 3:
        return {
            "verdict": "not enough data",
            "item_price": price,
            "comparable_count": len(comparables),
            "comp_min": None,
            "comp_median": None,
            "comp_max": None,
            "reasoning": (
                f"Only {len(comparables)} comparable "
                f"{item['category']} listing(s) exist, so price fairness "
                f"can't be assessed for '{item['title']}'."
            ),
        }

    prices = [l["price"] for l in comparables]
    median = statistics.median(prices)

    if price < median * 0.9:
        verdict = "below market"
        relation = "below"
    elif price > median * 1.1:
        verdict = "above market"
        relation = "above"
    else:
        verdict = "fair"
        relation = "right at"

    return {
        "verdict": verdict,
        "item_price": price,
        "comparable_count": len(comparables),
        "comp_min": min(prices),
        "comp_median": median,
        "comp_max": max(prices),
        "reasoning": (
            f"At ${price:.2f} this item sits {relation} the "
            f"${median:.2f} median of {len(comparables)} comparable "
            f"{item['category']} listings."
        ),
    }


# ── Tool 5: check_trends (stretch: Trend Awareness) ───────────────────────────

def check_trends(
    category: str | None = None,
    size: str | None = None,
) -> list[dict]:
    """
    Surface which styles are currently popular from data/trends.json,
    a snapshot of real reader-interest data fetched from the Wikimedia
    Pageviews API by utils/fetch_trends.py. Each trend's mentions is that
    style article's pageviews over the most recent 30 days, momentum is
    the 30-day views vs the prior 30 days as a ratio minus 1. Rerun the
    script to refresh the snapshot.

    Args:
        category: Limit trends to one listing category, such as "tops".
                  None returns trends across all categories.
        size:     The user's size. When provided, each trend reports how
                  many in-stock listings match both the trend and the size.
                  None skips the stock check.

    Returns:
        Up to 5 trend dicts sorted by mentions, each with tag, mentions,
        momentum, and in_stock (0 when size is None). Returns an empty
        list if trends.json is missing or unreadable, or no trends match
        the category. Trend data is flavor, never load-bearing, so this
        tool never raises and never blocks the core flow.
    """
    try:
        with open(_TRENDS_PATH, "r", encoding="utf-8") as f:
            trends = json.load(f)["trends"]
        log(f"file read  data/trends.json ({len(trends)} trends)")
    except (OSError, json.JSONDecodeError, KeyError, TypeError):
        log("file read  data/trends.json FAILED (missing/corrupt) -> []")
        return []

    listings = load_listings()
    results = []
    for trend in trends:
        tagged = [l for l in listings if trend["tag"] in l["style_tags"]]
        if category is not None:
            tagged = [l for l in tagged if l["category"] == category]
            if not tagged:
                continue

        in_stock = 0
        if size is not None:
            in_stock = sum(
                1 for l in tagged if _size_matches(size, l["size"])
            )

        results.append({
            "tag": trend["tag"],
            "mentions": trend["mentions"],
            "momentum": trend["momentum"],
            "in_stock": in_stock,
        })

    results.sort(key=lambda t: t["mentions"], reverse=True)
    return results[:5]


# ── Tool 6: save_style_preference (stretch: Style Profile Memory) ─────────────

def save_style_preference(preference: str) -> list[str] | str:
    """
    Persist a style preference to data/style_profile.json.

    Saving is the only router-visible operation. Reading is automatic, the
    executor loads the profile at session start and injects it into the
    suggest_outfit prompt the same way it injects the wardrobe.

    Args:
        preference: A short preference statement, such as "loves grunge"
                    or "dislikes pink".

    Returns:
        The updated list of saved preferences, so the router can confirm
        to the user what is now remembered. Saves dedupe case-insensitively,
        re-saving an existing preference returns the list unchanged.

        If the file cannot be written, returns a descriptive error string
        instead of raising. A failed write never affects the current
        interaction. A corrupt or missing profile on the read side is
        treated as an empty profile.
    """
    try:
        with open(_STYLE_PROFILE_PATH, "r", encoding="utf-8") as f:
            preferences = list(json.load(f)["preferences"])
    except (OSError, json.JSONDecodeError, KeyError, TypeError):
        preferences = []

    cleaned = preference.strip()
    already_saved = cleaned.lower() in (p.lower() for p in preferences)

    if cleaned and not already_saved:
        preferences.append(cleaned)
        try:
            with open(_STYLE_PROFILE_PATH, "w", encoding="utf-8") as f:
                json.dump({"preferences": preferences}, f, indent=2)
            log(f"file write data/style_profile.json ({len(preferences)} "
                f"prefs, added '{trunc(cleaned, 40)}')")
        except OSError as exc:
            log(f"file write data/style_profile.json FAILED ({trunc(exc, 50)})")
            return (
                f"Couldn't save the preference '{cleaned}' to the style "
                f"profile ({exc}). The rest of the session continues "
                f"normally, try saving it again later."
            )
    else:
        log(f"file write data/style_profile.json SKIPPED "
            f"({'duplicate' if already_saved else 'empty'})")

    return preferences
