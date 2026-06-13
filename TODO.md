# FitFindr Build Checklist

## Setup (5 min)
- [x] `source .venv/bin/activate`
- [x] `python utils/data_loader.py` runs clean

## search_listings (no LLM, fastest win)
- [x] Implement `search_listings`
- [x] Null brand skipped, no crash
- [x] "L" does NOT match "XL"
- [x] "One Size" matches any size
- [x] Test: normal query returns results
- [x] Test: impossible query returns `[]`
- [x] Test: price filter respected
- [x] Test: size token matching
- [x] `pytest tests/` green
- [x] Paste pytest output into EVIDENCE.md

## suggest_outfit
- [ ] Implement `suggest_outfit` (Groq)
- [ ] Empty wardrobe → general advice, no crash
- [ ] Null `notes` skipped in prompt
- [ ] Optional params `style_profile`, `trends` wired
- [ ] Test: empty wardrobe case
- [ ] One manual run pasted into EVIDENCE.md

## create_fit_card
- [ ] Implement `create_fit_card` (Groq, high temp)
- [ ] Empty outfit → error string, no exception
- [ ] Run twice, same input, outputs differ
- [ ] Paste both runs into EVIDENCE.md
- [ ] Test: empty outfit case

## stretch tools
- [ ] Implement `compare_prices`
- [ ] Test: under 3 comparables → "not enough data"
- [ ] Implement `save_style_preference`
- [ ] Writes file AND `session["style_profile"]`
- [ ] Author `data/trends.json` (real tags + 2 fakes)
- [ ] Implement `check_trends`
- [ ] Test: missing trends.json → `[]`

## router (agent.py)
- [ ] Session dict: add new fields
- [ ] Tool schemas for Groq function calling
- [ ] Router loop: call → validate → execute → append
- [ ] Executor resolves `item_id` from session
- [ ] Executor injects wardrobe / profile / trends
- [ ] Guard: `MAX_ITERATIONS`
- [ ] Guard: empty results → retry, drop size
- [ ] Guard: retry 2, drop max_price
- [ ] Guard: still empty → error, NO suggest_outfit
- [ ] Guard: no fit card without outfit
- [ ] Guard: empty description → ask user
- [ ] Bad tool / bad ref → observation back to router
- [ ] LLM failure → one retry → error
- [ ] `python agent.py` happy path works
- [ ] `python agent.py` ballgown path errors right
- [ ] Paste both `tool_log`s into EVIDENCE.md

## failure drills
- [ ] Terminal: trigger zero results → EVIDENCE.md
- [ ] Terminal: trigger empty wardrobe → EVIDENCE.md
- [ ] Terminal: trigger empty outfit → EVIDENCE.md
- [ ] Screenshot one failure for the demo

## app
- [ ] Implement `handle_query` in app.py
- [ ] `python app.py`: all 3 panels populate
- [ ] Two-session style memory test works

## README
- [ ] Tool inventory, 6 tools, params match code exactly
- [ ] Planning loop section (real conditional logic)
- [ ] No-results behavior with verbatim message text
- [ ] State management section
- [ ] Error handling per tool + 1 real example from EVIDENCE.md
- [ ] Spec reflection: 1 way it helped, 1 divergence + why
- [ ] AI usage: 2+ instances, what I directed, what I overrode
- [ ] Stretch: price comparison section
- [ ] Stretch: style memory section
- [ ] Stretch: trends section (name data source)
- [ ] Stretch: retry section

## demo video (3 to 5 min, hard limit)
- [ ] Write narration script from RUBRIC_LEDGER.md
- [ ] Rehearse once, time it
- [ ] Record: happy path, all 3 tools, narrated
- [ ] Record: state passing shown (print selected_item)
- [ ] Record: ballgown query, retry, graceful error
- [ ] Record: style memory across two sessions
- [ ] Record: price verdict + trend influence moments
- [ ] Confirm length is 3 to 5 minutes

## ship it
- [ ] Run /grade-sim, fix everything it flags
- [ ] `.env` NOT in the repo
- [ ] git push to fork
- [ ] planning.md in repo root on GitHub
- [ ] Submit portal: repo link + video
- [ ] Breathe
