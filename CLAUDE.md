# FitFindr — AI201 Project 2

Multi-tool AI agent (Groq llama-3.3-70b-versatile). Three required tools in `tools.py`, planning loop in `agent.py`, Gradio UI in `app.py`. Rubric source of truth: `docs/Rubric_all_projects.html` (Project 2 section) and `docs/project-description.html`.

Required workflow order (graded): planning.md filled BEFORE implementation code; tools tested in isolation BEFORE the planning loop; planning.md updated BEFORE any stretch feature.

## Evidence discipline (enforced by Claude every session)
- RUBRIC_LEDGER.md is the progress tracker. When any work satisfies a ledger row,
  immediately paste the verbatim output into EVIDENCE.md and tick the row.
- Whenever a test/print/demo output appears in the terminal, Claude asks one question:
  "Is this a ledger exhibit?" If yes, it gets captured before moving on.
- Stretch features ship as implement + demonstrate + document in one sitting.
- MY deadline is Sunday June 14, 2026, 6:00 PM PT for all artifacts (real deadline:
  Mon Jun 15, 12:59 AM MDT). Sunday evening is for /grade-sim + submission only.
  Bulk build day is Saturday June 13; weeknight sessions are ~20-min planning.md
  chunks only. Stretch: ALL FOUR stretch goals are COMMITTED (+7). Build order:
  retry, price comparison, style profile memory, trend awareness.
- Periodically (every few work sessions) report: ledger rows ticked / total.

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
- 2026-06-12: Trend awareness data source is a bundled `data/trends.json`
  snapshot (tag and style frequencies styled as a fashion-platform feed),
  documented in the README as the data source, with the tool interface
  written so a live API could be swapped in. No external API on build day.

## Working with Brian (enforced by Claude every session)
- Be decisive. Make one call, state the reason once, log it in the decision
  log above. Never present alternatives after a decision is made, never reopen
  a logged decision, never trim scope out of time-conservatism. Brian is a
  fast, competent programmer. Planning is where he wants the help, not pace.
- Writing style: no em dashes, no semicolons. Periods and commas instead.
  Wrap function names and variables in backticks.