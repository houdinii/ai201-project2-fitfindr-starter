# FitFindr

A multi-tool AI agent that helps you find secondhand fashion and figure out how
to wear it. You describe what you want in plain language, and FitFindr searches
mock listings across Depop, thredUp, and Poshmark, styles the best match against
your existing wardrobe, and writes a shareable caption for it.

FitFindr is an **outfit builder, not a search engine**. Every interaction ends
one of two ways: a complete styled outfit with a shareable fit card, or a short
spoken answer (a greeting reply, an info answer, or a clear "nothing matched"
message). It never dumps a list of listings on you and asks you to pick.

## Demo

[Demo Video (Loom)](https://www.loom.com/share/b5ccbe74f65b4564b4de8e7bb1130836)

---

## Setup

```bash
pip install -r requirements.txt
```

Set your Groq API key in a `.env` file (free key at [console.groq.com](https://console.groq.com), no card required):

```
GROQ_API_KEY=your_key_here
```

## Run it

```bash
python app.py        # Gradio web UI, the URL prints in the terminal
python agent.py      # CLI, runs a built-in happy path and a no-results case
```

---

## Architecture

FitFindr is a ReAct-style router loop with hard code guards. Each iteration, an 
LLM (Groq `llama-3.3-70b-versatile`) sees the available tools and the conversation 
so far and chooses the next tool to call. An executor layer around it validates 
every call, runs the tool, and writes the result into a single session dict. 
The loop ends when a fit card exists, the agent has given a spoken answer, 
or an error is set.

The LLM decides *what* to do. Code decides *what is allowed*. The guards (below) 
are not suggestions the model can talk its way past. They are enforced in 
`agent.py` regardless of what the router asks for.

```
user query
   │
   ▼
session init  (load wardrobe + style_profile.json)
   │
   ▼
router LLM ──chooses a tool──▶ executor ──validates, runs, writes session──┐
   ▲                                                                        │
   └──────────────── observation (lightweight summary) ◀────────────────────┘
   │
   ▼  (fit_card set, response set, or error set)
return session ──▶ three UI panels: item · outfit · fit card
```

---

## Tool Inventory

Six tools. Three are required, three are stretch. The signatures below match `tools.py`
exactly. Tools that style or caption call the LLM; the rest are pure local
computation over the dataset.

### `search_listings` (required)
- **Inputs:** `description (str)`, `size (str | None)`, `max_price (float | None)`
- **Returns:** `list[dict]` — matching listings sorted by relevance, best match
  first. Each dict has `id`, `title`, `description`, `category`,
  `style_tags (list[str])`, `size`, `condition`, `price (float)`,
  `colors (list[str])`, `brand (str | None)`, `platform`. Empty list when
  nothing matches.
- **Purpose:** find listings. Scoring is keyword overlap against a lowercase
  haystack of title, description, style tags, colors, category, and brand (brand
  skipped when null). Size matching is token-based, so "M" matches "S/M" but "L"
  never matches "XL", and "One Size" matches anything. Pure local, no LLM.

### `suggest_outfit` (required)
- **Inputs:** `new_item (dict)`, `wardrobe (dict)`, `style_profile (list[str] | None)`, `trends (list[dict] | None)`
- **Returns:** `str` — a non-empty outfit suggestion naming specific wardrobe
  pieces. With an empty wardrobe it returns general styling advice instead.
- **Purpose:** style the found item against the user's wardrobe. The optional
  `style_profile` and `trends` are injected by the executor when available and
  shape the suggestion. LLM-backed.

### `create_fit_card` (required)
- **Inputs:** `outfit (str)`, `new_item (dict)`
- **Returns:** `str` — a 2 to 4 sentence Instagram/TikTok-style caption that
  names the item, price, and platform once each. Returns a descriptive error
  string (never raises) if the outfit is empty.
- **Purpose:** write the shareable caption. Uses a higher temperature so the
  caption varies run to run. LLM-backed.

### `compare_prices` (stretch: Price Comparison)
- **Inputs:** `item (dict)`
- **Returns:** `dict` — `verdict` ("below market" / "fair" / "above market" /
  "not enough data"), `item_price (float)`, `comparable_count (int)`,
  `comp_min` / `comp_median` / `comp_max` (float or None), and a
  human-readable `reasoning (str)`.
- **Purpose:** assess whether a listing's price is fair. Comparables are listings
  in the same category sharing at least one style tag, falling back to the whole
  category below three matches. Pure local.

### `check_trends` (stretch: Trend Awareness)
- **Inputs:** `category (str | None)`, `size (str | None)`
- **Returns:** `list[dict]` — up to five trends sorted by popularity, each with
  `tag`, `mentions (int)`, `momentum (float)`, `in_stock (int)`. Empty list if
  trend data is missing or nothing matches.
- **Purpose:** surface currently popular styles and how many in-stock listings
  match them in the user's size. Reads a real data snapshot (see Trend Awareness
  below). Pure local at call time.

### `save_style_preference` (stretch: Style Profile Memory)
- **Inputs:** `preference (str)`
- **Returns:** `list[str]` (updated preferences) or `str` (a descriptive error if
  the file cannot be written).
- **Purpose:** persist a durable style taste to `data/style_profile.json` so it
  survives across sessions. Only triggered on first-person lasting taste ("I love
  grunge"), never on a one-off item description.

> Note: the router refers to listings by lightweight `item_id` (e.g. `lst_017`),
> and the executor resolves that id to the full listing dict before calling
> `compare_prices`, `suggest_outfit`, or `create_fit_card`. See State Management.

---

## How the Planning Loop Works

The loop is adaptive, not a fixed script. Its branches:

1. **Parse and search.** The router extracts `description`, and `size` /
   `max_price` only if the user gave them, and calls `search_listings`.
2. **No results → two-stage retry, then stop.** If the search returns empty, the
   executor retries once with the size filter dropped, then once more with the
   price cap dropped, recording a user-facing notice for each adjustment. If it
   still finds nothing, it sets `session["error"]` to a specific message and
   stops. `suggest_outfit` is **never** called on empty results. The actual
   no-results message:
   > "No matches for 'designer ballgown' even with all filters loosened. The
   > cheapest item in stock is $12.00. Try a different description."
3. **Optional enrichment.** The router calls `compare_prices` when the user asks
   about price or worth, and `check_trends` when they ask what is popular.
4. **Style and caption.** It calls `suggest_outfit` on the best match, then
   `create_fit_card`. The loop ends when the fit card exists.
5. **Non-item messages punt, never dead-end.** A greeting or "what can you do?"
   gets a one-line explanation with an example query. An info question ("what's
   trending?") is answered directly from the tool result. Neither forces an
   outfit.

Hard guards enforced in code regardless of the router's choice:
- `MAX_ITERATIONS` cap (10) so the loop cannot run forever.
- `suggest_outfit` blocked while there are no search results.
- `create_fit_card` blocked without an outfit suggestion.
- Invalid tool calls (unknown tool, bad `item_id`) are not executed; the error is
  fed back as an observation so the router can self-correct.

Because behavior branches on what each tool returns, different inputs produce
different tool sequences: a happy path runs search → suggest → card, while an
impossible query runs search → (retry) → error and stops.

---

## State Management

The session dict (`agent.py:_new_session`) is the single source of truth for one
interaction. Key fields and when they are written:

- `query` — the original input, set at start.
- `style_profile` — loaded from `data/style_profile.json` at session start.
- `search_results`, `selected_item` — written by `search_listings`.
- `price_assessment` — written by `compare_prices`.
- `trends` — written by `check_trends`.
- `outfit_suggestion` — written by `suggest_outfit`.
- `fit_card` — written by `create_fit_card`.
- `response` — a conversational answer for non-item messages.
- `error`, `notices` — early-exit message and user-facing retry notes.
- `iterations`, `tool_log` — loop counter and a record of every tool call.

**State passes by reference, never through the LLM.** The router only ever emits
a lightweight `item_id` like `lst_017`. The executor resolves that id against
`session["search_results"]` and injects the full listing dict into the tool. The
wardrobe and style profile are injected the same way. Because the heavy objects
never round-trip through the model, the item returned by `search_listings` is
guaranteed to be the *same object* passed into `suggest_outfit`, with no
re-description and no transcription error. The only state that survives a session
is `data/style_profile.json`; everything else lives in the session dict and dies
with the run.

---

## Error Handling

Every tool handles its own failure mode, and the agent always returns a readable
message rather than a traceback.

| Tool | Failure mode | What the agent does |
|------|--------------|---------------------|
| `search_listings` | No results | Two-stage retry (drop size, then price), telling the user each adjustment. Still nothing → specific error naming the cheapest in-stock price. Never calls `suggest_outfit`. |
| `suggest_outfit` | Empty wardrobe | Returns general styling advice instead of named pieces, and the flow continues to a fit card. |
| `suggest_outfit` / `create_fit_card` | LLM call errors | Executor retries once, then sets a specific `error` while preserving any work already done (e.g. the outfit is still shown if only the caption failed). |
| `create_fit_card` | Empty outfit string | Returns a descriptive error string, never raises. |
| `compare_prices` | Fewer than 3 comparables | Verdict "not enough data" with reasoning; flow continues. |
| `check_trends` | Trend file missing/unreadable | Returns empty list; the agent proceeds and notes trend data was unavailable. |
| `save_style_preference` | File unwritable | Returns an error string; the session continues normally. |
| router / executor | Bad tool name or `item_id`, or `MAX_ITERATIONS` hit | Invalid calls bounce back as observations to self-correct; on exhaustion the agent reports what it accomplished with partial results. |

**Concrete example from testing** — empty-wardrobe path, real output:

```
$ python -c "from tools import search_listings, suggest_outfit; from utils.data_loader import get_empty_wardrobe; \
  r = search_listings('vintage graphic tee', None, 50); print(suggest_outfit(r[0], get_empty_wardrobe()))"

This Y2K baby tee is a great find, and with its fitted crop length and sweet
butterfly graphic, it's perfect for creating a variety of looks. To style this
top, consider pairing it with high-waisted pants or skirts to balance out the
cropped length... [general advice, no wardrobe pieces, no exception]
```

And the no-results path, real `python agent.py` output, showing the two-stage
retry then a specific, actionable error (and `suggest_outfit` never called):

```
[notice] Nothing matched for 'designer ballgown' in size XXS under $5.00, so I searched again without the size filter.
[notice] Nothing matched for 'designer ballgown' under $5.00, so I searched again without the price cap.
Error: No matches for 'designer ballgown' even with all filters loosened. The cheapest item in stock is $12.00. Try a different description.

Tool sequence: search_listings
Iterations: 1
```


---

## Stretch Features

### Price Comparison (`compare_prices`)
Given a listing, it gathers comparables (same category sharing a style tag,
falling back to the whole category below three), then places the item's price
against the comparable median. The verdict band is the median plus or minus 10
percent: below is "below market", within is "fair", above is "above market".
Returns the verdict plus min/median/max and a one-sentence reasoning. Example
reasoning: "At \$22.00 this item sits above the \$19.50 median of 12 comparable
tops listings."

### Style Profile Memory (`save_style_preference` + automatic load)
Style tastes are durable and are saved to `data/style_profile.json` (shape:
`{"preferences": [...]}`, case-insensitive dedup). The file is loaded at the
start of every session and surfaced both to the styling prompt and to the router
itself, so a saved preference shapes future searches and styling without the user
restating it. Save only fires on first-person lasting taste, not on per-request
item descriptions.

The two-session recall (session one saves "loves grunge", a fresh session two
styles a grunge-leaning outfit with no re-statement) is demonstrated in the demo
video. The save path is covered by automated tests, including first-write,
append, case-insensitive dedup, corrupt-profile-treated-as-empty, and
write-failure-returns-error-string.

### Trend Awareness (`check_trends`)
**Data source: real, not invented.** `data/trends.json` is a snapshot fetched by
`utils/fetch_trends.py` from the **Wikimedia Pageviews API** (official, public,
keyless). Each dataset style tag maps to an English Wikipedia style article (e.g.
`y2k` → `Y2K_aesthetic`). `mentions` is that article's pageviews over the most
recent 30 days; `momentum` is the recent 30 days versus the prior 30 as a ratio.
Two real rising trends with no stock in the dataset (gorpcore, barbiecore) are
included on purpose so the tool can honestly report `in_stock: 0`. Rerun
`python utils/fetch_trends.py` to refresh. The interface is written so a live
fashion-platform API could be swapped in.

Real `check_trends(category="tops", size="M")` output, the actual Wikimedia data
narrowed by category with live in-stock counts per size:

```
[
  {"tag": "y2k",           "mentions": 12612, "momentum": -0.014, "in_stock": 2},
  {"tag": "crochet",       "mentions": 11632, "momentum": -0.03,  "in_stock": 1},
  {"tag": "dark academia", "mentions":  9890, "momentum":  0.07,  "in_stock": 1},
  {"tag": "cottagecore",   "mentions":  8311, "momentum": -0.124, "in_stock": 4},
  {"tag": "goth",          "mentions":  7452, "momentum": -0.009, "in_stock": 1}
]
```

The demo video shows a returned trend visibly shaping the outfit suggestion.

### Retry Logic with Fallback
Built into the no-results path above. A zero-result search auto-retries with
loosened constraints (size dropped first, then price), and tells the user exactly
what was adjusted, e.g. "Nothing matched in size XXS under $5, so I searched
again without the size filter."

---

## Testing

All automated tests live in `tests/` and run with pytest (configured via
`pytest.ini`, no path setup needed):

```bash
pytest              # everything
pytest -v           # one line per test
```

`tests/test_data_loader.py` smoke-tests the data layer; `tests/test_tools.py`
covers each tool with at least one test per failure mode; `tests/test_agent.py`
covers the router and guards. Pure-local tool tests run offline; LLM tools are
mocked, so the full suite needs no API key.

**Manual failure drills** (each must return a message, never a traceback):

```bash
python -c "from tools import search_listings; print(search_listings('designer ballgown', size='XXS', max_price=5))"
```

(See the existing drills below in Debug Logging for the empty-wardrobe and
empty-outfit cases.)

## Debug Logging

Set `FITFINDR_LOG=1` to stream a one-line, millisecond-stamped trace of every LLM
call, tool call, and file read/write to stderr. Off by default; secrets are never
logged. Gated by `utils/trace.py`.

```bash
FITFINDR_LOG=1 python app.py
```

---

## Spec Reflection

**One way the spec helped:** the spec helped me immensely. The plan was clear and
well-defined, and the implementation was straightforward. By the time the spec was
finished, I only had to ask the LLM to implement the tools themselves without any 
extra explanation whatsoever. I was able to focus on issues with the prompt and 
execution itself rather than squashing bugs the entire time.

**One way implementation diverged and why:** the plan called for the style
profile to be injected only into the `suggest_outfit` prompt. In practice the
recall feature broke, because the router never saw the saved preference and so
asked the user to restate their style right after loading it. The fix diverged
from the plan by also surfacing the profile into the router's context at session
start, which is what made cross-session recall actually visible.

---

## AI Usage

This project was built with Claude Code, spec first, with review at each step. Specific instances:

1. **One Size matching.** Directed Claude to implement `search_listings` size
   matching from the Tool 1 spec. Claude flagged that the dataset has three
   "One Size" variants ("One Size", "One Size (adjustable)", "One Size /
   Oversized") and proposed containment matching over exact token equality. I
   verified the three variants against the dataset before accepting it.

2. **Trend data integrity.** An early version generated a synthetic
   `trends.json` with invented numbers. I rejected it as a data-integrity
   problem and directed a rewrite to fetch real data from the Wikimedia
   Pageviews API instead. The fetch script is committed at
   `utils/fetch_trends.py`.

3. **Style-memory recall bug.** While testing, the agent asked for my style
   right after loading a saved preference. I diagnosed the cause (the router
   never received the loaded profile) and directed the fix to surface the
   profile into the router context, overriding the original "inject only into
   suggest_outfit" design.

---

## Dataset and Wardrobe

`data/listings.json` — 40 mock listings across tops, bottoms, outerwear, shoes,
and accessories. Fields: `id`, `title`, `description`, `category`, `style_tags`,
`size`, `condition`, `price`, `colors`, `brand`, `platform`.

`data/wardrobe_schema.json` — the wardrobe format plus an `example_wardrobe` (10
items) and an `empty_wardrobe` template. Load helpers live in
`utils/data_loader.py` (`load_listings`, `get_example_wardrobe`,
`get_empty_wardrobe`).

`data/trends.json` — a snapshot of **real** trend data, 23 style tags fetched
from the Wikimedia Pageviews API by `utils/fetch_trends.py` (see Trend Awareness
above). Top-level keys are `_source`, `_fetched`, `_window`, `_script`, and
`trends`. Each entry has `tag`, `article` (the source Wikipedia article),
`mentions` (pageviews over the recent 30-day window), and `momentum` (recent vs
prior 30 days). `check_trends` computes `in_stock` against `listings.json` at
call time. Rerun `python utils/fetch_trends.py` to refresh the snapshot.

`data/style_profile.json` — written at runtime by `save_style_preference`, not
shipped. Shape: `{"preferences": [...]}`. Delete it to reset saved tastes.
