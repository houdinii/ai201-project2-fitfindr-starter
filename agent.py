"""
agent.py

The FitFindr planning loop. A ReAct-style router (Groq function calling)
chooses the next tool each iteration. An executor layer validates every
call, resolves lightweight references (item ids) against the session dict,
and injects the heavy objects, so state passes between tools by reference
and never round-trips through the LLM.

Hard guards in code, per planning.md:
    - MAX_ITERATIONS cap on the router loop
    - suggest_outfit blocked while search_results is empty
    - create_fit_card blocked without session["outfit_suggestion"]
    - zero-result search retries twice inside the executor, dropping the
      size filter then the max_price cap, telling the user what was
      adjusted each time (stretch: Retry Logic with Fallback)

Usage:
    from agent import run_agent
    from utils.data_loader import get_example_wardrobe

    result = run_agent(
        query="vintage graphic tee under $30, size M",
        wardrobe=get_example_wardrobe(),
    )
    print(result["fit_card"])
    print(result["error"])   # None on success
"""

import json
import time

from tools import (
    _GROQ_MODEL,
    _STYLE_PROFILE_PATH,
    _get_groq_client,
    check_trends,
    compare_prices,
    create_fit_card,
    save_style_preference,
    search_listings,
    suggest_outfit,
)
from utils.data_loader import load_listings
from utils.trace import log, trunc

MAX_ITERATIONS = 10


# ── session state ─────────────────────────────────────────────────────────────

def _new_session(query: str, wardrobe: dict) -> dict:
    """
    Initialize and return a fresh session dict for one user interaction.

    The session dict is the single source of truth for everything that
    happens during a run. Fields per the State Management section of
    planning.md.
    """
    return {
        "query": query,              # original user query
        "parsed": {},                # extracted description / size / max_price
        "search_results": [],        # list of matching listing dicts
        "selected_item": None,       # the listing passed into suggest_outfit
        "wardrobe": wardrobe,        # user's wardrobe dict
        "style_profile": [],         # loaded from data/style_profile.json
        "trends": [],                # check_trends results, empty until called
        "price_assessment": None,    # compare_prices verdict, None until called
        "outfit_suggestion": None,   # string returned by suggest_outfit
        "fit_card": None,            # string returned by create_fit_card
        "error": None,               # set if the interaction ended early
        "notices": [],               # user-facing notes (retry adjustments etc.)
        "iterations": 0,             # router iterations, capped at MAX_ITERATIONS
        "tool_log": [],              # record of tool calls, for debugging + demo
    }


def _load_style_profile() -> list[str]:
    """Load saved preferences at session start. Corrupt or missing file is
    treated as an empty profile, per the Error Handling table."""
    try:
        with open(_STYLE_PROFILE_PATH, "r", encoding="utf-8") as f:
            prefs = list(json.load(f)["preferences"])
        log(f"file read  data/style_profile.json ({len(prefs)} prefs)")
        return prefs
    except (OSError, json.JSONDecodeError, KeyError, TypeError):
        log("file read  data/style_profile.json (none, new profile)")
        return []


# ── router LLM surface ────────────────────────────────────────────────────────

_SYSTEM_PROMPT = """You are the router for FitFindr, a secondhand fashion \
agent. You orchestrate tools. You never write outfit or caption content \
yourself, the tools do that.

Flow for an item request:
1. If the user states a durable style taste ("I mostly wear...", "never \
show me pink"), first call save_style_preference with a short phrase like \
"loves streetwear".
2. Call search_listings with description keywords plus size and max_price \
when the user gave them. Omit anything the user did not specify. Sizes are \
strings like "M", "US 8", "W30".
3. Only when the user asks about price, worth, or whether something is a \
good deal, call compare_prices with the item_id of the found item. Only \
when the user asks what is trending or popular, call check_trends.
4. Call suggest_outfit with the item_id of the listing to style. The \
system injects the wardrobe, saved style profile, and trend data \
automatically.
5. Call create_fit_card. The outfit is injected automatically.
The interaction is complete when the fit card is created.

If the message has nothing to search for (a greeting like "hey"), call no \
tools. Reply asking what they are looking for and give one example, such \
as: vintage graphic tee under $30, size M.

Rules: call one tool at a time. Use only item ids that appeared in search \
results. If a tool reports it is blocked or an argument is invalid, fix \
your next call instead of repeating it."""

