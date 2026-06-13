# Rubric Ledger — FitFindr (AI201 Project 2)

**DEADLINE: Monday June 15, 2026, 12:59 AM MDT (= Sunday June 14, 11:59 PM PT)**
**THE RULE: done before Saturday night if possible.** Whatever's left after that fits before the real deadline, including a /grade-sim pass before submitting.

Total: 25 pts required + 7 pts stretch. Graded artifacts: **GitHub repo, planning.md, README.md, demo video (3–5 min)**. If the evidence isn't in one of those four places, the point does not exist.

## Required Features (25 pts)

### Three Tools with Defined Interfaces (4 pts)
| Rubric line                                                                                                                 | Pts | Exhibit required                                                                               | Where it will live     | Status |
|-----------------------------------------------------------------------------------------------------------------------------|-----|------------------------------------------------------------------------------------------------|------------------------|--------|
| README lists all 3 required tools, each with a named function.                                                              | 1   | Tool inventory listing `search_listings`, `suggest_outfit`, `create_fit_card` by function name | README §Tool Inventory | ☐      |
| Each tool's inputs are described with parameter names and types (e.g., "description (str), size (str), max_price (float)"). | 1   | Every parameter as `name (type)` — must match actual signatures in tools.py                    | README §Tool Inventory | ☐      |
| Each tool's return value is described — not just "returns a list," but what's in the list.                                  | 1   | Return descriptions naming the fields inside (e.g., listing dict fields)                       | README §Tool Inventory | ☐      |
| Demo or source shows all 3 tools being called within a single interaction.                                                  | 1   | Demo segment of one query hitting all 3 tools (also visible in agent.py)                       | Demo video + agent.py  | ☐      |

### Multi-Step Workflow End to End (2 pts)
| Rubric line                                                                                                                                                    | Pts | Exhibit required                                                   | Where it will live                                 | Status |
|----------------------------------------------------------------------------------------------------------------------------------------------------------------|-----|--------------------------------------------------------------------|----------------------------------------------------|--------|
| Demo or source shows a complete interaction that starts with a natural language user query and ends with a fit card, using all 3 required tools along the way. | 1   | Full happy-path run: query → search → outfit → fit card, on camera | Demo video                                         | ☐      |
| The demo narration or the README / planning.md walkthrough explains what the agent is doing at each step — which tool is being called and why.                 | 1   | Narration script + step-by-step walkthrough in planning.md         | Demo narration + planning.md §Complete Interaction | ☑      |

### State Management Across Tool Calls (3 pts)
| Rubric line                                                                                                                                   | Pts | Exhibit required                                                                     | Where it will live                          | Status |
|-----------------------------------------------------------------------------------------------------------------------------------------------|-----|--------------------------------------------------------------------------------------|---------------------------------------------|--------|
| Demo or source shows that the item returned by search_listings is the same item passed into suggest_outfit — without the user re-entering it. | 1   | Print/narrate `session["selected_item"]` flowing into suggest_outfit                 | Demo video (+ EVIDENCE.md terminal capture) | ☐      |
| Demo or source shows the outfit from suggest_outfit passing into create_fit_card without re-entry.                                            | 1   | Print/narrate `session["outfit_suggestion"]` flowing into create_fit_card            | Demo video (+ EVIDENCE.md terminal capture) | ☐      |
| README describes the state management approach: what is stored, when, and how it passes between tools.                                        | 1   | Section describing the session dict: fields, when each is written, how tools read it | README §State Management                    | ☐      |

### Planning Loop Adaptiveness (4 pts)
| Rubric line                                                                                                                                                                      | Pts | Exhibit required                                                                                      | Where it will live                                   | Status |
|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-----|-------------------------------------------------------------------------------------------------------|------------------------------------------------------|--------|
| README explains the planning loop's conditional logic — what state it checks and what triggers each decision. "It decides what to do next" does not earn this point.             | 1   | Explicit branch description ("if search_results is empty → set error, return early; else …")          | README §Planning Loop                                | ☐      |
| README describes what the agent does specifically when search_listings returns no results (not just "it handles errors").                                                        | 1   | The exact no-results behavior, with the actual message text                                           | README §Planning Loop                                | ☐      |
| Demo or source shows the agent behaving differently for a non-standard input compared to the happy path — the agent doesn't call all tools unconditionally in the same sequence. | 2   | Side-by-side: happy path vs. impossible query ("designer ballgown XXS under $5") showing early return | Demo video + agent.py CLI test output in EVIDENCE.md | ☐      |

### Error Handling (3 pts)
| Rubric line                                                                                                                               | Pts | Exhibit required                                                       | Where it will live       | Status |
|-------------------------------------------------------------------------------------------------------------------------------------------|-----|------------------------------------------------------------------------|--------------------------|--------|
| README describes the specific failure mode for each of the 3 required tools and what the agent does in each case.                         | 1   | Per-tool failure table: no results / empty wardrobe / empty outfit     | README §Error Handling   | ☐      |
| Demo or source shows handling for at least one deliberately triggered failure (not a happy-path edge case — an actual failure).           | 1   | On-camera triggered failure (Milestone 5 commands)                     | Demo video + EVIDENCE.md | ☐      |
| Demo or source shows the agent's response to the failure is specific and actionable — it tells the user what failed and what to try next. | 1   | The failure message itself must name what failed + suggest what to try | Demo video + EVIDENCE.md | ☐      |

