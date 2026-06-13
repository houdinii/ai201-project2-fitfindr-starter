# FitFindr — AI201 Project 2

Multi-tool AI agent (Groq llama-3.3-70b-versatile). Three required tools in `tools.py`, planning loop in `agent.py`, Gradio UI in `app.py`. Rubric source of truth: `docs/Rubric_all_projects.html` (Project 2 section) and `docs/project-description.html`.

Required workflow order (graded): planning.md filled BEFORE implementation code; tools tested in isolation BEFORE the planning loop; planning.md updated BEFORE any stretch feature.

## Evidence discipline (enforced by Claude every session)
- RUBRIC_LEDGER.md is the progress tracker. When any work satisfies a ledger row,
  immediately paste the verbatim output into EVIDENCE.md and tick the row.
- Whenever a test/print/demo output appears in the terminal, Claude asks one question:
  "Is this a ledger exhibit?" If yes, it gets captured before moving on.
- Stretch features ship as implement + demonstrate + document in one sitting.
- Brian's one scheduling rule: done before Saturday night if possible. Real
  deadline Mon Jun 15, 12:59 AM MDT. Run /grade-sim before submitting. Do NOT
  give Brian day-by-day schedules or arbitrary intermediate deadlines.
  Stretch: ALL FOUR stretch goals are COMMITTED (+7). Build order:
  retry, price comparison, style profile memory, trend awareness.
- Periodically (every few work sessions) report: ledger rows ticked / total.

## Build workflow (the loop, one tool at a time)
- planning.md is the spec and the single source of truth. Implement FROM it.
  If implementation needs to diverge, update planning.md in the same sitting
  and note the divergence (it feeds the README's spec reflection).
- TODO.md is Brian's checklist, grouped by phase. Work top to bottom.
- Per tool: read its spec block in planning.md, implement it in tools.py,
  Brian reviews against the spec, write its pytest cases in tests/test_tools.py,
  run them, paste the output into EVIDENCE.md, tick TODO.md, tick any
  satisfied RUBRIC_LEDGER.md row. Brian commits.
- The AI Tool Plan section of planning.md lists per-tool verification checks
  (null brands, L vs XL, empty wardrobe, caption variation). Run them.

## Decision log (do not reopen without new information)
- 2026-06-12: Architecture is a ReAct-style LLM router with hard code guards
  (`MAX_ITERATIONS` cap, `suggest_outfit` blocked on empty results,
  `create_fit_card` blocked without `session["outfit_suggestion"]`).
- 2026-06-12: Zero-result retry is two-stage. Drop the `size` filter first,
  then the `max_price` cap, telling the user what was adjusted each time.
- 2026-06-12: State passes by reference. The router supplies lightweight ids,
  the executor resolves them against the session dict and injects full objects.
- 2026-06-12: All four stretch goals committed (+7).
- 2026-06-12: `search_listings` scoring is keyword overlap per the tools.py
  docstring (not semantic/distance search, that was Project 1). Each listing's
  `title`, `description`, `style_tags`, `colors`, `category`, and `brand` are
  joined into one lowercase haystack string, score is the count of query-word
  hits, `brand` skipped when null, score 0 dropped. Size matching is
  token-based so "L" never matches "XL".
- 2026-06-12: Style profile memory is a `data/style_profile.json` file.
  Reads are automatic, the executor loads it at session start and injects it
  into the `suggest_outfit` prompt like the wardrobe. Writes go through one
  router-visible tool, `save_style_preference(preference)`, so the demo shows
  the save happening in interaction one and the recall in interaction two.
- 2026-06-12: LLM tool failure signal is an exception. `suggest_outfit`
  propagates Groq client errors and raises `RuntimeError` on an empty LLM
  response. The executor owns catch, wait, retry once, then `session["error"]`,
  per the Error Handling table. Tools stay pure, the agent layer handles policy.
- 2026-06-12 (REVISED, supersedes the dummy-data version): Trend data is
  REAL. Brian rejected invented numbers. `data/trends.json` is a snapshot
  fetched by `utils/fetch_trends.py` from the Wikimedia Pageviews API
  (official, public, keyless). 23 style tags map to en.wikipedia style
  articles. `mentions` = real pageviews over the most recent 30 days,
  `momentum` = recent 30 days vs prior 30 days as a ratio minus 1. The
  snapshot nests under a `trends` key with `_source`, `_fetched`, `_window`
  metadata. Tags come from the dataset's own style_tags, plus gorpcore and
  barbiecore which are real trends with no stock (honest `in_stock: 0`).
  Rerun the script to refresh. NEVER fabricate data in this project.
- 2026-06-12: `compare_prices` verdict band is the comparable median ±10%,
  item excluded from its own comparables, comp stats are `None` on
  "not enough data". The tools.py function takes the resolved listing dict,
  `item_id` is the router-visible param, per the state-by-reference design.
- 2026-06-12: `check_trends` returns only the four specced fields (tag,
  mentions, momentum, in_stock), the snapshot's `article` and metadata keys
  stay in the file. Category narrowing and `in_stock` are computed against
  listings.json at call time, size matching reuses `_size_matches`. Profile
  file shape is `{"preferences": [...]}` with case-insensitive dedup on save.

## Working with Brian (enforced by Claude every session)
- Be decisive. Make one call, state the reason once, log it in the decision
  log above. Never present alternatives after a decision is made, never reopen
  a logged decision, never trim scope out of time-conservatism. Brian is a
  fast, competent programmer. Planning is where he wants the help, not pace.
- Writing style: no em dashes, no semicolons. Periods and commas instead.
  Wrap function names and variables in backticks.
- Brian handles all git commits himself. Claude never runs `git commit`,
  never adds Co-Authored-By trailers, and leaves the working tree for Brian
  to review and commit.