_ROUTER_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "save_style_preference",
            "description": "Remember a durable style taste the user stated. "
                           "Returns the updated preference list.",
            "parameters": {
                "type": "object",
                "properties": {
                    "preference": {
                        "type": "string",
                        "description": "Short phrase, e.g. 'loves grunge' "
                                       "or 'dislikes pink'.",
                    },
                },
                "required": ["preference"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_listings",
            "description": "Search secondhand listings by keyword, with "
                           "optional size and max price filters. Retries "
                           "with loosened filters automatically on zero "
                           "results.",
            "parameters": {
                "type": "object",
                "properties": {
                    "description": {
                        "type": "string",
                        "description": "Keywords describing the item, e.g. "
                                       "'vintage graphic tee'.",
                    },
                    "size": {
                        "type": "string",
                        "description": "Size filter, e.g. 'M', 'US 8', "
                                       "'W30'. Omit if not given.",
                    },
                    "max_price": {
                        "type": "number",
                        "description": "Maximum price in dollars. Omit if "
                                       "not given.",
                    },
                },
                "required": ["description"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "compare_prices",
            "description": "Assess whether a found listing's price is fair "
                           "against comparable listings.",
            "parameters": {
                "type": "object",
                "properties": {
                    "item_id": {
                        "type": "string",
                        "description": "Listing id from search results, "
                                       "e.g. 'lst_017'.",
                    },
                },
                "required": ["item_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "check_trends",
            "description": "Surface which styles are currently popular, "
                           "optionally narrowed to a category and "
                           "cross-referenced against the user's size.",
            "parameters": {
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "description": "One of tops, bottoms, outerwear, "
                                       "shoes, accessories. Omit for all.",
                    },
                    "size": {
                        "type": "string",
                        "description": "User's size for in-stock counts. "
                                       "Omit to skip.",
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "suggest_outfit",
            "description": "Suggest 1-2 outfits built around a found "
                           "listing, using the user's wardrobe. Requires "
                           "search results.",
            "parameters": {
                "type": "object",
                "properties": {
                    "item_id": {
                        "type": "string",
                        "description": "Listing id to style. Omit to use "
                                       "the top search result.",
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_fit_card",
            "description": "Create the shareable caption for the styled "
                           "item. Requires an outfit suggestion.",
            "parameters": {
                "type": "object",
                "properties": {
                    "item_id": {
                        "type": "string",
                        "description": "Listing id. Omit to use the "
                                       "selected item.",
                    },
                },
                "required": [],
            },
        },
    },
]


# ── executor layer ────────────────────────────────────────────────────────────

def _call_with_retry(fn):
    """Catch, wait briefly, retry once, per the Error Handling table. The
    second failure propagates to the caller."""
    try:
        return fn()
    except Exception:
        time.sleep(2)
        return fn()


def _resolve_item(item_id: str | None, session: dict):
    """Resolve a lightweight item_id against the session. Returns the full
    listing dict, or an observation string when the reference is invalid."""
    if item_id is None:
        if session["selected_item"] is not None:
            return session["selected_item"]
        return ("Invalid call: no item_id given and nothing selected yet. "
                "Call search_listings first.")
    for listing in session["search_results"]:
        if listing["id"] == item_id:
            return listing
    return (f"Invalid item_id '{item_id}'. It is not in the search "
            f"results. Use an id that appeared in them.")


def _describe_filters(description: str, size, max_price) -> str:
    parts = [f"for '{description}'"]
    if size is not None:
        parts.append(f"in size {size}")
    if max_price is not None:
        parts.append(f"under ${max_price:.2f}")
    return " ".join(parts)


def _run_search(args: dict, session: dict) -> str:
    """Run search_listings with the two-stage retry. Drops the size filter
    first, then the max_price cap, recording a user-facing notice for each
    adjustment (stretch: Retry Logic with Fallback)."""
    description = (args.get("description") or "").strip()
    size = args.get("size") or None
    max_price = args.get("max_price")
    if max_price is not None:
        max_price = float(max_price)
    session["parsed"] = {
        "description": description, "size": size, "max_price": max_price,
    }

    if not description:
        return ("Blocked: empty description. Ask the user what they are "
                "looking for instead.")

    attempts = [(size, max_price)]
    if size is not None:
        attempts.append((None, max_price))
    if max_price is not None:
        attempts.append((None, None))

    for i, (s, p) in enumerate(attempts):
        results = search_listings(description, s, p)
        if results:
            session["search_results"] = results
            session["selected_item"] = results[0]
            top = ", ".join(
                f"{l['id']} '{l['title']}' ${l['price']:.2f} ({l['size']})"
                for l in results[:5]
            )
            adjustments = (
                f" Adjustments made: {' '.join(session['notices'])}"
                if session["notices"] else ""
            )
            return (f"{len(results)} result(s), best match first: {top}. "
                    f"Selected item is {results[0]['id']}.{adjustments}")
        if i + 1 < len(attempts):
            next_size = attempts[i + 1][0]
            dropped = ("size filter" if s is not None and next_size is None
                       else "price cap")
            session["notices"].append(
                f"Nothing matched {_describe_filters(description, s, p)}, "
                f"so I searched again without the {dropped}."
            )

    cheapest = min(l["price"] for l in load_listings())
    loosened = " even with all filters loosened" if len(attempts) > 1 else ""
    session["error"] = (
        f"No matches for '{description}'{loosened}. The cheapest item in "
        f"stock is ${cheapest:.2f}. Try a different description."
    )
    return session["error"]


def _execute_tool(name: str, args: dict, session: dict) -> str:
    """
    Validate and run one router tool call. Invalid calls are never
    executed, the error is returned as an observation so the router can
    self-correct. Results are written into the session, the observation
    carries only a lightweight summary back to the LLM.
    """
    if name == "save_style_preference":
        result = save_style_preference(args.get("preference", ""))
        if isinstance(result, str):
            session["notices"].append(result)
            return result  # descriptive error string, session continues
        session["style_profile"] = result
        return f"Saved. Current preferences: {', '.join(result)}."

    if name == "search_listings":
        return _run_search(args, session)

    if name == "compare_prices":
        item = _resolve_item(args.get("item_id"), session)
        if isinstance(item, str):
            return item
        assessment = compare_prices(item)
        session["price_assessment"] = assessment
        return f"{assessment['reasoning']} Verdict: {assessment['verdict']}."

    if name == "check_trends":
        trends = check_trends(args.get("category"), args.get("size"))
        session["trends"] = trends
        if not trends:
            return ("No trend data available. Proceed normally and note "
                    "that trend data was unavailable.")
        return "Trends, most popular first: " + json.dumps(trends)

    if name == "suggest_outfit":
        if not session["search_results"]:
            return ("Blocked: suggest_outfit requires search results. "
                    "Call search_listings first.")
        item = _resolve_item(args.get("item_id"), session)
        if isinstance(item, str):
            return item
        try:
            outfit = _call_with_retry(lambda: suggest_outfit(
                item,
                session["wardrobe"],
                style_profile=session["style_profile"] or None,
                trends=session["trends"] or None,
            ))
        except Exception:
            session["error"] = (
                f"Couldn't put together an outfit for '{item['title']}'. "
                f"The styling service is busy, try again in a moment."
            )
            return session["error"]
        session["selected_item"] = item
        session["outfit_suggestion"] = outfit
        return (f"Outfit suggestion stored ({len(outfit)} chars). "
                f"Preview: {outfit[:200]}")

    if name == "create_fit_card":
        outfit = session["outfit_suggestion"]
        if not outfit or not outfit.strip():
            return ("Blocked: create_fit_card requires an outfit "
                    "suggestion. Call suggest_outfit first.")
        item = _resolve_item(args.get("item_id"), session)
        if isinstance(item, str):
            return item
        try:
            card = _call_with_retry(lambda: create_fit_card(outfit, item))
        except Exception:
            session["error"] = (
                "I found your item and styled it, but couldn't generate "
                "the caption. Here is the outfit suggestion, and you can "
                "re-run for a fit card."
            )
            return session["error"]
        session["fit_card"] = card
        return "Fit card created. The interaction is complete."

    return (f"Unknown tool '{name}'. Available tools: "
            f"save_style_preference, search_listings, compare_prices, "
            f"check_trends, suggest_outfit, create_fit_card.")


# ── planning loop ─────────────────────────────────────────────────────────────

def run_agent(query: str, wardrobe: dict) -> dict:
    """
    Main agent entry point. Runs the FitFindr planning loop for a single
    user interaction and returns the completed session dict.

    Args:
        query:    Natural language user request
                  (e.g., "vintage graphic tee under $30, size M")
        wardrobe: User's wardrobe dict. Use get_example_wardrobe() or
                  get_empty_wardrobe() from utils/data_loader.py.

    Returns:
        The session dict after the interaction completes. Check
        session["error"] first. If it is set the interaction ended early,
        though partial results (an outfit without a caption, retry
        notices) may still be populated.
    """
    log(f"session START query={trunc(query, 60)!r} "
        f"wardrobe={len(wardrobe.get('items', []))} items")
    session = _new_session(query, wardrobe)
    session["style_profile"] = _load_style_profile()

    try:
        client = _get_groq_client()
    except ValueError as exc:
        session["error"] = str(exc)
        log(f"session END error={trunc(session['error'], 60)}")
        return session

    messages = [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {"role": "user", "content": query},
    ]

    while (not session["fit_card"] and not session["error"]
           and session["iterations"] < MAX_ITERATIONS):
        session["iterations"] += 1

        log(f"llm  call  router iter {session['iterations']} "
            f"(msgs={len(messages)}, temp=0.2)")
        t0 = time.time()
        try:
            response = _call_with_retry(lambda: client.chat.completions.create(
                model=_GROQ_MODEL,
                messages=messages,
                tools=_ROUTER_TOOLS,
                tool_choice="auto",
                temperature=0.2,
            ))
        except Exception:
            session["error"] = ("The styling service is busy, try again "
                                "in a moment.")
            log("llm  resp  router FAILED after retry")
            break

        msg = response.choices[0].message
        decided = ([tc.function.name for tc in msg.tool_calls]
                   if msg.tool_calls else "none (final message)")
        log(f"llm  resp  router iter {session['iterations']} "
            f"({(time.time() - t0) * 1000:.0f}ms) -> {decided}")

        if not msg.tool_calls:
            # The router signalled it is done talking. With no fit card
            # this is the ask-the-user branch (e.g. nothing to search for).
            session["error"] = (msg.content or "").strip() or (
                "The agent stopped without producing a result. Try "
                "rephrasing your query."
            )
            break

        messages.append({
            "role": "assistant",
            "content": msg.content or "",
            "tool_calls": [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                }
                for tc in msg.tool_calls
            ],
        })

        for tc in msg.tool_calls:
            try:
                args = json.loads(tc.function.arguments or "{}")
                if not isinstance(args, dict):
                    raise ValueError("arguments must be a JSON object")
            except (json.JSONDecodeError, ValueError):
                args = None

            log(f"tool call  {tc.function.name} args={trunc(args, 70)}")
            if args is None:
                observation = (f"Invalid arguments for {tc.function.name}, "
                               f"send a valid JSON object.")
            else:
                observation = _execute_tool(tc.function.name, args, session)
            log(f"tool ret   {tc.function.name} -> {trunc(observation, 80)}")

            session["tool_log"].append({
                "tool": tc.function.name,
                "args": args,
                "observation": observation[:200],
            })
            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": observation,
            })

    if not session["fit_card"] and not session["error"]:
        # MAX_ITERATIONS exhausted. Say what was accomplished and show
        # partial results, per the Error Handling table.
        done = []
        if session["search_results"]:
            done.append(f"found {len(session['search_results'])} listing(s)")
        if session["outfit_suggestion"]:
            done.append("built an outfit suggestion")
        accomplished = " and ".join(done) if done else "no step completed"
        session["error"] = (
            f"Ran out of planning steps after {MAX_ITERATIONS} iterations. "
            f"So far: {accomplished}. Partial results are shown below, "
            f"try re-running or simplifying the query."
        )

    outcome = ("fit_card" if session["fit_card"]
               else f"error={trunc(session['error'], 50)}")
    log(f"session END {outcome} (iters={session['iterations']}, "
        f"tools={len(session['tool_log'])})")
    return session


# ── CLI test ──────────────────────────────────────────────────────────────────

def _print_session_outcome(session: dict) -> None:
    if session["notices"]:
        for note in session["notices"]:
            print(f"[notice] {note}")
    if session["error"]:
        print(f"Error: {session['error']}")
        if session["outfit_suggestion"]:
            print(f"\nPartial outfit kept: {session['outfit_suggestion']}")
    else:
        print(f"Found: {session['selected_item']['title']} "
              f"(${session['selected_item']['price']:.2f}, "
              f"{session['selected_item']['platform']})")
        print(f"\nOutfit: {session['outfit_suggestion']}")
        print(f"\nFit card: {session['fit_card']}")
    sequence = " -> ".join(t["tool"] for t in session["tool_log"])
    print(f"\nTool sequence: {sequence or '(no tools called)'}")
    print(f"Iterations: {session['iterations']}")


if __name__ == "__main__":
    from utils.data_loader import get_example_wardrobe

    print("=== Happy path: graphic tee ===\n")
    session = run_agent(
        query="looking for a vintage graphic tee under $30",
        wardrobe=get_example_wardrobe(),
    )
    _print_session_outcome(session)
    same_object = (session["search_results"]
                   and session["selected_item"] is session["search_results"][0])
    print(f"selected_item IS search_results[0]: {same_object}")

    print("\n\n=== No-results path: impossible query ===\n")
    session2 = run_agent(
        query="designer ballgown size XXS under $5",
        wardrobe=get_example_wardrobe(),
    )
    _print_session_outcome(session2)