### planning.md Quality (4 pts)
| Rubric line                                                                                                                                                                                               | Pts | Exhibit required                                                                                    | Where it will live                                  | Status |
|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-----|-----------------------------------------------------------------------------------------------------|-----------------------------------------------------|--------|
| Tools — all 3 required tools described with name, inputs (name + type), return value, and what the agent does on failure.                                                                                 | 1   | All four fields filled for each of the 3 tool blocks                                                | planning.md §Tools                                  | ☑      |
| Planning Loop — conditional logic described (not just intent); State Management — what is stored and how it flows.                                                                                        | 1   | Specific branches + session dict description                                                        | planning.md §Planning Loop + §State Management      | ☑      |
| Error Handling table — completed with specific agent responses for each tool's failure mode; Complete Interaction walkthrough — traces the example query step-by-step through all three tool calls.       | 1   | Filled table (actual agent responses) + step-by-step trace of the example query                     | planning.md §Error Handling + §Complete Interaction | ☑      |
| Architecture diagram — shows data and control flow through the agent; AI Tool Plan — names specific spec sections used to prompt AI tools and describes how generated code was verified against the spec. | 1   | TEXT-BASED diagram (ASCII or Mermaid — images rejected by automated grader) + named-section AI plan | planning.md §Architecture + §AI Tool Plan           | ☑      |

### README Completeness (3 pts)
| Rubric line                                                                                                                                  | Pts | Exhibit required                                                        | Where it will live      | Status |
|----------------------------------------------------------------------------------------------------------------------------------------------|-----|-------------------------------------------------------------------------|-------------------------|--------|
| Tool inventory with inputs, outputs, and purpose for each tool; planning loop explanation with conditional logic; state management approach. | 1   | All three sections present and substantive                              | README                  | ☐      |
| Error handling per tool with at least one concrete example from testing.                                                                     | 1   | A REAL pasted example from a test run (this is what EVIDENCE.md is for) | README §Error Handling  | ☐      |
| Spec reflection (one way the spec helped, one divergence and why).                                                                           | 1   | Two specific sentences: one help, one divergence + why                  | README §Spec Reflection | ☐      |

### AI Usage Transparency (2 pts)
| Rubric line                                                                                                                 | Pts | Exhibit required                                                                    | Where it will live | Status |
|-----------------------------------------------------------------------------------------------------------------------------|-----|-------------------------------------------------------------------------------------|--------------------|--------|
| Section describes at least 2 specific instances of AI tool use, naming what the student directed the AI to do in each case. | 1   | ≥2 instances: what was given as input (which spec sections/diagram), what was asked | README §AI Usage   | ☐      |
| Each instance describes what the student reviewed, revised, or overrode.                                                    | 1   | Per instance: the specific thing reviewed/changed before accepting                  | README §AI Usage   | ☐      |

## Stretch (implement + demonstrate + document = ONE unit; 2 of 3 = zero points)
| Stretch line                                                                                                                                    | Pts | Exhibit required                                                     | Where it will live              | Status         |
|-------------------------------------------------------------------------------------------------------------------------------------------------|-----|----------------------------------------------------------------------|---------------------------------|----------------|
| Price Comparison Tool — tool returns a price assessment with reasoning based on comparable listings. README describes how comparisons are made. | +2  | Demo/source of assessment with reasoning + README method description | Demo + README §Price Comparison | ☐ COMMITTED |
| Style Profile Memory — two interactions where the second uses preferences from the first without re-entry. README describes storage approach.   | +2  | Two-session demo + README storage description                        | Demo + README §Style Memory     | ☐ COMMITTED |
| Trend Awareness Tool — trend info visibly influences the outfit suggestion. README describes the data source.                                   | +2  | Demo of trend → suggestion influence + README data source            | Demo + README §Trend Awareness  | ☐ COMMITTED |
| Retry Logic with Fallback — zero-result search auto-retries with loosened constraints, explaining what was adjusted.                            | +1  | Demo of retry with the "what was adjusted" message                   | Demo + README §Retry Logic      | ☐ COMMITTED, canonical in planning.md |

## Non-rubric hard requirements (zero-point traps)
- [ ] Demo video is **3–5 minutes** — a grader can and will check the length.
- [ ] Architecture diagram is **text-based in planning.md** (ASCII or ```mermaid block). Embedded image = automated grader can't read it = point lost.
- [ ] README tool inputs/returns **must match actual function signatures** in tools.py.
- [ ] planning.md **updated before starting any stretch feature** (stated requirement).
- [x] pytest tests in `tests/test_tools.py`, ≥1 test per failure mode, all passing (Milestone 3 requirement). COMPLETE 2026-06-12: Tool 1, 16 tests. Tool 2, 11 tests (empty wardrobe, LLM error). Tool 3, 8 tests (empty outfit error string, LLM error). Stretch tools 4-6, 17 tests (not enough data, missing/corrupt trends.json, write failure). 52 passing, exhibits in EVIDENCE.md.
- [ ] Submit: forked repo link + planning.md in root + README.md + demo video, via Course Portal.
- [ ] `.env` never committed.

## Progress
**Required rows ticked: 5 / 24** (planning.md Quality complete: 4/4. Multi-step walkthrough line earned via planning.md, demo narration Sat/Sun will reinforce it.)